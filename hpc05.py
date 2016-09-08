import json
from zmq.ssh import tunnel
import pexpect
import tempfile
import os
import ipyparallel
os.environ['SSH_AUTH_SOCK'] = os.path.expanduser('~/ssh-agent.socket')


class HPC05Client(ipyparallel.Client):
    ssh_forward_child = None

    def __init__(self, profile_name="pbs", *args, **kwargs):
        json_file, self.json_filename = tempfile.mkstemp()
        os.close(json_file)

        scp_cmd = ("scp -o ConnectTimeout=10 " +
                   "hpc05:.ipython/profile_{}/security/ipcontroller-client.json ".format(profile_name) +
                   self.json_filename)
        child = pexpect.spawn(scp_cmd)
        result = child.expect([pexpect.EOF, pexpect.TIMEOUT, "[Pp]assword", "passphrase"],
                              timeout=30)
        child.close(force=True)

        if result == 0:
            if child.exitstatus != 0:
                raise RuntimeError("Could not copy json file of pbs cluster: Is cluster running? "
                                   "Or is ssh connection blocked because of too many attempts?")
        elif result == 1:
            raise RuntimeError("scp didn't do anything within 30 seconds (not even fail). Somehow "
                               "scp is blocked.")
        elif result == 2:
            raise RuntimeError(
                "scp asks for a password. System not set up for passwordless ssh.")
        elif result == 3:
            raise RuntimeError(
                "scp asks for a password for the ssh key. No connection to ssh agent.")

        # read the json file and replace remote ports by local ports

        json_file = open(self.json_filename)
        jsondata = json.load(json_file)
        json_file.close()

        newports = tunnel.select_random_ports(6)

        localjsondata = jsondata.copy()
        ssh_forward_cmd = "ssh -o ConnectTimeout=3 -N "
        for i, key in enumerate(("control", "iopub", "mux", "notification", "registration", "task")):
            localjsondata[key] = newports[i]
            ssh_forward_cmd += "-L "
            ssh_forward_cmd += "{0}:{1}:{2} ".format(
                newports[i], jsondata['location'], jsondata[key])

        localjsondata['location'] = 'localhost'
        ssh_forward_cmd += "hpc05"

        json_file = open(self.json_filename, "w")
        json.dump(localjsondata, json_file)
        json_file.close()
        # set up forward of ports via ssh
        self.ssh_forward_child = pexpect.spawn(ssh_forward_cmd)

        # wait longer than connect timeout to allow ssh to make the connection.
        # This is probably not the most elegant way, but I'm not sure how to
        # solve this otherwise - ssh does not give any feedback on when the
        # forward is succesful
        result = self.ssh_forward_child.expect([pexpect.TIMEOUT, pexpect.EOF, "[Pp]assword", "passphrase"],
                                               timeout=6)

        if result == 0:
            # expect timed out after ConnectTimout, so should be OK
            pass
        else:
            self.ssh_forward_child.close(force=True)
            if result == 1:
                if self.ssh_forward_child.exitstatus == 0:
                    raise RuntimeError("Haeh? Tell Michael about that.")
                else:
                    raise RuntimeError(
                        "Could not do ssh tunnel. Over the limit of 3 logins per minute?")
            elif result == 2:
                raise RuntimeError(
                    "ssh asks for a password. System not set up for passwordless ssh.")
            elif result == 3:
                raise RuntimeError(
                    "ssh asks for a password for the ssh key. No connection to ssh agent.")

        ssh_culler_cmd = 'ssh hpc05 "/home/basnijholt/anaconda3/bin/python -m hpc05_culler"'
        self.ssh_culler_child = pexpect.spawn(ssh_culler_cmd)
        result = self.ssh_culler_child.expect([pexpect.TIMEOUT, pexpect.EOF, "[Pp]assword", "passphrase"],
                                              timeout=6)
        if result != 0:
            raise RuntimeError(
                "Something weird went wrong: " + self.ssh_culler_child.before)

        super(HPC05Client, self).__init__(self.json_filename, *args, **kwargs)

    def __del__(self):
        if self.ssh_forward_child:
            self.ssh_forward_child.close(force=True)
        if self.ssh_culler_child:
            self.ssh_culler_child.close(force=True)
