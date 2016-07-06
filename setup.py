from setuptools import setup

setup(name='hpc05',
      version='1.0',
      description='Client package for local TU Delft cluster',
      url='https://gitlab.kwant-project.org/cwg/hpc05',
      author='Michael Wimmer and Bas Nijholt',
      license='BSD 2-clause',
      packages=['hpc05'],
      install_requires=['ipyparallel'],
      zip_safe=False)