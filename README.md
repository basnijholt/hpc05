# hpc05
🖥 `ipyparallel` Client package for a PBS or SLURM cluster with a headnode.

Script that connects to PBS or SLURM cluster with headnode. Since `ipyparallel` doesn't cull enginges when inactive and people are lazy (because they forget to `qdel` their jobs), it automatically kills the `ipengines` after the set timeout (default=15 min). Note that this package doesn't only work for the `hpc05` cluster on the TU Delft but also other clusters.

First install this package on **both** your machine and the cluster.

```
conda config --add channels conda-forge
conda install hpc05
```

Make sure you can connect over `ssh` passwordless by copying your ssh key:

```
ssh-copy-id hpc05
```

Then add the key to a ssh-agent by running:
```
ssh-agent -a ~/ssh-agent.socket
export SSH_AUTH_SOCK=~/ssh-agent.socket
ssh-add
```

Further, you need a parallel profile called `pbs` on the `hpc05`, which can be created by the following command on your local machine:
```
import hpc05
hpc05.create_remote_pbs_profile(hostname='hpc05')
```

Then start a cluster (preferably in a screen), run on hpc05:

```
screen -S pbs
ipcluster start --profile=pbs --n=20
```

Now you can connect to the cluster by:
```
import hpc05
hpc05.Client(hostname='hpc05')
```
