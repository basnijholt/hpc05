#!/usr/bin/env python


latest_data = {}

def get_usage():
    """return a dict of usage info for this process"""
    from IPython import get_ipython
    import socket
    import psutil
    from datetime import datetime
    hn = socket.gethostname()
    p = psutil.Process()
    mem = p.memory_percent()
    cpu = p.cpu_percent(interval=0.1)
    return {
        'engine_id': getattr(get_ipython().kernel, 'engine_id', None),
        'date': datetime.utcnow(),
        'cpu': cpu,
        'mem': mem,
        'hostname': hn,
        'pid': os.getpid(),
    }


def publish_data_forever(interval):
    """Forever, call get_usage and publish the data via datapub

    This will be available on all AsyncResults as `ar.data`.
    """
    from threading import Thread
    import time
    import __main__ as user_ns # the interactive namespace

    from ipyparallel.datapub import publish_data

    def main():
        while not getattr(user_ns, 'stop_publishing', False):
            publish_data(get_usage())
            time.sleep(interval)
    Thread(target=main, daemon=True).start()


def collect_data(session, msg_frames):
    """Collect and deserialize messages"""
    from ipyparallel import serialize
    global latest_data
    idents, msg = session.feed_identities(msg_frames)
    try:
        msg = session.deserialize(msg, content=True)
    except Exception as e:
        print(e)
        return
    if msg['header']['msg_type'] != 'data_message':
        return
    # show the contents of data messages:
    data, remainder = serialize.deserialize_object(msg['buffers'])
    latest_data[data['engine_id']] = data


def start(client):
    from functools import partial
    client._iopub_stream.on_recv(partial(collect_data, client.session))


def print_usage(data=None):
    import pprint
    """Nicely print usage data"""
    if data is None:
        data = latest_data
    print(
        " {:2s} {:20s} {:32s} {:3s}% {:3s}%".format(
            "id",
            "hostname",
            "date",
            "CPU",
            "MEM",
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
        ))


if __name__ == '__main__':
    publish_data_forever(interval=5)
