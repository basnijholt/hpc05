import contextlib
import os
import shutil
import subprocess
import sys
import textwrap

from IPython.paths import locate_profile

import hpc05_monitor
from hpc05.ssh_utils import setup_ssh


# XXX: 2018-09-24: I used to add
# 'ipcontroller_config.py': "c.HeartMonitor.period = 90000"
# but for some unknown reason the connection time went from
# ~10 s to 180 s.

DEFAULTS = {
    "ipcontroller_config.py": [
        "c.HubFactory.ip = u'*'",
        "c.HubFactory.registration_timeout = 600",
    ],
    "ipengine_config.py": [
        "c.IPEngineApp.wait_for_url_file = 300",
        "c.EngineFactory.timeout = 300",
        "c.IPEngineApp.startup_command = 'import os, sys'",
        "c.IPClusterStart.log_level = 'DEBUG'",
        f"c.IPEngineApp.startup_script = '{hpc05_monitor.__file__}'",
    ],
}


def line_prepender(filename, line):
    if isinstance(line, list):
        line = "\n".join(line)
    with open(filename, "r") as f:
        content = f.read()
    with open(filename, "w") as f:
        f.write(line + "\n" + content)


def add_lines_in_profile(profile, files_lines_dict):
    for fname, line in files_lines_dict.items():
        fname = os.path.join(locate_profile(profile), fname)
        line_prepender(fname, line)


def _remove_parallel_profile(profile):
    with contextlib.suppress(FileNotFoundError):
        path = os.path.expanduser(f"~/.ipython/profile_{profile}")
        shutil.rmtree(path, ignore_errors=True)


def _create_parallel_profile(profile):
    _remove_parallel_profile(profile)
    cmd = [
        sys.executable,
        "-E",
        "-c",
        "from IPython import start_ipython; start_ipython()",
        "profile",
        "create",
        profile,
        "--parallel",
    ]
    subprocess.check_call(cmd)


def create_local_pbs_profile(
    profile="pbs", local_controller=False, custom_template=None
):
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
    import hpc05
    import sys
    custom_template = f'''\\
        #!/bin/sh
        #PBS -t 1-{{n}}
        #PBS -V
        #PBS -N ipengine
        #PBS -l mem=15GB
        {sys.executable} -m ipyparallel.engine --profile-dir="{{profile_dir}}" --cluster-id=""
    '''
    hpc05.create_local_pbs_profile('pbs_15GB',
                                   local_controller=False,
                                   custom_template=custom_template)
    ```
    """
    _create_parallel_profile(profile)

    default_template = f"""\
        #!/bin/sh
        #PBS -t 1-{{n}}
        #PBS -V
        #PBS -N ipengine
        {sys.executable} -m ipyparallel.engine --profile-dir="{{profile_dir}}" --cluster-id=""
        """
    template = textwrap.dedent(custom_template or default_template)

    ipcluster = [
        "c.IPClusterEngines.engine_launcher_class = 'PBSEngineSetLauncher'",
        f'c.PBSEngineSetLauncher.batch_template = """{template}"""',
    ]

    if not local_controller:
        ipcluster.append(
            "c.IPClusterStart.controller_launcher_class = 'PBSControllerLauncher'"
        )

    files_lines_dict = {"ipcluster_config.py": ipcluster, **DEFAULTS}

    add_lines_in_profile(profile, files_lines_dict)

    print(f"Succesfully created a new {profile} profile.")
    print(
        "WARNING: the ipengines of this profile will ALWAYS use this"
        f" environment! ({sys.executable})"
    )


def create_local_slurm_profile(
    profile="slurm", local_controller=False, custom_template=None
):
    """Creata a SLURM profile for ipyparallel.

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
    import hpc05
    custom_template = '''\
        #!/bin/sh
        #SBATCH --ntasks={n}
        #SBATCH --mem-per-cpu=4G
        #SBATCH --job-name=ipy-engine-
        srun ipengine --profile-dir='{profile_dir}' --cluster-id=''
    '''
    hpc05.create_local_pbs_profile('pbs', False, custom_template)
    ```
    """
    _create_parallel_profile(profile)

    default_template = """\
        #!/bin/sh
        #SBATCH --ntasks={n}
        #SBATCH --job-name=ipy-engine-
        srun ipengine --profile-dir='{profile_dir}' --cluster-id=''
        """
    template = textwrap.dedent(custom_template or default_template)

    ipcluster = [
        "c.IPClusterEngines.engine_launcher_class = 'SlurmEngineSetLauncher'",
        f'c.SlurmEngineSetLauncher.batch_template = """{template}"""',
    ]

    if not local_controller:
        ipcluster.append(
            "c.IPClusterStart.controller_launcher_class = 'SlurmControllerLauncher'"
        )

    files_lines_dict = {"ipcluster_config.py": ipcluster, **DEFAULTS}

    add_lines_in_profile(profile, files_lines_dict)

    print(f"Succesfully created a new {profile} profile.")
    print(
        "WARNING: the ipengines of this profile will ALWAYS use this"
        f" environment! ({sys.executable})"
    )


def _create_remote_profile(
    hostname="hpc05",
    username=None,
    password=None,
    profile="pbs",
    local_controller=False,
    custom_template=None,
    batch_type="pbs",
):
    assert batch_type in ("pbs", "slurm")
    if custom_template is not None:
        raise NotImplementedError(
            f"Use `create_local_{batch_type}_profile` on the"
            " cluster locally or implement this function."
        )
    with setup_ssh(hostname, username, password) as ssh:
        cmd = f'import hpc05; hpc05.create_local_{batch_type}_profile("{profile}", {local_controller})'
        cmd = f"python -c '{cmd}'"
        stdin, stdout, stderr = ssh.exec_command(cmd, get_pty=True)
        out, err = stdout.readlines(), stderr.readlines()

        for lines in [out, err]:
            for line in lines:
                print(line.rstrip("\n"))


def create_remote_pbs_profile(
    hostname="hpc05",
    username=None,
    password=None,
    profile="pbs",
    local_controller=False,
    custom_template=None,
):
    _create_remote_profile(
        hostname,
        username,
        password,
        profile,
        local_controller,
        custom_template,
        batch_type="pbs",
    )


def create_remote_slurm_profile(
    hostname="hpc05",
    username=None,
    password=None,
    profile="slurm",
    local_controller=False,
    custom_template=None,
):
    _create_remote_profile(
        hostname,
        username,
        password,
        profile,
        local_controller,
        custom_template,
        batch_type="slurm",
    )
