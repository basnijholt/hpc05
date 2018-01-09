import glob
import os.path
import subprocess
import time

from .client import Client

from ipyparallel.error import NoEnginesRegistered

from .ssh_utils import setup_ssh


def wait_for_succesful_start(stdout, decode, timeout=60):
    lines = iter(stdout.readline, b'')
    t_start = time.time()
    done = False
    while not done:
        line = next(lines)
        if decode:
            line = line.decode('utf-8')
        line = line.rstrip('\n').rstrip()
        if line:
            print(line)
        done = 'Engines appear to have started successfully' in line
        if time.time() - t_start > timeout:
            raise Exception(f'Failed to start a ipcluster in {timeout} seconds.')

        if 'Cluster is already running with' in line:
            # Currently not working!
            raise Exception(f'Failed to start a ipcluster because a cluster is '
                              'already running, run '
                              '`hpc05.kill_remote_ipcluster()` or use '
                              'your `del` alias.')
        time.sleep(0.01)


def start_ipcluster(n, profile, timeout=60):
    log_file_pattern = os.path.expanduser(f'~/.ipython/profile_{profile}/log/ipcluster-*.log')
    for f in glob.glob(log_file_pattern):
        # Remove old log files.
        os.remove(f)

    print(f'Launching {n} engines in a ipcluster.')
    cmd = f'ipcluster start --profile={profile} --n={n} --log-to-file --daemon &'

    # For an unknown reason `subprocess.Popen(cmd.split())` doesn't work when
    # running `start_remote_ipcluster` and connecting to it, so we use os.system.
    os.system(cmd)

    time.sleep(5)  # We wait a bit since we need the log file to exit

    # We don't PIPE stdout of the process above because we need a detached
    # process so we tail the log file.
    log_file = glob.glob(log_file_pattern)[0]
    cmd = f'tail -F {log_file}'
    proc = subprocess.Popen(cmd.split(),
                            stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT)

    wait_for_succesful_start(proc.stdout, decode=True, timeout=timeout)


def start_remote_ipcluster(n, profile='pbs', hostname='hpc05',
                           username=None, password=None, timeout=60):
    with setup_ssh(hostname, username, password) as ssh:
        cmd = f"import hpc05; hpc05.start_ipcluster({n}, '{profile}')"
        cmd = f'python -c "{cmd}"'
        stdin, stdout, stderr = ssh.exec_command(cmd, get_pty=True)
        wait_for_succesful_start(stdout, decode=False, timeout=timeout)


def connect_ipcluster(n, profile='pbs', folder=None, timeout=60):
    client = Client(profile=profile, timeout=timeout)
    print("Connected to hpc05")
    print(f'Initially connected to {len(client)} engines.')
    time.sleep(2)
    try:
        dview = client[:]
    except NoEnginesRegistered:
        # This can happen, we just need to wait a little longer.
        pass

    t_start = time.time()
    done = len(client) == n
    while not done:
        done = len(client) == n
        try:
            dview = client[:]
        except NoEnginesRegistered:
            # This can happen, we just need to wait a little longer.
            pass
        t_diff = int(time.time() - t_start)
        if t_diff % 10 == 0:
            print(f'Connected to {len(client)} engines after {int(t_diff)} seconds')
        if t_diff > timeout:
            raise Exception(f'Not all connected after {timeout} seconds.')
        time.sleep(1)

    print(f'Connected to all {len(client)} engines.')
    dview.use_dill()
    lview = client.load_balanced_view()

    if folder is not None:
        print(f'Adding {folder} to path.')
        get_ipython().magic(f"px import sys, os; sys.path.append(os.path.expanduser('{folder}'))")

    return client, dview, lview


def start_and_connect(n, profile='pbs', folder=None,
                      del_old_ipcluster=True, timeout=60):
    if del_old_ipcluster:
        kill_ipcluster()
        print('Killed old intances of ipcluster.')

    start_ipcluster(n, profile)
    return connect_ipcluster(n, profile, folder, timeout)


def start_remote_and_connect(n, profile='pbs', folder=None, hostname='hpc05',
                             username=None, password=None,
                             del_old_ipcluster=True, timeout=60):
    if del_old_ipcluster:
        kill_remote_ipcluster(hostname, username, password)
        print('Killed old intances of ipcluster.')

    start_remote_ipcluster(n, profile, hostname, username, password)
    time.sleep(2)
    return connect_ipcluster(n, profile, folder, timeout)


def kill_ipcluster():
    """Kill your ipcluster and cleanup the files.

    This should do the same as the following bash function (recommended:
    add this in your `.bash_profile` / `.bashrc`):
    ```bash
    del() {
        qselect -u $USER | xargs qdel
        rm -f *.hpc05.hpc* ipengine* ipcontroller* pbs_*
        pkill -f hpc05_culler 2> /dev/null
        pkill -f ipcluster 2> /dev/null
        pkill -f ipengine 2> /dev/null
        pkill -f ipyparallel.controller 2> /dev/null
        pkill -f ipyparallel.engines 2> /dev/null
    }
    ```
    """
    clean_up_cmds = ["qselect -u $USER | xargs qdel",
                     "rm -f *.hpc05.hpc* ipengine* ipcontroller* pbs_*",
                     "pkill -f hpc05_culler",
                     "pkill -f ipcluster",
                     "pkill -f ipengine",
                     "pkill -f ipyparallel.controller",
                     "pkill -f ipyparallel.engines"]

    clean_up_cmds = [cmd + ' 2> /dev/null' for cmd in clean_up_cmds]

    for cmd in clean_up_cmds:
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, shell=True)
        process.wait()


def kill_remote_ipcluster(hostname='hpc05', username=None, password=None):
    """Kill your remote ipcluster and cleanup the files.

    This should do the same as the following bash function (recommended:
    add this in your `.bash_profile` / `.bashrc`):
    ```bash
    del() {
        qselect -u $USER | xargs qdel
        rm -f *.hpc05.hpc* ipengine* ipcontroller* pbs_*
        pkill -f hpc05_culler 2> /dev/null
        pkill -f ipcluster 2> /dev/null
        pkill -f ipengine 2> /dev/null
        pkill -f ipyparallel.controller 2> /dev/null
        pkill -f ipyparallel.engines 2> /dev/null
    }
    ```
    """
    with setup_ssh(hostname, username, password) as ssh:
        cmd = f"import hpc05; hpc05.connect.kill_ipcluster()"
        cmd = f'python -c "{cmd}"'
        stdin, stdout, stderr = ssh.exec_command(cmd, get_pty=True)
        try:
            lines = stdout.readlines()
            for line in lines:
                print(line)
        except:
            pass
