import logging
logging.disable(logging.CRITICAL)

# Standard library imports
import json
import os
import tempfile

# Third party imports
import ipyparallel
from sshtunnel import SSHTunnelForwarder
from zmq.ssh import tunnel

# Local imports
from .pbs_profile import create_remote_pbs_profile
from .ssh_utils import get_info_from_ssh_config, setup_ssh, check_bash_profile
os.environ['SSH_AUTH_SOCK'] = os.path.expanduser('~/ssh-agent.socket')


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
    profile_name : str
        profile name, default results in folder `profile_pbs`.

    Attributes
    ----------
    json_filename : str
        file name of tmp local json file with connection details.
    tunnel : SSHTunnelForwarder object
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
        profile_name='pbs', culler=True, *args, **kwargs):
        # Create temporary file
        json_file, self.json_filename = tempfile.mkstemp()
        os.close(json_file)

        # Get username from ssh_config
        if username is None:
            try:
                username, hostname = get_info_from_ssh_config(hostname)
            except KeyError:
                raise Exception('hostname not in ~/.ssh/config, enter username')

        # Make ssh connection
        ssh = setup_ssh(hostname, username, password)

        # Open SFTP connection and get the ipcontroller-client.json
        with ssh.open_sftp() as sftp:
            profile_dir = "/home/{}/.ipython/profile_{}/".format(username, profile_name)
            remote_json = profile_dir + "security/ipcontroller-client.json"
            try:
                sftp.get(remote_json, self.json_filename)
            except FileNotFoundError:
                raise Exception('Could not copy json file of pbs cluster, the `ipcluster` probably is not running.' +
                                'or you have no `profile_pbs`, create with `hpc05.pbs_profile.create_remote_pbs_profile()`')

        # Read the json file
        with open(self.json_filename) as json_file:
            json_data = json.load(json_file)

        # Select six random ports for the local machine
        local_ports = tunnel.select_random_ports(6)
        local_addresses = [('', port) for port in local_ports]  # Format for SSHTunnelForwarder
        local_json_data = json_data.copy()
        local_json_data['location'] = 'localhost'

        keys = ("control", "iopub", "mux", "notification", "registration", "task")
        remote_addresses = [(json_data['location'], json_data[key]) for key in keys]

        for port, key in zip(local_ports, keys):
            local_json_data[key] = port

        # Replace remote ports by local ports
        with open(self.json_filename, "w") as json_file:
            json.dump(local_json_data, json_file)

        self.tunnel = SSHTunnelForwarder(hostname, ssh_username=username,
                                         local_bind_addresses=local_addresses,
                                         remote_bind_addresses=remote_addresses)
        self.tunnel.start()
        
        if culler:
            source_profile = check_bash_profile(ssh, username)
            python_cmd = 'nohup python -m hpc05_culler --logging=debug --profile={} --log_file_prefix=~/culler.log &'
            ssh.exec_command(source_profile + python_cmd.format(profile_name))

        super(Client, self).__init__(self.json_filename, *args, **kwargs)


    def __del__(self):
        if self.tunnel:
            self.tunnel.close()
