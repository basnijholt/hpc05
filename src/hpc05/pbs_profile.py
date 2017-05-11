# Standard library imports
import os
import shutil
import subprocess
import sys

# Third party imports
from IPython.paths import locate_profile

# Local imports
from .ssh_utils import get_info_from_ssh_config, setup_ssh, check_bash_profile

os.environ['SSH_AUTH_SOCK'] = os.path.expanduser('~/ssh-agent.socket')


def line_prepender(filename, line):
    if isinstance(line, list):
        line = "\n".join(line)
    with open(filename, 'r') as f:
        content = f.read()
    with open(filename, 'w') as f:
        f.write(line + '\n' + content)


def create_parallel_profile(profile):
    cmd = [sys.executable, "-E", "-c", "from IPython import start_ipython; start_ipython()",
           "profile", "create", profile, "--parallel"]
    subprocess.check_call(cmd)


def create_pbs_profile(profile='pbs'):
    try:
        shutil.rmtree(os.path.expanduser('~/.ipython/profile_{}'.format(profile)))
    except:
        pass

    create_parallel_profile(profile)

    f = {'ipcluster_config.py': ["c.IPClusterStart.controller_launcher_class = 'PBSControllerLauncher'",
                                 "c.IPClusterEngines.engine_launcher_class = 'PBSEngineSetLauncher'"],
         'ipcontroller_config.py': "c.HubFactory.ip = u'*'",
         'ipengine_config.py': ["c.IPEngineApp.wait_for_url_file = 60",
                                "c.IPEngineApp.startup_command = 'import numpy as np;" +
                                "import kwant, os, sys'"]}

    for fname, line in f.items():
        fname = os.path.join(locate_profile(profile), fname)
        line_prepender(fname, line)


def create_remote_pbs_profile(hostname='hpc05', username=None, password=None, profile="pbs"):
    # Get username from ssh_config
    if username is None:
        try:
            username, hostname = get_info_from_ssh_config(hostname)
        except KeyError:
            raise Exception('hostname not in ~/.ssh/config, enter username')

    # Make ssh connection
    with setup_ssh(hostname, username, password) as ssh:
        source_profile = check_bash_profile(ssh, username)
        cmd = 'python -c "import hpc05; hpc05.pbs_profile.create_pbs_profile(\'{}\')"'
        stdin, stdout, sterr = ssh.exec_command(source_profile + cmd.format(profile))
        return stdout.readlines(), sterr.readlines()
