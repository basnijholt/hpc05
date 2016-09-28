__all__ = []
available = [('hpc05', ['HPC05Client']),
             ('pbs_profile',
             ['create_pbs_profile', 'create_remote_pbs_profile'])]
for module, names in available:
    exec('from .{0} import {1}'.format(module, ', '.join(names)))
    __all__.extend(names)
