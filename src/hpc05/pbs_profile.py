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

def create_base_ipython_dirs():
    """Create default user directories to prevent potential race conditions downstream.
    """
    os.makedirs(get_ipython_dir(), exist_ok=True)
    ProfileDir.create_profile_dir_by_name(get_ipython_dir())


def create_parallel_profile(profile_name):
    cmd = [sys.executable, "-E", "-c", "from IPython import start_ipython; start_ipython()",
           "profile", "create", profile_name, "--parallel"]
    subprocess.check_call(cmd)
    return profile_name


def delete_profile(profile_name):
    MAX_TRIES = 10
    dir_to_remove = locate_profile(profile_name)
    if os.path.exists(dir_to_remove):
        num_tries = 0
        while True:
            try:
                shutil.rmtree(dir_to_remove)
                break
            except OSError:
                if num_tries > MAX_TRIES:
                    raise
                time.sleep(5)
                num_tries += 1
    else:
        raise ValueError("Cannot find {0} to remove, "
                         "something is wrong.".format(dir_to_remove))


def line_prepender(filename, line):
    if isinstance(line, list):
        line = "\n".join(line)
    with open(filename, 'r+') as f:
        content = f.read()
        f.seek(0, 0)
        f.write(line.rstrip('\r\n') + '\n' + content)


def create_pbs_profile(profile_name='pbs'):
    create_base_ipython_dirs()
    try:
        delete_profile(profile_name)
    except OSError:
        pass
    create_parallel_profile(profile_name)
    f = {'ipcluster_config.py': ["c.IPClusterStart.controller_launcher_class = 'PBSControllerLauncher'", 
                                 "c.IPClusterEngines.engine_launcher_class = 'PBSEngineSetLauncher'"],
         'ipcontroller_config.py': "c.HubFactory.ip = u'*'",
         'ipengine_config.py': "c.IPEngineApp.wait_for_url_file = 60"}

    for fname, line in f.items():
        fname = os.path.join(locate_profile(profile_name), fname)
        line_prepender(fname, line)


def create_remote_pbs_profile(hostname='hpc05', username=None, password=None, profile_name="pbs"):
    # Get username from ssh_config
    if username is None:
        try:
            username, hostname = get_info_from_ssh_config(hostname)
        except KeyError:
            raise Exception('hostname not in ~/.ssh/config, enter username')

    # Make ssh connection
    with setup_ssh(hostname, username, password) as ssh:
        source_profile = check_bash_profile(ssh, username)
        cmd = 'python -c "import hpc05; hpc05.pbs_profile.create_pbs_profile()"'
        stdin, stdout, sterr = ssh.exec_command(source_profile + cmd.format(profile_name))
        return stdout.readlines(), sterr.readlines()
