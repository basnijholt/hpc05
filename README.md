# hpc05
🖥 Client package for local TU Delft cluster

Script that connects to PBS cluster with headnode. Since `ipyparallel` doesn't cull enginges when inactive and people are lazy (because they forget to `qdel` their jobs), it automatically kills the `ipengines` after two hours of inactivity.


Make sure you can connect over `ssh` passwordless:
```
ssh-agent -a ~/ssh-agent.socket
export SSH_AUTH_SOCK=~/ssh-agent.socket
ssh-add
```


Further it assumes the presence of a profile called `pbs`, which can be created on the cluster with:
```
ipython profile create --parallel --profile=pbs
cd .ipython/profile_pbs
```
`nano ipcluster_config.py`
add these lines:
```
c.IPClusterStart.controller_launcher_class = 'PBSControllerLauncher'
c.IPClusterEngines.engine_launcher_class = 'PBSEngineSetLauncher'
```

`nano ipcontroller_config.py`
add this line:
```
`c.HubFactory.ip = u'*'
```

Then start a cluster, run on hpc05:

```
ipcluster start --profile=pbs --n=20
```
