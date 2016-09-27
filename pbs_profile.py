import sys
import subprocess
from IPython.paths import locate_profile, get_ipython_dir
from IPython.core.profiledir import ProfileDir
import os
import shutil

def create_base_ipython_dirs():
    """Create default user directories to prevent potential race conditions downstream.
    """
    os.makedirs(get_ipython_dir(), exist_ok=True)
    ProfileDir.create_profile_dir_by_name(get_ipython_dir())


def create_throwaway_profile(profile):
    cmd = [sys.executable, "-E", "-c", "from IPython import start_ipython; start_ipython()",
           "profile", "create", profile, "--parallel"]
    subprocess.check_call(cmd)
    return profile


def delete_profile(profile):
    MAX_TRIES = 10
    dir_to_remove = locate_profile(profile)
    if os.path.exists(dir_to_remove):
        num_tries = 0
        while True:
            try:
                shutil.rmtree(dir_to_remove)
                break
            except OSError:
                if num_tries > MAX_TRIES:
                    raise
                time.sleep(5)
                num_tries += 1
    else:
        raise ValueError("Cannot find {0} to remove, "
                         "something is wrong.".format(dir_to_remove))


def line_prepender(filename, line):
    if isinstance(line, list):
        line = "\n".join(line)
    with open(filename, 'r+') as f:
        content = f.read()
        f.seek(0, 0)
        f.write(line.rstrip('\r\n') + '\n' + content)


def create_pbs_profile(profile='pbs'):
    create_base_ipython_dirs()
    delete_profile(profile)
    create_throwaway_profile(profile)
    f = {'ipcluster_config.py': ["c.IPClusterStart.controller_launcher_class = 'PBSControllerLauncher'", 
                                 "c.IPClusterEngines.engine_launcher_class = 'PBSEngineSetLauncher'"],
         'ipcontroller_config.py': "c.HubFactory.ip = u'*'",
         'ipengine_config.py': "c.IPEngineApp.wait_for_url_file = 60"}

    for fname, line in f.items():
        fname = os.path.join(locate_profile(profile), fname)
        line_prepender(fname, line)
