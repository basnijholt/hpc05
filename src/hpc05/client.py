import logging
logging.disable(logging.CRITICAL)

# Standard library imports
import json
import os
import subprocess
import tempfile

# Third party imports
import ipyparallel
import zmq.ssh

# Local imports
from .ssh_utils import setup_ssh
from .utils import bash, on_hostname


def get_culler_cmd(profile='pbs', env_path=None, culler_args=None):
    python = 'python'
    if env_path:
        python = os.path.join(os.path.expanduser(env_path), 'bin', python)
    cmd = (f'nohup {python} -m hpc05_culler --logging=debug '
           f'--profile={profile} --log_file_prefix=culler.log {culler_args} &')
    return bash(cmd)


class Client(ipyparallel.Client):
    """ipyparallel Client to connect to the hpc05.

    Parameters
    ----------
    hostname : str
        hostname, e.g. `hpc05.tudelft.net` or as in config.
    username : str
        user name at hostname
    password : str
        password for hpc05. NOT RECOMMENDED, use ssh-agent.
    profile : str
        profile name, default results in folder `profile_pbs`.
    culler : bool
        Controls starting of the culler. Default: True.
    culler_args : str
        Add arguments to the culler. e.g. '--timeout=200'
    env_path : str, default=None
        Path of the Python environment, '/path/to/ENV/' if Python is in /path/to/ENV/bin/python.
        Examples '~/miniconda3/envs/dev/', 'miniconda3/envs/dev', '~/miniconda3'.
        Defaults to the environment that is sourced in `.bashrc` or `.bash_profile`.

    Attributes
    ----------
    json_filename : str
        file name of tmp local json file with connection details.
    tunnel : pexpect.spawn object
        ssh tunnel for making connection to the hpc05.

    Notes
    -----
    You have to have a profile with PBS settings in your `.ipython`
    folder on the hpc05. You can generate this by running:
        hpc05.create_remote_pbs_profile(username, hostname)
    Then setup a ipcluster on the hpc05 by starting a screen and running
        ipcluster start --n=10 --profile=pbs
    """

    def __init__(self, hostname='hpc05', username=None, password=None,
                 profile='pbs', culler=True, culler_args=None, env_path=None,
                 *args, **kwargs):

        if culler_args is None:
            culler_args = ''

        if on_hostname(hostname):
            # Don't connect over ssh if this is run on the hpc05.
            if culler:
                cmd = get_culler_cmd(profile, env_path, culler_args=culler_args)
                subprocess.Popen(cmd, shell=True,
                                 stdout=open('/dev/null', 'w'),
                                 stderr=open('logfile.log', 'a'))
            super(Client, self).__init__(profile=profile, *args, **kwargs)

        else:
            import pexpect
            # Create temporary file
            json_file, self.json_filename = tempfile.mkstemp()
            os.close(json_file)

            # Make ssh connection
            ssh = setup_ssh(hostname, username, password)

            # Open SFTP connection and get the ipcontroller-client.json
            with ssh.open_sftp() as sftp:
                remote_json = f".ipython/profile_{profile}/security/ipcontroller-client.json"
                try:
                    sftp.get(remote_json, self.json_filename)
                except FileNotFoundError:
                    raise Exception(
                        f'Could not copy the json file: "{remote_json}"of the pbs '
                        'cluster, the `ipcluster` probably is not running or '
                        'you have no `profile_pbs`, create with '
                        '`hpc05.pbs_profile.create_remote_pbs_profile()`')

            # Read the json file
            with open(self.json_filename) as json_file:
                json_data = json.load(json_file)

            keys = ("control", "iopub", "mux",
                    "notification", "registration", "task")

            local_json_data = json_data.copy()
            local_json_data['location'] = 'localhost'

            # Select six random ports for the local machine
            local_ports = zmq.ssh.tunnel.select_random_ports(6)
            for port, key in zip(local_ports, keys):
                local_json_data[key] = port

            # Replace remote ports by local ports
            with open(self.json_filename, "w") as json_file:
                json.dump(local_json_data, json_file)

            ips = ["{}:{}:{} ".format(local_json_data[key],
                                      json_data['location'],
                                      json_data[key])
                   for key in keys]
            ssh_forward_cmd = ("ssh -o ConnectTimeout=10 -N -L " +
                               "-L ".join(ips) + hostname)
            self.tunnel = pexpect.spawn(ssh_forward_cmd)
            result = self.tunnel.expect([pexpect.TIMEOUT, pexpect.EOF,
                                         "[Pp]assword", "passphrase"],
                                        timeout=6)

            if culler:
                cmd = get_culler_cmd(profile, env_path, culler_args=culler_args)
                ssh.exec_command(cmd, get_pty=True)

            super(Client, self).__init__(self.json_filename, *args, **kwargs)

        if not on_hostname(hostname):
            def __del__(self):
                if self.tunnel:
                    self.tunnel.close()
