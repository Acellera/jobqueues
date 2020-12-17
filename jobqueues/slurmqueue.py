# (c) 2015-2018 Acellera Ltd http://www.acellera.com
# All Rights Reserved
# Distributed under HTMD Software License Agreement
# No redistribution in whole or part
#
import os
import shutil
import random
import string
from jobqueues.config import loadConfig
import yaml
from subprocess import check_output, CalledProcessError
from protocolinterface import ProtocolInterface, val
from jobqueues.simqueue import SimQueue, QueueJobStatus, _inProgressStatus
from jobqueues.util import ensurelist
import getpass
import logging

logger = logging.getLogger(__name__)


JOB_STATE_CODES = {
    "BOOT_FAIL": QueueJobStatus.FAILED,
    "CANCELLED": QueueJobStatus.CANCELLED,
    "COMPLETED": QueueJobStatus.COMPLETED,
    "DEADLINE": QueueJobStatus.FAILED,
    "FAILED": QueueJobStatus.FAILED,
    "NODE_FAIL": QueueJobStatus.FAILED,
    "OUT_OF_MEMORY": QueueJobStatus.OUT_OF_MEMORY,
    "PENDING": QueueJobStatus.PENDING,
    "PREEMPTED": QueueJobStatus.PENDING,
    "RUNNING": QueueJobStatus.RUNNING,
    "REQUEUED": QueueJobStatus.PENDING,
    "RESIZING": QueueJobStatus.PENDING,
    "REVOKED": QueueJobStatus.FAILED,
    "SUSPENDED": QueueJobStatus.PENDING,
    "TIMEOUT": QueueJobStatus.TIMEOUT,
}


