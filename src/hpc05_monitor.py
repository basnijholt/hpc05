#!/usr/bin/env python

import asyncio
import operator
import os
import socket
from collections import defaultdict
from datetime import datetime

import psutil

MAX_USAGE = defaultdict(dict)

LATEST_DATA = {}

START_TIME = None


def get_usage():
    """return a dict of usage info for this process"""
    from IPython import get_ipython

    hn = socket.gethostname()
    mem = psutil.virtual_memory().percent
    cpu = psutil.cpu_percent()
    return {
        "engine_id": getattr(get_ipython().kernel, "engine_id", None),
        "date": datetime.utcnow(),
        "cpu": cpu,
        "mem": mem,
        "hostname": hn,
        "pid": os.getpid(),
    }


def publish_data_forever(interval):
    """Forever, call get_usage and publish the data via datapub

    This will be available on all AsyncResults as `ar.data`.
    """
    from threading import Thread
    import time
    import __main__ as user_ns  # the interactive namespace

    from ipyparallel.datapub import publish_data

    def main():
        while not getattr(user_ns, "stop_publishing", False):
            publish_data(get_usage())
            time.sleep(interval)

    Thread(target=main, daemon=True).start()


def collect_data(session, msg_frames):
    """Collect and deserialize messages"""
    from ipyparallel import serialize

    global LATEST_DATA
    idents, msg = session.feed_identities(msg_frames)
    try:
        msg = session.deserialize(msg, content=True)
    except Exception as e:
        print(e)
        return
    if msg["header"]["msg_type"] != "data_message":
        return
    # show the contents of data messages:
    data, remainder = serialize.deserialize_object(msg["buffers"])
    LATEST_DATA[data["engine_id"]] = data


def start(client, interval=5):
    global START_TIME
    from functools import partial

    client._iopub_stream.on_recv(partial(collect_data, client.session))
    ioloop = asyncio.get_event_loop()
    START_TIME = datetime.utcnow()
    return ioloop.create_task(_update_max_usage(interval))


async def _update_max_usage(interval):
    while True:
        for i, info in LATEST_DATA.items():
            for k in ["cpu", "mem"]:
                MAX_USAGE[i][k] = max(
                    (info[k], info["date"]),
                    MAX_USAGE[i].get(k, (0, None)),
                    key=operator.itemgetter(0),
                )
        await asyncio.sleep(interval)


def print_usage(data=None):
    """Nicely print usage data"""
    if data is None:
        data = LATEST_DATA
    print(
        " {:2s} {:20s} {:32s} {:3s}% {:3s}%".format(
            "id", "hostname", "date", "CPU", "MEM"
        )
    )
    for eid, report in sorted(data.items()):
        print(
            "{:3.0f} {:20s} {:32s} {:3.0f}% {:3.0f}%".format(
                report["engine_id"],
                report["hostname"],
                report["date"].isoformat(),
                report["cpu"],
                report["mem"],
            )
        )


def print_max_usage():
    if START_TIME is None:
        raise Exception(
            "Start the hpc05_monitor first by using" '"hpc05_monitor.start(client)".'
        )
    for k in ["mem", "cpu"]:
        i, info = max(MAX_USAGE.items(), key=lambda x: x[1][k][0])
        usage, date = info[k]
        time_ago = (datetime.utcnow() - START_TIME).total_seconds()
        print(
            f"Max {k} usage of {usage:.2f}% on engine {i}"
            f" at {date.isoformat()}, {time_ago:.0f} seconds ago."
        )


if __name__ == "__main__":
    publish_data_forever(interval=5)
