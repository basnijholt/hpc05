#!/usr/bin/env python

import sys
from setuptools import find_packages, setup


if sys.version_info < (3, 6):
    print("hpc05 requires Python 3.6 or above.")
    sys.exit(1)


# Loads _version.py module without importing the whole package.
def get_version_and_cmdclass(package_name):
    import os
    from importlib.util import module_from_spec, spec_from_file_location

    spec = spec_from_file_location("version", os.path.join(package_name, "_version.py"))
    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.__version__, module.cmdclass


version, cmdclass = get_version_and_cmdclass("hpc05")

with open("README.md") as f:
    readme = f.read()

extras_require = dict(
    docs=[
        "sphinx",
        "sphinx-rtd-theme",
        "m2r",  # markdown support
        "sphinxcontrib.apidoc",  # run sphinx-apidoc when building docs
    ],
    dev=["pre-commit"],
)

install_requires = ["ipyparallel", "pexpect", "pyzmq", "paramiko", "tornado", "psutil"]


setup(
    name="hpc05",
    version=version,
    cmdclass=cmdclass,
    python_requires=">=3.6",
    classifiers=[
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.7",
    ],
    description="Client package for PBS and SLURM clusters with a headnode.",
    long_description=readme,
    long_description_content_type="text/markdown",
    url="https://github.com/basnijholt/hpc05",
    author="Bas Nijholt",
    author_email="basnijholt@gmail.com",
    license="MIT",
    packages=find_packages("."),
    py_modules=["hpc05_culler", "hpc05_monitor"],
    install_requires=install_requires,
    extras_require=extras_require,
    zip_safe=False,
)
