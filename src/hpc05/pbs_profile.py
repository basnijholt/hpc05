# Standard library imports
import os
import shutil
import subprocess
import sys

# Third party imports
from IPython.paths import locate_profile

# Local imports
from .ssh_utils import get_info_from_ssh_config, setup_ssh
from .utils import bash


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


def create_pbs_profile(profile='pbs', local_controller=True):
    try:
        shutil.rmtree(os.path.expanduser(f'~/.ipython/profile_{profile}'))
    except:
        pass

    create_parallel_profile(profile)

    ipcluster = ["c.IPClusterEngines.engine_launcher_class = 'PBSEngineSetLauncher'"]

    if not local_controller:
        ipcluster += ["c.IPClusterStart.controller_launcher_class = 'PBSControllerLauncher'"]

    f = {'ipcluster_config.py': ipcluster,
         'ipcontroller_config.py': "c.HubFactory.ip = u'*'",
         'ipengine_config.py': ["c.IPEngineApp.wait_for_url_file = 60",
                                "c.IPEngineApp.startup_command = 'import numpy as np;" +
                                "import kwant, os, sys'"]}

    for fname, line in f.items():
        fname = os.path.join(locate_profile(profile), fname)
        line_prepender(fname, line)

    print(f'Succesfully created a new {profile} profile.')


def create_remote_pbs_profile(hostname='hpc05', username=None,
                              password=None, profile="pbs"):
    with setup_ssh(hostname, username, password) as ssh:
        cmd = f'import hpc05; hpc05.pbs_profile.create_pbs_profile("{profile}")'
        cmd = f"python -c '{cmd}'"
        stdin, stdout, stderr = ssh.exec_command(cmd, get_pty=True)
        out, err = stdout.readlines(), stderr.readlines()

        for lines in [out, err]:
            for line in lines:
                print(line.rstrip('\n'))
