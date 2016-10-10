from ._version import get_versions
__all__ = []
available = [('client', ['Client']),
             ('pbs_profile',
             ['create_pbs_profile', 'create_remote_pbs_profile'])]
for module, names in available:
    exec('from .{0} import {1}'.format(module, ', '.join(names)))
    __all__.extend(names)

HPC05Client = Client

__version__ = get_versions()['version']
