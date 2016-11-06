# Standard library imports
import os
import shutil
import subprocess
import sys

# Third party imports
from IPython.paths import locate_profile, get_ipython_dir
from IPython.core.profiledir import ProfileDir

# Local imports
from .ssh_utils import get_info_from_ssh_config, setup_ssh, check_bash_profile

os.environ['SSH_AUTH_SOCK'] = os.path.expanduser('~/ssh-agent.socket')


def line_prepender(filename, line):
    if isinstance(line, list):
        line = "\n".join(line)
    with open(filename, 'r') as f:
        content = f.read()
        f.seek(0, 0)
        f.write(line.rstrip('\r\n') + '\n' + content)


def create_pbs_profile(profile='pbs'):
    shutil.rmtree(os.path.expanduser('~/.ipython/profile_{}'.format(profile)))
    subprocess.check_call('ipython profile create --parallel --profile={}'.format(profile))

    f = {'ipcluster_config.py': ["c.IPClusterStart.controller_launcher_class = 'PBSControllerLauncher'", 
                                 "c.IPClusterEngines.engine_launcher_class = 'PBSEngineSetLauncher'"],
         'ipcontroller_config.py': "c.HubFactory.ip = u'*'",
         'ipengine_config.py': "c.IPEngineApp.wait_for_url_file = 60"}

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
