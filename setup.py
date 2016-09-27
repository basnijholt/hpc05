from setuptools import setup

setup(name='hpc05',
      version='1.3',
      description='Client package for local TU Delft cluster',
      url='https://github.com/basnijholt/hpc05',
      author='Michael Wimmer and Bas Nijholt',
      license='BSD 2-clause',
      packages=['hpc05'],
      py_modules=["hpc05_culler"],
      install_requires=['ipyparallel', 'pexpect', 'pyzmq', 'paramiko',
                        'sshtunnel', 'tornado'],
      zip_safe=False)
