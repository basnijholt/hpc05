#!/usr/bin/env python

from setuptools import setup


# Loads _version.py module without importing the whole package.
def get_version_and_cmdclass(package_name):
    import os
    from importlib.util import module_from_spec, spec_from_file_location

    spec = spec_from_file_location(
        "version", os.path.join("src", package_name, "_version.py")
    )
    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.__version__, module.cmdclass


version, cmdclass = get_version_and_cmdclass("hpc05")


setup(
    name="hpc05",
    version=version,
    cmdclass=cmdclass,
    description="Client package for PBS and SLURM clusters with a headnode.",
    url="https://github.com/basnijholt/hpc05",
    author="Bas Nijholt",
    license="MIT",
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