class SlurmQueue(SimQueue, ProtocolInterface):
    """Queue system for SLURM

    Parameters
    ----------
    jobname : str, default=None
        Job name (identifier)
    partition : str or list of str, default=None
        The queue (partition) or list of queues to run on. If list, the one offering earliest initiation will be used.
    priority : str, default=None
        Job priority
    ngpu : int, default=1
        Number of GPUs to use for a single job
    ncpu : int, default=1
        Number of CPUs to use for a single job
    memory : int, default=1000
        Amount of memory per job (MiB)
    gpumemory : int, default=None
        Only run on GPUs with at least this much memory. Needs special setup of SLURM. Check how to define gpu_mem on
        SLURM.
    walltime : int, default=None
        Job timeout (s)
    mailtype : str, default=None
        When to send emails. Separate options with commas like 'END,FAIL'.
    mailuser : str, default=None
        User email address.
    outputstream : str, default='slurm.%N.%j.out'
        Output stream.
    errorstream : str, default='slurm.%N.%j.err'
        Error stream.
    datadir : str, default=None
        The path in which to store completed trajectories.
    trajext : str, default='xtc'
        Extension of trajectory files. This is needed to copy them to datadir.
    nodelist : list, default=None
        A list of nodes on which to run every job at the *same time*! Careful! The jobs will be duplicated!
    exclude : list, default=None
        A list of nodes on which *not* to run the jobs. Use this to select nodes on which to allow the jobs to run on.
    envvars : str, default='ACEMD_HOME,HTMD_LICENSE_FILE'
        Envvars to propagate from submission node to the running node (comma-separated)
    prerun : list, default=None
        Shell commands to execute on the running node before the job (e.g. loading modules)

    Examples
    --------
    >>> s = SlurmQueue()
    >>> s.partition = 'multiscale'
    >>> s.submit('/my/runnable/folder/')  # Folder containing a run.sh bash script
    """

    _defaults = {
        "partition": None,
        "priority": None,
        "ngpu": 1,
        "ncpu": 1,
        "memory": 1000,
        "walltime": None,
        "envvars": "ACEMD_HOME,HTMD_LICENSE_FILE",
        "prerun": None,
    }

    def __init__(
        self, _configapp=None, _configfile=None, _findExecutables=True, _logger=True
    ):
        SimQueue.__init__(self)
        ProtocolInterface.__init__(self)
        self._arg("jobname", "str", "Job name (identifier)", None, val.String())
        self._arg(
            "partition",
            "str",
            "The queue (partition) or list of queues to run on. If list, the one offering "
            "earliest initiation will be used.",
            self._defaults["partition"],
            val.String(),
            nargs="*",
        )
        self._arg(
            "priority", "str", "Job priority", self._defaults["priority"], val.String()
        )
        self._arg(
            "ngpu",
            "int",
            "Number of GPUs to use for a single job",
            self._defaults["ngpu"],
            val.Number(int, "0POS"),
        )
        self._arg(
            "ncpu",
            "int",
            "Number of CPUs to use for a single job",
            self._defaults["ncpu"],
            val.Number(int, "POS"),
        )
        self._arg(
            "memory",
            "int",
            "Amount of memory per job (MiB)",
            self._defaults["memory"],
            val.Number(int, "POS"),
        )
        self._arg(
            "gpumemory",
            "int",
            "Only run on GPUs with at least this much memory. Needs special setup of SLURM. "
            "Check how to define gpu_mem on SLURM.",
            None,
            val.Number(int, "0POS"),
        )
        self._arg(
            "walltime",
            "int",
            "Job timeout (minutes)",
            self._defaults["walltime"],
            val.Number(int, "POS"),
        )
        self._cmdDeprecated("environment", "envvars")
        self._arg(
            "mailtype",
            "str",
            "When to send emails. Separate options with commas like 'END,FAIL'.",
            None,
            val.String(),
        )
        self._arg("mailuser", "str", "User email address.", None, val.String())
        self._arg(
            "outputstream", "str", "Output stream.", "slurm.%N.%j.out", val.String()
        )
        self._arg(
            "errorstream", "str", "Error stream.", "slurm.%N.%j.err"
        ), val.String()
        self._arg(
            "datadir",
            "str",
            "The path in which to store completed trajectories.",
            None,
            val.String(),
        )
        self._arg(
            "trajext",
            "str",
            "Extension of trajectory files. This is needed to copy them to datadir.",
            "xtc",
            val.String(),
        )
        self._arg(
            "nodelist",
            "list",
            "A list of nodes on which to run every job at the *same time*! Careful! The jobs"
            " will be duplicated!",
            None,
            val.String(),
            nargs="*",
        )
        self._arg(
            "exclude",
            "list",
            "A list of nodes on which *not* to run the jobs. Use this to select nodes on "
            "which to allow the jobs to run on.",
            None,
            val.String(),
            nargs="*",
        )
        self._arg(
            "envvars",
            "str",
            "Envvars to propagate from submission node to the running node (comma-separated)",
            self._defaults["envvars"],
            val.String(),
        )
        self._arg(
            "prerun",
            "list",
            "Shell commands to execute on the running node before the job (e.g. "
            "loading modules)",
            self._defaults["prerun"],
            val.String(),
            nargs="*",
        )
        self._arg(
            "account",
            "str",
            "Charge resources used by the jobs to specified account.",
            None,
            val.String(),
        )
        self._arg(
            "user",
            "str",
            "The SLURM user submitting and managing jobs",
            getpass.getuser(),
            val.String(),
        )

        # Load Slurm configuration profile
        loadConfig(self, "slurm", _configfile, _configapp, _logger)

        # Find executables
        if _findExecutables:
            self._qsubmit = SlurmQueue._find_binary("sbatch")
            self._qinfo = SlurmQueue._find_binary("sinfo")
            self._qcancel = SlurmQueue._find_binary("scancel")
            self._qstatus = SlurmQueue._find_binary("squeue")
            self._qjobinfo = SlurmQueue._find_binary("sacct")
            self._checkQueue()

    def _checkQueue(self):
        # Check if the slurm daemon is running by executing squeue
        try:
            ret = check_output([self._qstatus])
        except CalledProcessError as e:
            raise RuntimeError(
                f"SLURM squeue command failed with error: {e} and errorcode: {e.returncode}"
            )
        except Exception as e:
            raise RuntimeError(f"SLURM squeue command failed with error: {e}")

    @staticmethod
    def _find_binary(binary):
        ret = shutil.which(binary, mode=os.X_OK)
        if not ret:
            raise FileNotFoundError(
                "Could not find required executable [{}]".format(binary)
            )
        ret = os.path.abspath(ret)
        return ret

    def _createJobScript(self, fname, workdir, runsh):
        workdir = os.path.abspath(workdir)
        with open(fname, "w") as f:
            f.write("#!/bin/bash\n")
            f.write("#\n")
            f.write("#SBATCH --job-name={}\n".format(self.jobname))
            f.write(
                "#SBATCH --partition={}\n".format(",".join(ensurelist(self.partition)))
            )
            if self.ngpu != 0:
                f.write("#SBATCH --gres=gpu:{}".format(self.ngpu))
                if self.gpumemory is not None:
                    f.write(",gpu_mem:{}".format(self.gpumemory))
                f.write("\n")
            f.write("#SBATCH --cpus-per-task={}\n".format(self.ncpu))
            f.write("#SBATCH --mem={}\n".format(self.memory))
            f.write("#SBATCH --priority={}\n".format(self.priority))
            f.write(
                "#SBATCH -D {}\n".format(workdir)
            )  # Don't use the long version. Depending on SLURM version it's workdir or chdir
            f.write("#SBATCH --output={}\n".format(self.outputstream))
            f.write("#SBATCH --error={}\n".format(self.errorstream))
            if self.envvars is not None:
                f.write("#SBATCH --export={}\n".format(self.envvars))
            if self.walltime is not None:
                f.write("#SBATCH --time={}\n".format(self.walltime))
            if self.mailtype is not None and self.mailuser is not None:
                f.write("#SBATCH --mail-type={}\n".format(self.mailtype))
                f.write("#SBATCH --mail-user={}\n".format(self.mailuser))
            if self.nodelist is not None:
                f.write(
                    "#SBATCH --nodelist={}\n".format(
                        ",".join(ensurelist(self.nodelist))
                    )
                )
            if self.exclude is not None:
                f.write(
                    "#SBATCH --exclude={}\n".format(",".join(ensurelist(self.exclude)))
                )
            if self.account is not None:
                f.write("#SBATCH --account={}\n".format(self.account))
            # Trap kill signals to create sentinel file
            f.write(
                '\ntrap "touch {}" EXIT SIGTERM\n'.format(
                    os.path.normpath(os.path.join(workdir, self._sentinel))
                )
            )
            f.write("\n")
            if self.prerun is not None:
                for call in ensurelist(self.prerun):
                    f.write("{}\n".format(call))
            f.write("\ncd {}\n".format(workdir))
            f.write("{}".format(runsh))

            # Move completed trajectories
            if self.datadir is not None:
                simname = os.path.basename(os.path.normpath(workdir))
                datadir = os.path.abspath(os.path.join(self.datadir, simname))
                os.makedirs(datadir, exist_ok=True)
                f.write(f"\nmv *.{self.trajext} {datadir}")

        os.chmod(fname, 0o700)

    def retrieve(self):
        # Nothing to do
        pass

    def _autoJobName(self, path):
        return (
            os.path.basename(os.path.abspath(path))
            + "_"
            + "".join([random.choice(string.digits) for _ in range(5)])
        )

    def submit(self, dirs):
        """Submits all directories

        Parameters
        ----------
        dirs : list
            A list of executable directories.
        """
        dirs = self._submitinit(dirs)

        if self.partition is None:
            raise ValueError("The partition needs to be defined.")

        # if all folders exist, submit
        for d in dirs:
            logger.info("Queueing " + d)

            if self.jobname is None:
                self.jobname = self._autoJobName(d)

            runscript = self._getRunScript(d)
            self._cleanSentinel(d)

            jobscript = os.path.abspath(os.path.join(d, "job.sh"))
            self._createJobScript(jobscript, d, runscript)
            try:
                ret = check_output([self._qsubmit, jobscript])
                logger.debug(ret)
            except CalledProcessError as e:
                logger.error(e.output)
                raise
            except:
                raise

    def _robust_check_output(self, cmd, maxtries=3):
        # Attempts multiple times to execute the command before failing. This is to handle connection issues to SLURM
        import time

        tries = 0
        while tries < maxtries:
            try:
                ret = check_output(cmd)
            except CalledProcessError:
                if tries == (maxtries - 1):
                    raise
                tries += 1
                time.sleep(3)
                continue
            break
        return ret

    def inprogress(self):
        """Returns the sum of the number of running and queued workunits of the specific group in the engine.

        Returns
        -------
        total : int
            Total running and queued workunits
        """
        import time

        if self.jobname is None:
            raise ValueError("The jobname needs to be defined.")

        cmd = [
            self._qstatus,
            "-n",
            self.jobname,
            "-u",
            self.user,
        ]
        if self.partition is not None:
            cmd += ["--partition", ",".join(ensurelist(self.partition))]

        logger.debug(cmd)
        ret = self._robust_check_output(cmd).decode("ascii")
        logger.debug(ret)

        # Count the number of lines returned by squeue as number of "in progress" jobs
        lines = ret.splitlines()
        inprog = max(0, len(lines) - 1)

        # Check also with sacct because squeue sometimes fails to report the right number
        try:
            info = [
                key
                for key, val in self.jobInfo().items()
                if val["state"] in _inProgressStatus
            ]
            if len(info) != inprog:
                logger.warning(
                    f"squeue and sacct gave different number of running jobs ({inprog}/{len(info)}) with name {self.jobname}. Using the max of the two."
                )
            inprog = max(inprog, len(info))
        except Exception as e:
            logger.warning(f"Failed to get jobInfo with error: {e}")

        return inprog

    def stop(self):
        """Cancels all currently running and queued jobs"""
        if self.jobname is None:
            raise ValueError("The jobname needs to be defined.")

        if self.partition is not None:
            for q in ensurelist(self.partition):
                cmd = [self._qcancel, "-n", self.jobname, "-u", self.user, "-p", q]
                logger.debug(cmd)
                ret = check_output(cmd)
                logger.debug(ret.decode("ascii"))
        else:
            cmd = [self._qcancel, "-n", self.jobname, "-u", self.user]
            logger.debug(cmd)
            ret = check_output(cmd)
            logger.debug(ret.decode("ascii"))

    def jobInfo(self):
        from jobqueues.simqueue import QueueJobStatus

        if self.jobname is None:
            raise ValueError("The jobname needs to be defined.")

        cmd = [
            self._qjobinfo,
            "--name",
            self.jobname,
            "-u",
            self.user,
            "-o",
            "JobID,JobName,State,ExitCode,Reason,Timelimit",
            "-P",
            "-X",
        ]
        if self.partition is not None:
            cmd += ["--partition", ",".join(ensurelist(self.partition))]

        logger.debug(cmd)
        ret = self._robust_check_output(cmd).decode("ascii")
        logger.debug(ret)

        # TODO: Is there a specific exit code for this?
        if "Slurm accounting storage is disabled" in ret:
            raise RuntimeError("Slurm accounting is disabled. Cannot get job info.")

        lines = ret.splitlines()
        if len(lines) < 2:
            return None

        info = {}
        for line in lines[1:]:
            jobid, _, state, exitcode, reason, timelimit = line.split("|")

            if state in JOB_STATE_CODES:
                state = JOB_STATE_CODES[state]
            else:
                raise RuntimeError(f'Unknown SLURM job state "{state}"')

            info[jobid] = {
                "state": state,
                "exitcode": exitcode,
                "reason": reason,
                "timelimit": timelimit,
            }

        return info

    @property
    def ncpu(self):
        return self.__dict__["ncpu"]

    @ncpu.setter
    def ncpu(self, value):
        self.ncpu = value

    @property
    def ngpu(self):
        return self.__dict__["ngpu"]

    @ngpu.setter
    def ngpu(self, value):
        self.ngpu = value

    @property
    def memory(self):
        return self.__dict__["memory"]

    @memory.setter
    def memory(self, value):
        self.memory = value


import unittest


class _TestSlurmQueue(unittest.TestCase):
    def test_config(self):
        from jobqueues.home import home
        import os

        configfile = os.path.join(home(), "config_slurm.yml")
        with open(configfile, "r") as f:
            reference = yaml.load(f, Loader=yaml.FullLoader)

        for appkey in reference:
            sq = SlurmQueue(
                _configapp=appkey, _configfile=configfile, _findExecutables=False
            )
            for key in reference[appkey]:
                assert (
                    sq.__getattribute__(key) == reference[appkey][key]
                ), f'Config setup of SlurmQueue failed on app "{appkey}" and key "{key}""'


if __name__ == "__main__":
    unittest.main(verbosity=2)
