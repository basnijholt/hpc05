import json
import os
import subprocess
import tempfile
import time
from contextlib import suppress

import ipyparallel
import zmq.ssh

from hpc05.ssh_utils import setup_ssh
from hpc05.utils import bash, on_hostname, print_same_line

import logging

logging.disable(logging.CRITICAL)


def get_culler_cmd(profile="pbs", env_path=None, culler_args=None):
    python = "python"
    if env_path:
        python = os.path.join(os.path.expanduser(env_path), "bin", python)
    if culler_args is None:
        culler_args = ""
    cmd = (
        f"nohup {python} -m hpc05_culler --logging=debug "
        f"--profile={profile} --log_file_prefix=culler.log {culler_args} &"
    )
    return bash(cmd)


class Client(ipyparallel.Client):
    """Return an `ipyparallel.Client` and connect to a remote `ipcluster`
    over ssh if `local=False` and start the engine culler.

    Parameters
    ----------
    profile : str
        profile name, default is 'pbs' which results in
        the folder `~/.ipython/profile_pbs`.
    hostname : str
        Hostname of machine where the ipcluster runs. If connecting
        via the headnode use: `socket.gethostname()` or set `local=True`.
    username : str
        Username to log into `hostname`. If not provided, it tries to look it up in
        your `.ssh/config`.
    password : str
        password for `ssh username@hostname`.
    culler : bool
        Controls starting of the culler. Default: True.
    culler_args : str
        Add arguments to the culler. e.g. '--timeout=200'
    env_path : str, default: None
        Path of the Python environment, '/path/to/ENV/' if Python is in /path/to/ENV/bin/python.
        Examples '~/miniconda3/envs/dev/', 'miniconda3/envs/dev', '~/miniconda3'.
        Defaults to the environment that is sourced in `.bashrc` or `.bash_profile`.
    local : bool, default: False
        Connect to the client locally or over ssh. Set it False if
        a connection over ssh is needed.

    Attributes
    ----------
    json_filename : str
        file name of tmp local json file with connection details.
    tunnel : pexpect.spawn object
        ssh tunnel for making connection to the hpc05.

    Notes
    -----
    You need a profile with PBS (or SLURM) settings in your `.ipython`
    folder on the cluster. You can generate this by running:
        hpc05.create_remote_pbs_profile(username, hostname)
    Then setup a ipcluster on the hpc05 by starting a `screen` and running
        `ipcluster start --n=10 --profile=pbs`.
    """

    def __init__(
        self,
        profile="pbs",
        hostname="hpc05",
        username=None,
        password=None,
        culler=True,
        culler_args=None,
        env_path=None,
        local=False,
        *args,
        **kwargs,
    ):
        culler_cmd = get_culler_cmd(profile, env_path, culler_args=culler_args)

        if local or on_hostname(hostname):
            # Don't connect over ssh if this is run on hostname.
            if culler:
                subprocess.Popen(
                    culler_cmd,
                    shell=True,
                    stdout=open("/dev/null", "w"),
                    stderr=open("logfile.log", "a"),
                )
            super().__init__(profile=profile, *args, **kwargs)
        else:
            import pexpect

            json_file, self.json_filename = tempfile.mkstemp()  # Create temporary file
            os.close(json_file)

            # Try to get the json 10 times.
            remote_json = (
                fr".ipython/profile_{profile}/security/ipcontroller-client.json"
            )
            print_same_line(f"Trying to copy over {remote_json}.")
            for i in range(10):
                print_same_line(f"Trying to copy over {remote_json}. Attempt: {i}/10.")
                with setup_ssh(hostname, username, password) as ssh:
                    with suppress(FileNotFoundError), ssh.open_sftp() as sftp:
                        sftp.chdir(os.path.dirname(remote_json))
                        sftp.get(os.path.basename(remote_json), self.json_filename)
                        break
                if i == 9:
                    raise FileNotFoundError(
                        f'Could not copy the json file: "{remote_json}" of the pbs '
                        "cluster. This could have several reasons, most likely it is "
                        "because the `ipcluster` probably is not running or "
                        "you have no `profile_pbs`, create with "
                        "`hpc05.profile.create_remote_pbs_profile()`."
                    )
                time.sleep(1)
            print_same_line(
                f"Copied over {remote_json} in {i+1} attempt.", new_line_end=True
            )

            # Read the json file
            with open(self.json_filename) as json_file:
                json_data = json.load(json_file)

            keys = ("control", "iopub", "mux", "notification", "registration", "task")

            local_json_data = json_data.copy()
            local_json_data["location"] = "localhost"

            # Select six random ports for the local machine
            local_ports = zmq.ssh.tunnel.select_random_ports(6)
            for port, key in zip(local_ports, keys):
                local_json_data[key] = port

            # Replace remote ports by local ports
            with open(self.json_filename, "w") as json_file:
                json.dump(local_json_data, json_file)

            ips = [
                "{}:{}:{} ".format(
                    local_json_data[key], json_data["location"], json_data[key]
                )
                for key in keys
            ]
            ssh_forward_cmd = (
                "ssh -o ConnectTimeout=10 -N -L " + "-L ".join(ips) + hostname
            )
            self.tunnel = pexpect.spawn(ssh_forward_cmd)
            self.tunnel.expect(
                [pexpect.TIMEOUT, pexpect.EOF, "[Pp]assword", "passphrase"], timeout=6
            )

            if culler:
                # Using `with setup_ssh` here results in the culler not being started.
                ssh = setup_ssh(hostname, username, password)
                ssh.exec_command(culler_cmd, get_pty=True)
            super().__init__(self.json_filename, *args, **kwargs)

        if not on_hostname(hostname):

            def __del__(self):
                if self.tunnel:
                    self.tunnel.close()
