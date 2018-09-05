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
hpc05.create_remote_pbs_profile(hostname='hpc05')  # on the remote machine
# or
hpc05.create_local_pbs_profile(hostname='hpc05')  # on the cluster
```

# Start `ipcluster` and connect (via `ssh`)
To start **and** connect to an `ipcluster` just do (and read the error messages if any, for instructions):
```python
client, dview, lview = hpc05.start_remote_and_connect(
	n=100, profile='pbs', folder='~/your_folder_on_the_cluster/')
```

This is equivent to the following three commmands:
```python
# 1. starting an `ipcluster`, similar to `ipcluster start --n=200 --profile=pbs`
hpc05.start_remote_ipcluster(n=200, profile='pbs')

# 2. Connecting to the started ipcluster and adding a folder to the cluster's `PATH`
client, dview, lview = hpc05.connect_ipcluster(
	n=200, profile='pbs', folder='~/your_folder_on_the_cluster/')

# 3. Killing and removing files of an old ipcluster (this is optional with
#    the `start_remote_and_connect` function, use the `kill_old_ipcluster` argument)
hpc05.kill_remote_ipcluster()
```


# Start `ipcluster` and connect (on cluster headnode)
To start **and** connect to an `ipcluster` just do (and read the error messages if any, for instructions):
```python
client, dview, lview = hpc05.start_and_connect(
	n=100, profile='pbs',  folder='~/your_folder_on_the_cluster/')
```

This is equivent to the following three commmands:
```python
# 1. starting an `ipcluster`, similar to `ipcluster start --n=200 --profile=pbs`
hpc05.start_ipcluster(n=200, profile='pbs')

# 2. Connecting to the started ipcluster and adding a folder to the cluster's `PATH`
client, dview, lview = hpc05.connect_ipcluster(
	n=200, profile='pbs', folder='~/your_folder_on_the_cluster/')

# 3. Killing and removing files of an old ipcluster (this is optional with
#    the `start_remote_and_connect` function, use the `kill_old_ipcluster` argument)
hpc05.kill_ipcluster()
```
