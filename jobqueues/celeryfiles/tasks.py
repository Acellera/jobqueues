from jobqueues.celeryfiles.celery import app
from celery.exceptions import SoftTimeLimitExceeded
import psutil


def kill(proc_pid):
    process = psutil.Process(proc_pid)
    for proc in process.children(recursive=True):
        proc.kill()
    process.kill()


@app.task
def run_simulation(folder, deviceid, sentinel, datadir, copyextensions, jobname=None):
    import subprocess
    import os
    import time

    runsh = os.path.join(folder, "run.sh")
    jobsh = os.path.join(folder, "job.sh")
    stdfile = os.path.join(folder, "celery.out")
    _createJobScript(jobsh, folder, runsh, deviceid, sentinel, datadir, copyextensions)

    # Sleep for a short bit so that the OS can pick up on the new file before executing it
    time.sleep(0.2)

    process = None
    try:
        with open(stdfile, "a") as fout:
            process = subprocess.Popen(
                ["/bin/sh", jobsh], stdout=fout, stderr=fout, shell=False
            )
            _ = process.communicate()
    except SoftTimeLimitExceeded:
        # The SoftTimeLimitExceeded exception is a hack because SIGTERM doesn't work in Celery. See celeryqueue.py comment.
        if process is not None:
            kill(process.pid)
        print(f"Job {jobname} has been cancelled by the user")
    except Exception as e:
        raise e


def _createJobScript(
    fname, workdir, runsh, deviceid, sentinel, datadir, copyextensions
):
    import os

    with open(fname, "w") as f:
        f.write("#!/bin/bash\n\n")
        f.write(
            '\ntrap "touch {}" EXIT SIGTERM SIGINT\n'.format(
                os.path.normpath(os.path.join(workdir, sentinel))
            )
        )
        f.write("\n")
        if deviceid is not None:
            f.write("export CUDA_VISIBLE_DEVICES={}\n\n".format(deviceid))

        f.write("cd {}\n".format(os.path.abspath(workdir)))
        f.write("{}".format(runsh))

        # Move completed trajectories
        if datadir is not None:
            datadir = os.path.abspath(datadir)
            os.makedirs(datadir, exist_ok=True)
            simname = os.path.basename(os.path.normpath(workdir))
            # create directory for new file
            odir = os.path.join(datadir, simname)
            os.makedirs(odir, exist_ok=True)
            if os.path.abspath(odir) != os.path.abspath(workdir):
                f.write("\nmv {} {}".format(" ".join(copyextensions), odir))

    os.chmod(fname, 0o700)
