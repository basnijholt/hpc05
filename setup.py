#!/usr/bin/env python

from setuptools import setup
import versioneer

setup(
    name="hpc05",
    version=versioneer.get_version(),
    cmdclass=versioneer.get_cmdclass(),
    description="Client package for PBS and SLURM clusters with a headnode.",
    url="https://github.com/basnijholt/hpc05",
    author="Bas Nijholt",
    license="BSD 2-clause",
    package_dir={"": "src"},
    packages=["hpc05"],
    py_modules=["hpc05_culler", "hpc05_monitor"],
    install_requires=[
        "ipyparallel",
        "pexpect",
        "pyzmq",
        "paramiko",
        "tornado",
        "psutil",
    ],
    zip_safe=False,
)
