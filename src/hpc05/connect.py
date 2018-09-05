from contextlib import suppress
import glob
import os.path
import subprocess
import sys
import time

from .client import Client

from ipyparallel.error import NoEnginesRegistered

from .ssh_utils import setup_ssh


VERBOSE = True
MAX_LINE_LENGTH = 100


def print_same_line(msg):
    msg = msg.strip()
    global MAX_LINE_LENGTH
    MAX_LINE_LENGTH = max(len(msg), MAX_LINE_LENGTH)
    empty_space = max(MAX_LINE_LENGTH - len(msg), 0) * ' '
    print(msg + empty_space, end='\r')


def watch_file(fname):
    fp = open(fname, 'r')
    while True:
        new = fp.readline()
        # Once all lines are read this just returns ''
        # until the file changes and a new line appears
        if new:
            yield new.strip()
        else:
            time.sleep(0.01)


def watch_stdout(stdout):
    text_iter = iter(stdout.readline, b'')
    while True:
        lines = [l.strip() for l in next(text_iter).replace('\r', '\n').strip().split('\n')]
        for line in lines:
            if line:
                yield line


def wait_for_succesful_start(log_file, timeout=300):
    t_start = time.time()
    watch = watch_file if isinstance(log_file, str) else watch_stdout
    for line in watch(log_file):
        print(line) if VERBOSE else print_same_line(line)
        if 'Engines appear to have started successfully' in line:
            break

        if 'Cluster is already running with' in line:
            # Currently not working!
            raise Exception('Failed to start a ipcluster because a cluster is '
                            'already running, run '
                            '`hpc05.kill_remote_ipcluster()`.')

        if time.time() - t_start > timeout:
            raise Exception(f'Failed to start a ipcluster in {timeout} seconds.')
        time.sleep(0.01)

    print_same_line('The log-file reports "Engines appear to have started successfully".')
    print()



def start_ipcluster(n, profile, env_path=None, timeout=300):
    """Start an ipcluster.

    Parameters
    ----------
    n : int
        Number of engines to be started.
    profile : str
        Profile name of IPython profile.
    env_path : str, default=None
        Path of the Python environment, '/path/to/ENV/' if Python is in /path/to/ENV/bin/python.
        Examples '~/miniconda3/envs/dev/', 'miniconda3/envs/dev', '~/miniconda3'.
        Defaults to the environment that is sourced in `.bashrc` or `.bash_profile`.
    timeout : int
        Time limit after which the connection attempt is cancelled.
    """
    log_file_pattern = os.path.expanduser(f'~/.ipython/profile_{profile}/log/ipcluster-*.log')
    for f in glob.glob(log_file_pattern):
        # Remove old log files.
        os.remove(f)

    pid_pattern = os.path.expanduser(f'~/.ipython/profile_{profile}/pid/*')
    for f in glob.glob(pid_pattern):
        # Remove old pid files.
        os.remove(f)

    ipcluster = 'ipcluster'
    if env_path:
        ipcluster = os.path.join(os.path.expanduser(env_path), 'bin', ipcluster)

    print(f'Launching {n} engines in a ipcluster.')
    cmd = f'{ipcluster} start --profile={profile} --n={n} --log-to-file --daemon &'

    # For an unknown reason `subprocess.Popen(cmd.split())` doesn't work when
    # running `start_remote_ipcluster` and connecting to it, so we use os.system.
    os.system(cmd + ("> /dev/null 2>&1" if not VERBOSE else ''))
    for i in range(10):
        print_same_line(f'Waiting for {i} seconds for the log-file.')
        time.sleep(1)  # We wait a bit since we need the log file to exist

        # We don't PIPE stdout of the process above because we need a detached
        # process so we tail the log file.
        with suppress(IndexError):
            log_file = glob.glob(log_file_pattern)[0]
            break
    print(f'Found the log-file ({log_file}) in {i} seconds.')

    wait_for_succesful_start(log_file, timeout=timeout)


