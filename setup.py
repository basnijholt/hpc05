from setuptools import setup

setup(name='hpc05',
      version='1.1',
      description='Client package for local TU Delft cluster',
      url='https://gitlab.kwant-project.org/cwg/hpc05',
      author='Michael Wimmer and Bas Nijholt',
      license='BSD 2-clause',
      py_modules=["hpc05", "hpc05_culler"],
      install_requires=['ipyparallel', 'pexpect', 'pyzmq'],
      zip_safe=False)