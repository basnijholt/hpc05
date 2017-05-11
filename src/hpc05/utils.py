import subprocess
from .ssh_utils import setup_ssh
import sys


def get_local_env(env=None):
    if env is None:
        env = sys.exec_prefix.split('/')[-1]  # conda environment name
    cmd = 'conda list --export -n {}'.format(env).split()
    local_env = subprocess.check_output(cmd).decode('utf-8')
    local_env = [l for l in local_env.split('\n')
                 if not l.startswith('# ') and l != '']
    return local_env


def get_remote_env(env=None):
    ssh = setup_ssh()
    cmd = 'conda list --export'
    if env:
        cmd += " -n {}".format(env)
    stdin, stdout, sterr = ssh.exec_command(cmd)
    remote_env = [l[:-1] for l in stdout.readlines() if not l.startswith('# ')]
    return remote_env


def check_difference_in_envs(local_env_name=None, remote_env_name=None):
    """Only works when setting the Python env in .bash_profile or .bash_rc on the
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
