import json
from zmq.ssh import tunnel
import pexpect
import tempfile
import os
import ipyparallel
from sshtunnel import SSHTunnelForwarder
import paramiko
from paramiko.ssh_exception import PasswordRequiredException
os.environ['SSH_AUTH_SOCK'] = os.path.expanduser('~/ssh-agent.socket')


class HPC05Client(ipyparallel.Client):

    def __init__(self, username, hostname, password=None, profile_name="pbs", *args, **kwargs):
        # Create temporary file
        json_file, self.json_filename = tempfile.mkstemp()
        os.close(json_file)

        # Make ssh connection
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        try:
            ssh.connect(hostname, username=username, allow_agent=True,
                        password=password)
        except PasswordRequiredException:
            raise Exception('Enter `password` argument or run `rm -f ~/ssh-agent.socket; ssh-agent -a ~/ssh-agent.socket;' +
                            'export SSH_AUTH_SOCK=~/ssh-agent.socket; ssh-add` on the local machine')

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

        ssh.exec_command('nohup /home/basnijholt/anaconda3/bin/python -m hpc05_culler')

        super(HPC05Client, self).__init__(self.json_filename, *args, **kwargs)

    def __del__(self):
        if self.tunnel:
            self.tunnel.close()
