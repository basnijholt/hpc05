import os
from ._version import get_versions

__all__ = []

available = [('client', ['Client']),
             ('profile', ['create_local_pbs_profile',
                          'create_remote_pbs_profile',
                          'create_local_slurm_profile',
                          'create_remote_slurm_profile']),
             ('utils', ['check_difference_in_envs']),
             ('connect', ['start_ipcluster',
                          'start_remote_ipcluster',
                          'connect_ipcluster',
                          'start_and_connect',
                          'start_remote_and_connect',
                          'kill_remote_ipcluster'])]

for module, names in available:
    exec('from .{0} import {1}'.format(module, ', '.join(names)))
    __all__.extend(names)

__version__ = get_versions()['version']

os.environ['SSH_AUTH_SOCK'] = os.path.expanduser('~/ssh-agent.socket')
