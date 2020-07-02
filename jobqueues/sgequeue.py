# (c) 2015-2019 Acellera Ltd http://www.acellera.com
# All Rights Reserved
# Distributed under HTMD Software License Agreement
# No redistribution in whole or part
#
import os
import shutil
import random
import string
from subprocess import check_output, CalledProcessError, DEVNULL
from protocolinterface import ProtocolInterface, val
from jobqueues.simqueue import SimQueue
from jobqueues.util import ensurelist
from jobqueues.config import loadConfig
from math import ceil
import yaml
import logging

logger = logging.getLogger(__name__)


class SgeQueue(SimQueue, ProtocolInterface):
    """ Queue system for Sun Grid Engine

    #TODO: SGE documentation


    Examples
    --------
    >>> s = SgeQueue()
    >>> s.jobname = 'simulation1'
    >>> s.queue = 'multiscale'
    >>> s.submit('/my/runnable/folder/')  # Folder containing a run.sh bash script
    """

    _defaults = {
        "queue": None,
        "app": None,
        "gpu_queue": None,
        "cpu_queue": None,
        "ngpu": 1,
        "gpu_options": None,
        "ncpu": 1,
        "memory": None,
        "walltime": None,
        "resources": None,
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
            "queue",
            "list",
            "The queue or list of queues to run on. If list, it attempts to submit the job to "
            "the first queue listed",
            self._defaults["queue"],
            val.String(),
            nargs="*",
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
            val.Number(int, "0POS"),
        )
        self._arg(
            "memory",
            "int",
            "Amount of memory per job (MiB)",
            self._defaults["memory"],
            val.Number(int, "0POS"),
        )
        self._arg(
            "walltime",
            "int",
            "Job timeout (hour:min or min)",
            self._defaults["walltime"],
            val.Number(int, "0POS"),
        )
        self._arg(
            "resources",
            "list",
            "Resources of the queue",
            self._defaults["resources"],
            val.String(),
            nargs="*",
        )
        self._cmdDeprecated("environment", "prerun")
        self._arg(
            "outputstream",
            "str",
            "Output stream.",
            "$REQUEST.oJID[.TASKID]",
            val.String(),
        )
        self._arg(
            "errorstream",
            "str",
            "Error stream.",
            "$REQUEST.eJID[.TASKID]",
            val.String(),
        )
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

        # Load SGE configuration profile
        loadConfig(self, "sge", _configfile, _configapp, _logger)

        # Find executables
        if _findExecutables:
            self._qsubmit = SgeQueue._find_binary("qsub")
            self._qinfo = SgeQueue._find_binary("qhost")
            self._qcancel = SgeQueue._find_binary("qdel")
            self._qstatus = SgeQueue._find_binary("qstat")
            self._checkQueue()

    def _checkQueue(self):
        # Check if the slurm daemon is running by executing squeue
        try:
            ret = check_output([self._qstatus])
        except CalledProcessError as e:
            raise RuntimeError(
                f"SGE qstat command failed with error: {e} and errorcode: {e.returncode}"
            )
        except Exception as e:
            raise RuntimeError(f"SGE qstat command failed with error: {e}")

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
            f.write("#$ -N PM{}\n".format(self.jobname))
            f.write('#$ -q "{}"\n'.format(",".join(ensurelist(self.queue))))
            f.write("#$ -pe thread {}\n".format(self.ncpu))
            f.write("#$ -l ngpus={}\n".format(self.ngpu))
            if self.memory is not None:
                f.write("#$ -l h_vmem={}G\n".format(int(ceil(self.memory / 1000))))
            f.write("#$ -wd {}\n".format(workdir))
            # f.write("#$ -o {}\n".format(self.outputstream))
            # f.write("#$ -e {}\n".format(self.errorstream))
            if self.envvars is not None:
                f.write("#$ -v {}\n".format(self.envvars))
            if self.walltime is not None:
                f.write("#$ -l h_rt={}\n".format(self.walltime))
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
                datadir = os.path.abspath(self.datadir)
                if not os.path.isdir(datadir):
                    os.mkdir(datadir)
                simname = os.path.basename(os.path.normpath(workdir))
                # create directory for new file
                odir = os.path.join(datadir, simname)
                os.mkdir(odir)
                f.write("\nmv *.{} {}".format(self.trajext, odir))

        os.chmod(fname, 0o700)

    def retrieve(self):
        # Nothing to do
        pass

    def _autoJobName(self, path):
        return (
            "PM"
            + os.path.basename(os.path.abspath(path))
            + "_"
            + "".join([random.choice(string.digits) for _ in range(5)])
        )

    def submit(self, dirs):
        """ Submits all directories

        Parameters
        ----------
        dirs : list
            A list of executable directories.
        """
        dirs = self._submitinit(dirs)

        if self.queue is None:
            raise ValueError("The queue needs to be defined.")

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
                ret = check_output(self._qsubmit + " < " + jobscript, shell=True)
                logger.debug(ret)
            except CalledProcessError as e:
                logger.error(e.output)
                raise
            except:
                raise

    def _getJobStatusTree(self):
        import xml.etree.ElementTree as ET
        import getpass
        import time

        if self.jobname is None:
            raise ValueError("The jobname needs to be defined.")

        user = getpass.getuser()
        cmd = [self._qstatus, "-u", user, "-xml"]
        if self.queue is not None:
            cmd += ["-q", ",".join(ensurelist(self.queue))]

        logger.debug(cmd)

        # This command randomly fails so I need to allow it to repeat or it crashes adaptive
        tries = 0
        while tries < 3:
            try:
                ret = check_output(cmd, stderr=DEVNULL)
            except CalledProcessError:
                if tries == 2:
                    raise
                tries += 1
                time.sleep(3)
                continue
            break

        logger.debug(ret.decode("ascii"))
        return ET.fromstring(ret.decode("ascii").strip())

    def inprogress(self):
        """ Returns the sum of the number of running and queued workunits of the specific group in the engine.

        Returns
        -------
        total : int
            Total running and queued workunits
        """
        root = self._getJobStatusTree()
        jobs = root.find("queue_info").findall("job_list")
        if len(jobs) == 0:
            return 0

        count = 0
        for job in jobs:
            if job.find("JB_name").text == "PM" + self.jobname:
                count += 1
        return count

    def stop(self):
        """ Cancels all currently running and queued jobs
        """
        root = self._getJobStatusTree()
        jobs = root.find("queue_info").findall("job_list")
        if len(jobs) == 0:
            return

        for job in jobs:
            if job.find("JB_name").text == "PM" + self.jobname:
                jobid = job.find("JB_job_number").text
                cmd = [self._qcancel, jobid]
                logger.debug(cmd)
                ret = check_output(cmd, stderr=DEVNULL)
                logger.debug(ret.decode("ascii"))

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


if __name__ == "__main__":
    # TODO: Create fake binaries for instance creation testing
    """
    q = LsfQueue()
    """
