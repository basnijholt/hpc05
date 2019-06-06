from contextlib import suppress
import glob
import os.path
import subprocess
import time

from ipyparallel.error import NoEnginesRegistered

from hpc05.client import Client
from hpc05.ssh_utils import setup_ssh
from hpc05.utils import print_same_line


VERBOSE = True


def watch_file(fname):
    fp = open(fname, "r")
    while True:
        new = fp.readline()
        # Once all lines are read this just returns ''
        # until the file changes and a new line appears
        if new:
            yield new.strip()
        else:
            time.sleep(0.01)


def watch_stdout(stdout):
    text_iter = iter(stdout.readline, b"")
    while True:
        lines = [
            l.strip() for l in next(text_iter).replace("\r", "\n").strip().split("\n")
        ]
        for line in lines:
            if line:
                yield line


def wait_for_succesful_start(log_file, timeout=300):
    t_start = time.time()
    watch = watch_file if isinstance(log_file, str) else watch_stdout
    for line in watch(log_file):
        print(line) if VERBOSE else print_same_line(line)
        if "Engines appear to have started successfully" in line:
            break

        if "Cluster is already running with" in line:
            # Currently not working!
            raise Exception(
                "Failed to start a ipcluster because a cluster is "
                "already running, run "
                "`hpc05.kill_remote_ipcluster()`."
            )

        if time.time() - t_start > timeout:
            raise Exception(f"Failed to start a ipcluster in {timeout} seconds.")
        time.sleep(0.01)
    msg = 'The log-file reports "Engines appear to have started successfully".'
    print_same_line(msg, new_line_end=True)


def start_ipcluster(n, profile, env_path=None, timeout=300):
    """Start an `ipcluster` locally.

    Parameters
    ----------
    n : int
        Number of engines to be started.
    profile : str, default 'pbs'
        Profile name of IPython profile.
    env_path : str, default=None
        Path of the Python environment, '/path/to/ENV/' if Python is in /path/to/ENV/bin/python.
        Examples '~/miniconda3/envs/dev/', 'miniconda3/envs/dev', '~/miniconda3'.
        Defaults to the environment that is sourced in `.bashrc` or `.bash_profile`.
    timeout : int
        Time limit after which the connection attempt is cancelled.

    Returns
    -------
    None
    """
    log_file_pattern = os.path.expanduser(
        f"~/.ipython/profile_{profile}/log/ipcluster-*.log"
    )
    for f in glob.glob(log_file_pattern):
        # Remove old log files.
        os.remove(f)

    pid_pattern = os.path.expanduser(f"~/.ipython/profile_{profile}/pid/*")
    for f in glob.glob(pid_pattern):
        # Remove old pid files.
        os.remove(f)

    ipcluster = "ipcluster"
    if env_path:
        ipcluster = os.path.join(os.path.expanduser(env_path), "bin", ipcluster)

    print(f"Launching {n} engines in a ipcluster.")
    cmd = f"{ipcluster} start --profile={profile} --n={n} --log-to-file --daemon &"

    # For an unknown reason `subprocess.Popen(cmd.split())` doesn't work when
    # running `start_remote_ipcluster` and connecting to it, so we use os.system.
    os.system(cmd + ("> /dev/null 2>&1" if not VERBOSE else ""))
    for i in range(10):
        print_same_line(f"Waiting for {i} seconds for the log-file.")
        time.sleep(1)  # We wait a bit since we need the log file to exist

        # We don't PIPE stdout of the process above because we need a detached
        # process so we tail the log file.
        with suppress(IndexError):
            log_file = glob.glob(log_file_pattern)[0]
            break
    print(f"Found the log-file ({log_file}) in {i} seconds.")

    wait_for_succesful_start(log_file, timeout=timeout)


