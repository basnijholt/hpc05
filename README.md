# hpc05
[![PyPI](https://img.shields.io/pypi/v/hpc05.svg)](https://pypi.python.org/pypi/hpc05)
[![Conda](https://anaconda.org/conda-forge/hpc05/badges/installer/conda.svg)](https://anaconda.org/conda-forge/hpc05)
[![Downloads](https://anaconda.org/conda-forge/hpc05/badges/downloads.svg)](https://anaconda.org/conda-forge/hpc05)

🖥 `ipyparallel.Client` package for a PBS or SLURM cluster with a headnode.

Script that connects to PBS or SLURM cluster with headnode over ssh. Since `ipyparallel` doesn't cull enginges when inactive and people are lazy (because they forget to `qdel` their jobs), it automatically kills the `ipengines` after the set timeout (default=15 min). Note that this package doesn't only work for the `hpc05` cluster on the TU Delft but also other clusters.

# Installation
First install this package on **both** your machine and the cluster.

```bash
conda config --add channels conda-forge
conda install hpc05
```
or using `pip`
```
pip install hpc05
```

Make sure you can connect over `ssh` passwordless by copying your ssh key:

```bash
ssh-copy-id hpc05
```

# Setup profile
You need a parallel profile on your cluster, which can be created by the following command on your local machine:
```python
import hpc05
# for PBS use
hpc05.create_remote_pbs_profile(profile='pbs', hostname='hpc05')  # on the remote machine
# or
hpc05.create_local_pbs_profile(profile='pbs')  # on the cluster

# for SLURM use
hpc05.create_remote_slurm_profile(profile='slurm', hostname='hpc05')  # on the remote machine
# or
hpc05.create_local_slurm_profile(profile='slurm')  # on the cluster
```

# Start `ipcluster` and connect (via `ssh`)
To start **and** connect to an `ipcluster` just do (and read the error messages if any, for instructions):
```python
client, dview, lview = hpc05.start_remote_and_connect(
	n=100, profile='pbs', hostname='hpc05', folder='~/your_folder_on_the_cluster/')
```

This is equivent to the following three commmands:
```python
# 0. Killing and removing files of an old ipcluster (this is optional with
#    the `start_remote_and_connect` function, use the `kill_old_ipcluster` argument)
hpc05.kill_remote_ipcluster(hostname='hpc05')

# 1. starting an `ipcluster`, similar to running
#    `ipcluster start --n=100 --profile=pbs` on the cluster headnode.
hpc05.start_remote_ipcluster(n=100, profile='pbs', hostname='hpc05')

# 2. Connecting to the started ipcluster and adding a folder to the cluster's `PATH`
client, dview, lview = hpc05.connect_ipcluster(
	n=200, profile='pbs', hostname='hpc05', folder='~/your_folder_on_the_cluster/')

```


# Start `ipcluster` and connect (on cluster headnode)
To start **and** connect to an `ipcluster` just do (and read the error messages if any, for instructions):
```python
client, dview, lview = hpc05.start_and_connect(
	n=100, profile='pbs',  folder='~/your_folder_on_the_cluster/')
```

This is equivent to the following three commmands:
```python
# 0. Killing and removing files of an old ipcluster (this is optional with
#    the `start_remote_and_connect` function, use the `kill_old_ipcluster` argument)
hpc05.kill_ipcluster()

# 1. starting an `ipcluster`, similar to `ipcluster start --n=200 --profile=pbs`
hpc05.start_ipcluster(n=200, profile='pbs')

# 2. Connecting to the started ipcluster and adding a folder to the cluster's `PATH`
client, dview, lview = hpc05.connect_ipcluster(
	n=200, profile='pbs', folder='~/your_folder_on_the_cluster/')

```

# Monitor resources
This package will monitor your resources if you start it with `hpc05_monitor.start(client)`, see the following example use:
```python
import time
import hpc05_monitor
hpc05_monitor.start(client, interval=5)  # update hpc05_monitor.MAX_USAGE every 'interval' seconds.

while not hpc05_monitor.LATEST_DATA:
    time.sleep(1)

hpc05_monitor.print_usage()  # uses hpc05_monitor.LATEST_DATA by default

hpc05_monitor.print_max_usage()  # uses hpc05_monitor.MAX_USAGE
```

With output:
```
 id hostname             date                             CPU% MEM%
 15 node29.q1cluster     2018-09-10T14:25:05.350499       190%   3%
 19 node29.q1cluster     2018-09-10T14:25:04.860693       200%   3%
 26 node29.q1cluster     2018-09-10T14:25:05.324466       200%   3%
 28 node29.q1cluster     2018-09-10T14:25:05.148623       190%   2%
 29 node29.q1cluster     2018-09-10T14:25:04.737664       190%   3%
 ...
```


## Development

We use [pre-commit](https://pre-commit.com) for linting of the code, so `pip install pre_commit` and run
```
pre-commit install
```
in the repository.