def start_remote_ipcluster(n, profile='pbs', hostname='hpc05',
                           username=None, password=None, env_path=None, 
                           timeout=300):
    if env_path is None:
        env_path = ''

    with setup_ssh(hostname, username, password) as ssh:
        cmd = f"import hpc05; hpc05.start_ipcluster({n}, '{profile}', '{env_path}', {timeout})"
        cmd = f'python -c "{cmd}"'
        stdin, stdout, stderr = ssh.exec_command(cmd, get_pty=True)
        wait_for_succesful_start(stdout, timeout=timeout)


def connect_ipcluster(n, profile='pbs', folder=None, env_path=None,
                      timeout=300, hostname='hpc05', client_kwargs=None,
                      local=True):
    """Connect to a local ipcluster on the cluster headnode.

    Parameters
    ----------
    n : int
        Number of engines to be started.
    profile : str, default 'pbs'
        Profile name of IPython profile.
    folder : str, optional
        Folder that is added to the path of the engines, e.g. "~/Work/my_current_project".
    timeout : int
        Time for which we try to connect to get all the engines.
    hostname : str
        Hostname of machine where the ipcluster runs. If connecting
        via the headnode use: `socket.gethostname()` or set `local=True`.
    client_kwargs : dict
        Keyword arguments that are passed to `ipyparallel.Client()`.
    local : bool, default: True
        Connect to the client locally or over ssh. Set it False if
        a connection over ssh is needed.

    Returns
    -------
    client : ipython.Client object
        An IPyparallel client.
    dview : ipyparallel.client.view.DirectView object
        Direct view, equivalent to `client[:]`.
    lview : ipyparallel.client.view.LoadBalancedView
        LoadedBalancedView, equivalent to `client.load_balanced_view()`.
    """
    if client_kwargs is None:
        client_kwargs = {}
    client = Client(profile=profile, env_path=env_path,
                    timeout=timeout, hostname=hostname, **client_kwargs)
    print("Connected to the `ipcluster` using a `ipyparallel.Client`.")
    time.sleep(2)
    with suppress(NoEnginesRegistered):
        # This can happen, we just need to wait a little longer.
        dview = client[:]

    t_start = time.time()
    n_engines_old = len(client)
    done = (n_engines_old == n)
    while not done:
        n_engines = len(client)
        done = (n_engines == n)
        with suppress(NoEnginesRegistered):
            # This can happen, we just need to wait a little longer.
            dview = client[:]
        t_diff = time.time() - t_start
        msg = f'Connected to {n_engines} out of {n} engines after {int(t_diff)} seconds.'
        print_same_line(msg) if n_engines_old == n_engines else print(msg)
        if t_diff > timeout:
            raise Exception(f'Not all ({n_engines}/{n}) connected after {timeout} seconds.')
        n_engines_old = n_engines
        time.sleep(1)

    dview.use_dill()
    lview = client.load_balanced_view()

    if folder is not None:
        print(f'Adding {folder} to path.')
        cmd = f"import sys, os; sys.path.append(os.path.expanduser('{folder}'))"
        dview.execute(cmd).result()

    return client, dview, lview