def start_remote_ipcluster(
    n,
    profile="pbs",
    hostname="hpc05",
    username=None,
    password=None,
    env_path=None,
    timeout=300,
):
    """Starts an `ipcluster` over ssh on `hostname` and wait untill it's
    successfully started.

    Parameters
    ----------
    n : int
        Number of engines to be started.
    profile : str, default 'pbs'
        Profile name of IPython profile.
    hostname : str
        Hostname of machine where the ipcluster runs.
    username : str
        Username to log into `hostname`. If not provided, it tries to look it up in
        your `.ssh/config`.
    password : str
        Password for `ssh username@hostname`.
    env_path : str, default=None
        Path of the Python environment, '/path/to/ENV/' if Python is in `/path/to/ENV/bin/python`.
        Examples '~/miniconda3/envs/dev/', 'miniconda3/envs/dev', '~/miniconda3'.
        Defaults to the environment that is sourced in `.bashrc` or `.bash_profile`.
    timeout : int
        Time for which we try to connect to get all the engines.

    Returns
    -------
    None
    """
    if env_path is None:
        env_path = ""

    with setup_ssh(hostname, username, password) as ssh:
        cmd = f"import hpc05; hpc05.start_ipcluster({n}, '{profile}', '{env_path}', {timeout})"
        cmd = f'python -c "{cmd}"'
        stdin, stdout, stderr = ssh.exec_command(cmd, get_pty=True)
        wait_for_succesful_start(stdout, timeout=timeout)


def connect_ipcluster(
    n,
    profile="pbs",
    hostname="hpc05",
    username=None,
    password=None,
    culler=True,
    culler_args=None,
    env_path=None,
    local=True,
    timeout=300,
    folder=None,
    client_kwargs=None,
):
    """Connect to an `ipcluster` on the cluster headnode.

    Parameters
    ----------
    n : int
        Number of engines to be started.
    profile : str, default 'pbs'
        Profile name of IPython profile.
    hostname : str
        Hostname of machine where the ipcluster runs. If connecting
        via the headnode use: `socket.gethostname()` or set `local=True`.
    username : str
        Username to log into `hostname`. If not provided, it tries to look it up in
        your `.ssh/config`.
    password : str
        Password for `ssh username@hostname`.
    culler : bool
        Controls starting of the culler. Default: True.
    culler_args : str
        Add arguments to the culler. e.g. '--timeout=200'
    env_path : str, default: None
        Path of the Python environment, '/path/to/ENV/' if Python is in /path/to/ENV/bin/python.
        Examples '~/miniconda3/envs/dev/', 'miniconda3/envs/dev', '~/miniconda3'.
        Defaults to the environment that is sourced in `.bashrc` or `.bash_profile`.
    local : bool, default: True
        Connect to the client locally or over ssh. Set it False if
        a connection over ssh is needed.
    timeout : int
        Time for which we try to connect to get all the engines.
    folder : str, optional
        Folder that is added to the path of the engines, e.g. "~/Work/my_current_project".
    client_kwargs : dict
        Keyword arguments that are passed to `hpc05.Client()`.

    Returns
    -------
    client : ipython.Client object
        An IPyparallel client.
    dview : ipyparallel.client.view.DirectView object
        Direct view, equivalent to `client[:]`.
    lview : ipyparallel.client.view.LoadBalancedView
        LoadedBalancedView, equivalent to `client.load_balanced_view()`.
    """
    client = Client(
        profile=profile,
        hostname=hostname,
        username=username,
        password=password,
        culler=culler,
        culler_args=culler_args,
        env_path=env_path,
        local=local,
        timeout=timeout,
        **(client_kwargs or {}),
    )
    print("Connected to the `ipcluster` using an `ipyparallel.Client`.")

    t_start = time.time()
    done = False
    n_engines_old = 0
    while not done:
        n_engines = len(client)
        done = n_engines == n
        with suppress(NoEnginesRegistered):
            # This can happen, we just need to wait a little longer.
            dview = client[:]
        t = int(time.time() - t_start)
        msg = f"Connected to {n_engines} out of {n} engines after {t} seconds."
        print_same_line(msg, new_line_end=(n_engines_old != n_engines))
        if t > timeout:
            raise Exception(
                f"Not all ({n_engines}/{n}) connected after {timeout} seconds."
            )
        n_engines_old = n_engines
        time.sleep(1)

    dview.use_dill()
    lview = client.load_balanced_view()

    if folder is not None:
        print(f"Adding {folder} to path.")
        cmd = f"import sys, os; sys.path.append(os.path.expanduser('{folder}'))"
        dview.execute(cmd).result()

    return client, dview, lview


