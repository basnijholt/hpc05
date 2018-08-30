# Standard library imports
import contextlib
import os
import shutil
import subprocess
import sys
import textwrap

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


def _create_parallel_profile(profile):
    cmd = [sys.executable, "-E", "-c", "from IPython import start_ipython; start_ipython()",
           "profile", "create", profile, "--parallel"]
    subprocess.check_call(cmd)


def create_pbs_profile(profile='pbs', local_controller=False, custom_template=None):
    """Creata a PBS profile for ipyparallel.

    Parameters
    ----------
    profile : str
        Profile name.
    local_controller : bool
        Create a ipcontroller on a seperate node if True and locally if False.
    custom_template : str
        A custom job script template, see the example below.

    Examples
    --------
    By default no memory is specified, using the following `custom_template`
    allows you to request a certain amount of memory.

    ```python
    custom_template = '''\
        #!/bin/sh
        #PBS -t 1-{n}
        #PBS -V
        #PBS -N ipengine
        #PBS -l mem=4GB
        python -m ipyparallel.engine --profile-dir="{profile_dir}" --cluster-id=""
    '''
    ```
    """
    with contextlib.suppress(FileNotFoundError):
        path = os.path.expanduser(f'~/.ipython/profile_{profile}')
        shutil.rmtree(path, ignore_errors=True)

    _create_parallel_profile(profile)

    default_template = """\
        #!/bin/sh
        #PBS -t 1-{n}
        #PBS -V
        #PBS -N ipengine
        python -m ipyparallel.engine --profile-dir="{profile_dir}" --cluster-id=""
        """
    template = textwrap.dedent(custom_template or default_template)

    ipcluster = ["c.IPClusterEngines.engine_launcher_class = 'PBSEngineSetLauncher'",
                f'c.PBSEngineSetLauncher.batch_template = """{template}"""']

    if not local_controller:
        ipcluster.append("c.IPClusterStart.controller_launcher_class = 'PBSControllerLauncher'")

    f = {'ipcluster_config.py': ipcluster,
         'ipcontroller_config.py': ["c.HubFactory.ip = u'*'",
                                    "c.HubFactory.registration_timeout = 600",
                                    "c.HeartMonitor.period = 90000"],
         'ipengine_config.py': ["c.IPEngineApp.wait_for_url_file = 300",
                                "c.EngineFactory.timeout = 300",
                                "c.IPEngineApp.startup_command = 'import os, sys'"]}

    for fname, line in f.items():
        fname = os.path.join(locate_profile(profile), fname)
        line_prepender(fname, line)

    print(f'Succesfully created a new {profile} profile.')


def create_remote_pbs_profile(hostname='hpc05', username=None,
                              password=None, profile="pbs", local_controller=False,
                              custom_template=None):
    if custom_template is not None:
        raise NotImplementedError('Use `create_pbs_profile` locally or implement this.')
    with setup_ssh(hostname, username, password) as ssh:
        cmd = f'import hpc05; hpc05.create_pbs_profile("{profile}", {local_controller})'
        cmd = f"python -c '{cmd}'"
        stdin, stdout, stderr = ssh.exec_command(cmd, get_pty=True)
        out, err = stdout.readlines(), stderr.readlines()

        for lines in [out, err]:
            for line in lines:
                print(line.rstrip('\n'))
