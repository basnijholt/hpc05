# Standard library imports
import json
import os
import tempfile

# Third party imports
import ipyparallel
import paramiko
from paramiko.ssh_exception import PasswordRequiredException
from sshtunnel import SSHTunnelForwarder
from zmq.ssh import tunnel

# Local imports
import hpc05
from hpc05.config import remote_python_path
os.environ['SSH_AUTH_SOCK'] = os.path.expanduser('~/ssh-agent.socket')


def setup_ssh(username, hostname, password=None):
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        ssh.connect(hostname, username=username, allow_agent=True,
                    password=password)
    except PasswordRequiredException:
        raise Exception('Enter `password` argument or run `rm -f ~/ssh-agent.socket; ssh-agent -a ~/ssh-agent.socket;' +
                        'export SSH_AUTH_SOCK=~/ssh-agent.socket; ssh-add` on the local machine')
    return ssh


class HPC05Client(ipyparallel.Client):
    """ipyparallel Client to connect to the hpc05.

    Parameters
    ----------
    username : str
        user name at hpc05
    hostname : str
        hostname, e.g. `hpc05.tudelft.net` or as in config.
    password : str
        password for hpc05. NOT RECOMMENDED, use ssh-agent.
    profile_name : str
        profile name, default results in folder `profile_pbs`.
    create_new_profile : bool
        Generates new parallel profile at hpc05.

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
    def __init__(self, username, hostname='hpc05', password=None,
        profile_name="pbs", create_new_profile=False, *args, **kwargs):
        # Create temporary file
        json_file, self.json_filename = tempfile.mkstemp()
        os.close(json_file)

        # Make ssh connection
        ssh = setup_ssh(username, hostname, password)

        # Create new profile on remote location
        if create_new_profile:
            hpc05.create_remote_pbs_profile(username, hostname, password, profile_name)

        # Open SFTP connection and get the ipcontroller-client.json
        with ssh.open_sftp() as sftp:
            profile_dir = "/home/{}/.ipython/profile_{}/".format(username, profile_name)
            remote_json = profile_dir + "security/ipcontroller-client.json"
            try:
                sftp.get(remote_json, self.json_filename)
            except FileNotFoundError:
                raise Exception('Could not copy json file of pbs cluster, the `ipcluster` probably is not running.')

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

        self.tunnel = SSHTunnelForwarder(hostname, local_bind_addresses=local_addresses,
                                         remote_bind_addresses=remote_addresses)
        self.tunnel.start()

        ssh.exec_command('nohup {} -m hpc05_culler'.format(remote_python_path))

        super(HPC05Client, self).__init__(self.json_filename, *args, **kwargs)


    def __del__(self):
        if self.tunnel:
            self.tunnel.close()