def start_and_connect(n, profile='pbs', folder=None,
                      kill_old_ipcluster=True, env_path=None, timeout=300,
                      hostname='hpc05', client_kwargs=None, local=True):
    """Start a ipcluster locally and connect to it. Run this on the cluster headnode.

    Parameters
    ----------
    n : int
        Number of engines to be started.
    profile : str, default 'pbs'
        Profile name of IPython profile.
    folder : str, optional
        Folder that is added to the path of the engines, e.g. "~/Work/my_current_project".
    kill_old_ipcluster : bool
        If True, it cleansup any old instances of `ipcluster` and kills your jobs in qstat.
    env_path : str, default None
        Path of the Python environment, '/path/to/ENV/' if Python is in /path/to/ENV/bin/python.
        Examples '~/miniconda3/envs/dev/', 'miniconda3/envs/dev', '~/miniconda3'.
        Defaults to the environment that is sourced in `.bashrc` or `.bash_profile`.
    timeout : int
        Time for which we try to connect to get all the engines.
    hostname : str
        Hostname of machine where the ipcluster runs. If connecting
        via the headnode use: `socket.gethostname()`.
    client_kwargs : dict
        Keyword arguments that are passed to `ipyparallel.Client()`.
    local : bool, default: True
        Connect to the client locally or over ssh. Set it False if
        a connection over ssh is needed.

    Returns
    -------
    client : ipython.Client object
        An IPyparallel client.
    dview : ipyparallel.client.view.DirectView object
        Direct view, equivalent to `client[:]`.
    lview : ipyparallel.client.view.LoadBalancedView
        LoadedBalancedView, equivalent to `client.load_balanced_view()`.
    """
    if kill_old_ipcluster:
        kill_ipcluster(profile)
        print('Killed old intances of ipcluster.')

    start_ipcluster(n, profile, env_path, timeout)
    return connect_ipcluster(n, profile, folder, env_path, timeout,
                             hostname, client_kwargs, local)


def start_remote_and_connect(n, profile='pbs', folder=None, hostname='hpc05',
                             username=None, password=None,
                             kill_old_ipcluster=True, env_path=None, timeout=300,
                             client_kwargs=None):
    """Start a remote ipcluster and connect to it.

    Parameters
    ----------
    n : int
        Number of engines to be started.
    profile : str, default 'pbs'
        Profile name of IPython profile.
    folder : str, optional
        Folder that is added to the path of the engines, e.g. "~/Work/my_current_project".
    hostname : str, optional, default 'hpc05'
        Hostname of cluster headnode.
    username : str
        Username to log into `hostname`. If not provided, it tries to look it up in
        your `.ssh/config`.
    password : str
        Password for `ssh username@hostname`.
    kill_old_ipcluster : bool
        If True, it cleansup any old instances of `ipcluster` and kills your jobs in qstat.
    env_path : str, default None
        Path of the Python environment, '/path/to/ENV/' if Python is in /path/to/ENV/bin/python.
        Examples '~/miniconda3/envs/dev/', 'miniconda3/envs/dev', '~/miniconda3'.
        Defaults to the environment that is sourced in `.bashrc` or `.bash_profile`.
    timeout : int
        Time for which we try to connect to get all the engines.
    client_kwargs : dict
        Keyword arguments that are passed to `ipyparallel.Client()`.

    Returns
    -------
    client : ipython.Client object
        An IPyparallel client.
    dview : ipyparallel.client.view.DirectView object
        Direct view, equivalent to `client[:]`.
    lview : ipyparallel.client.view.LoadBalancedView
        LoadedBalancedView, equivalent to `client.load_balanced_view()`.
    """
    if kill_old_ipcluster:
        kill_remote_ipcluster(hostname, username, password)
        print('Killed old intances of ipcluster.')

    start_remote_ipcluster(n, profile, hostname, username,
                           password, env_path, timeout)
    time.sleep(2)
    return connect_ipcluster(n, profile, folder, env_path, timeout,
                             client_kwargs=client_kwargs, local=False)


def kill_ipcluster(name=None):
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
    clean_up_cmds = [
        "qselect -u $USER | xargs qdel",
         "rm -f *.hpc05.hpc* ipengine* ipcontroller* pbs_*",
         "pkill -f hpc05_culler",
         "pkill -f ipcluster",
         "pkill -f ipengine",
         "pkill -f ipyparallel.controller",
         "pkill -f ipyparallel.engines",
         "scancel --name='ipy-engine-' --user=$USER",
         "scancel --name='ipy-controller-' --user=$USER",
    ]

    if name is not None:
        clean_up_cmds.append(f"scancel --name='{name}' --user=$USER")

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
        with suppress(Exception):
            lines = stdout.readlines()
            for line in lines:
                print(line)
