# hpc05
🖥 `ipyparallel.Client` package for a PBS or SLURM cluster with a headnode.

Script that connects to PBS or SLURM cluster with headnode over ssh. Since `ipyparallel` doesn't cull enginges when inactive and people are lazy (because they forget to `qdel` their jobs), it automatically kills the `ipengines` after the set timeout (default=15 min). Note that this package doesn't only work for the `hpc05` cluster on the TU Delft but also other clusters.

# Installation
First install this package on **both** your machine and the cluster.

```bash
conda config --add channels conda-forge
conda install hpc05
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
hpc05.create_remote_pbs_profile(profile='pbs')  # on the remote machine
# or
hpc05.create_local_pbs_profile(profile='pbs')  # on the cluster

# for SLURM use
hpc05.create_remote_slurm_profile(profile='slurm')  # on the remote machine
# or
hpc05.create_local_slurm_profile(profile='slurm')  # on the cluster
```

# Start `ipcluster` and connect (via `ssh`)
To start **and** connect to an `ipcluster` just do (and read the error messages if any, for instructions):
```python
client, dview, lview = hpc05.start_remote_and_connect(
	n=100, profile='pbs', folder='~/your_folder_on_the_cluster/')
```

This is equivent to the following three commmands:
```python
# 0. Killing and removing files of an old ipcluster (this is optional with
#    the `start_remote_and_connect` function, use the `kill_old_ipcluster` argument)
hpc05.kill_remote_ipcluster()

# 1. starting an `ipcluster`, similar to running
#    `ipcluster start --n=200 --profile=pbs` on the cluster headnode.
hpc05.start_remote_ipcluster(n=200, profile='pbs')

# 2. Connecting to the started ipcluster and adding a folder to the cluster's `PATH`
client, dview, lview = hpc05.connect_ipcluster(
	n=200, profile='pbs', folder='~/your_folder_on_the_cluster/')

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
hpc05_monitor.start(client)

while not hpc05_monitor.latest_data:
    time.sleep(1)

hpc05_monitor.print_usage()  # uses hpc05_monitor.latest_data by default
```


