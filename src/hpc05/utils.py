#!/usr/bin/env python

import glob
import os.path
import socket
import subprocess
import sys
import time

from .ssh_utils import setup_ssh


def on_hostname(hostname='hpc05'):
    return socket.gethostname() == hostname


def bash(cmd):
    # https://stackoverflow.com/a/25099813
    return f'/bin/bash -i -c "{cmd}"'


def get_local_env(env=None):
    if env is None:
        env = sys.exec_prefix.split('/')[-1]  # conda environment name
    cmd = f'conda list --export -n {env}'.split()
    local_env = subprocess.check_output(cmd).decode('utf-8')
    local_env = [l for l in local_env.split('\n')
                 if not l.startswith('# ') and l != '']
    return local_env


def get_remote_env(env=None):
    with setup_ssh() as ssh:
        cmd = 'conda list --export'
        if env:
            cmd += f" -n {env}"
        stdin, stdout, stderr = ssh.exec_command(cmd, get_pty=True)
        remote_env = [l[:-1] for l in stdout.readlines() if not l.startswith('# ')]
    return remote_env


def check_difference_in_envs(local_env_name=None, remote_env_name=None):
    """Only works when setting the Python env in your .bash_rc on the
    remote machine."""
    local_env = get_local_env(local_env_name)
    remote_env = get_remote_env(remote_env_name)
    not_on_remote = set(remote_env) - set(local_env)
    not_on_local = set(local_env) - set(remote_env)

    not_on_remote = [p + ' is installed on remote machine' for p in not_on_remote]
    not_on_local = [p + ' is installed on local machine' for p in not_on_local]

    def diff(first, second):
        second = [package.split('=')[0] for i, package in enumerate(second)]
        return sorted([v for v in first if v.split('=')[0] not in second])

    return {'missing_packages_on_remote': diff(not_on_local, not_on_remote),
            'missing_packages_on_local': diff(not_on_remote, not_on_local),
            'mismatches': sorted(not_on_local + not_on_remote)}


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
                              '`hpc05.utils.kill_remote_ipcluster()` or use '
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

    wait_for_succesful_start(proc.stdout, decode=True)


def start_remote_ipcluster(n, profile='pbs', hostname='hpc05',
                           username=None, password=None, timeout=60):
    with setup_ssh(hostname, username, password) as ssh:
        cmd = f"import hpc05; hpc05.utils.start_ipcluster({n}, '{profile}')"
        cmd = f'python -c "{cmd}"'
        stdin, stdout, stderr = ssh.exec_command(cmd, get_pty=True)
        wait_for_succesful_start(stdout, decode=False, timeout=timeout)


def kill_remote_ipcluster(hostname='hpc05', username=None, password=None):
    with setup_ssh(hostname, username, password) as ssh:
        stdin, stdout, stderr = ssh.exec_command('del')
        try:
            lines = stdout.readlines()
            for line in lines:
                print(line)
        except:
            pass
