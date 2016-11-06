from setuptools import setup
import versioneer

setup(name='hpc05',
      version=versioneer.get_version(),
      cmdclass=versioneer.get_cmdclass(),
      description='Client package for local TU Delft cluster',
      url='https://github.com/basnijholt/hpc05',
      author='Michael Wimmer and Bas Nijholt',
      license='BSD 2-clause',
      package_dir={'': 'src'},
      packages=['hpc05'],
      py_modules=["hpc05_culler"],
      install_requires=['ipyparallel', 'pexpect', 'pyzmq', 'paramiko',
                        'sshtunnel', 'tornado', 'psutil'],
      zip_safe=False)