def start_and_connect(
    n,
    profile="pbs",
    hostname="hpc05",
    culler=True,
    culler_args=None,
    env_path=None,
    local=True,
    timeout=300,
    folder=None,
    client_kwargs=None,
    kill_old_ipcluster=True,
):
    """Start an `ipcluster` locally and connect to it.

    Parameters
    ----------
    n : int
        Number of engines to be started.
    profile : str, default 'pbs'
        Profile name of IPython profile.
    hostname : str
        Hostname of machine where the ipcluster runs. If connecting
        via the headnode use: `socket.gethostname()` or set `local=True`.
    culler : bool
        Controls starting of the culler. Default: True.
    culler_args : str
        Add arguments to the culler. e.g. '--timeout=200'
    env_path : str, default: None
        Path of the Python environment, '/path/to/ENV/' if Python is in /path/to/ENV/bin/python.
        Examples '~/miniconda3/envs/dev/', 'miniconda3/envs/dev', '~/miniconda3'.
        Defaults to the environment that is sourced in `.bashrc` or `.bash_profile`.
    local : bool, default: True
        Connect to the client locally or over ssh. Set it False if
        a connection over ssh is needed.
    timeout : int
        Time for which we try to connect to get all the engines.
    folder : str, optional
        Folder that is added to the path of the engines, e.g. "~/Work/my_current_project".
    client_kwargs : dict
        Keyword arguments that are passed to `hpc05.Client()`.
    kill_old_ipcluster : bool
        If True, it cleansup any old instances of `ipcluster` and kills
        your jobs in qstat or squeue.

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
        print("Killed old intances of ipcluster.")

    start_ipcluster(n, profile, env_path, timeout)

    # all arguments for `connect_ipcluster` except `username` and `password`.
    return connect_ipcluster(
        n,
        profile=profile,
        hostname=hostname,
        culler=culler,
        culler_args=culler_args,
        env_path=env_path,
        local=local,
        timeout=timeout,
        folder=folder,
        client_kwargs=client_kwargs,
    )


def start_remote_and_connect(
    n,
    profile="pbs",
    hostname="hpc05",
    username=None,
    password=None,
    culler=True,
    culler_args=None,
    env_path=None,
    timeout=300,
    folder=None,
    client_kwargs=None,
    kill_old_ipcluster=True,
):
    """Start a remote `ipcluster` on `hostname` and connect to it.

    Parameters
    ----------
    n : int
        Number of engines to be started.
    profile : str, default 'pbs'
        Profile name of IPython profile.
    hostname : str
        Hostname of machine where the ipcluster runs. If connecting
        via the headnode use: `socket.gethostname()` or set `local=True`.
    username : str
        Username to log into `hostname`. If not provided, it tries to look it up in
        your `.ssh/config`.
    password : str
        Password for `ssh username@hostname`.
    culler : bool
        Controls starting of the culler. Default: True.
    culler_args : str
        Add arguments to the culler. e.g. '--timeout=200'
    env_path : str, default: None
        Path of the Python environment, '/path/to/ENV/' if Python is in /path/to/ENV/bin/python.
        Examples '~/miniconda3/envs/dev/', 'miniconda3/envs/dev', '~/miniconda3'.
        Defaults to the environment that is sourced in `.bashrc` or `.bash_profile`.
    timeout : int
        Time for which we try to connect to get all the engines.
    folder : str, optional
        Folder that is added to the path of the engines, e.g. "~/Work/my_current_project".
    client_kwargs : dict
        Keyword arguments that are passed to `hpc05.Client()`.
    kill_old_ipcluster : bool
        If True, it cleansup any old instances of `ipcluster` and kills
        your jobs in qstat or squeue.

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
        print("Killed old intances of ipcluster.")

    start_remote_ipcluster(n, profile, hostname, username, password, env_path, timeout)
    time.sleep(2)

    # all arguments for `connect_ipcluster` except `local`.
    return connect_ipcluster(
        n,
        profile=profile,
        hostname=hostname,
        username=username,
        password=password,
        culler=culler,
        culler_args=culler_args,
        env_path=env_path,
        local=False,
        timeout=timeout,
        folder=folder,
        client_kwargs=client_kwargs,
    )


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
        "scancel --name='ipy-engine-' --user=$USER",  # SLURM
        "scancel --name='ipy-controller-' --user=$USER",  # SLURM
    ]

    if name is not None:
        clean_up_cmds.append(f"scancel --name='{name}' --user=$USER")

    clean_up_cmds = [cmd + " 2> /dev/null" for cmd in clean_up_cmds]

    for cmd in clean_up_cmds:
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, shell=True)
        process.wait()


def kill_remote_ipcluster(hostname="hpc05", username=None, password=None):
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
