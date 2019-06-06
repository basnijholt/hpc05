import os.path
import paramiko
from paramiko.ssh_exception import PasswordRequiredException, SSHException


def get_info_from_ssh_config(hostname):
    user_config_file = os.path.expanduser("~/.ssh/config")
    ssh_config = paramiko.SSHConfig()
    if os.path.exists(user_config_file):
        with open(user_config_file) as f:
            ssh_config.parse(f)
    cfg = ssh_config.lookup(hostname)
    full_hostname = cfg["hostname"]
    username = cfg["user"]
    proxy = (
        paramiko.ProxyCommand(cfg["proxycommand"]) if "proxycommand" in cfg else None
    )
    return username, full_hostname, proxy


def setup_ssh(hostname="hpc05", username=None, password=None):
    if username is None:
        try:
            username, hostname, proxy = get_info_from_ssh_config(hostname)
        except KeyError:
            raise Exception("hostname not in ~/.ssh/config, enter username")
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        ssh.connect(
            hostname, username=username, allow_agent=True, password=password, sock=proxy
        )
    except (PasswordRequiredException, SSHException):
        msg = [
            "Enter `password` argument or run",
            "rm -f ~/ssh-agent.socket; ssh-agent -a ~/ssh-agent.socket; "
            "export SSH_AUTH_SOCK=~/ssh-agent.socket; ssh-add",
            "on the local machine",
        ]
        raise Exception("\n".join(msg))
    return ssh
