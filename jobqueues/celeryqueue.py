from jobqueues.localqueue import LocalGPUQueue
from protocolinterface import ProtocolInterface, val
import os
import logging


logger = logging.getLogger(__name__)


class CeleryQueue(LocalGPUQueue):
    """ Beta: Queue with support for Celery local queueing

    Start a celery server with:
    >>> docker run -d -p 5462:5672 rabbitmq
    >>> celery --app=jobqueues.celeryfiles.celery worker --loglevel=info -Q gpu,celery -c 1
    """

    def __init__(self, _configapp=None, _configfile=None):
        super().__init__()
        self._arg(
            "datadir",
            "str",
            "The path in which to store completed trajectories.",
            None,
            val.String(),
        )
        self._arg(
            "copy",
            "list",
            "A list of file names or globs for the files to copy to datadir",
            ("*.xtc",),
            val.String(),
            nargs="*",
        )
        self._arg("jobname", "str", "UNUSED: Job name (identifier)", None, val.String())
        self._tasks = []

    def submit(self, dirs):
        from jobqueues.celeryfiles.tasks import run_simulation

        dirs = self._submitinit(dirs)

        for d in dirs:
            if not os.path.isdir(d):
                raise NameError("Submit: directory " + d + " does not exist.")

        # if all folders exist, submit
        for d in dirs:
            dirname = os.path.abspath(d)
            logger.info("Queueing " + dirname)

            runscript = self._getRunScript(dirname)
            self._cleanSentinel(dirname)

            async_res = run_simulation.delay(
                dirname, 0, self._sentinel, self.datadir, self.copy
            )
            self._tasks.append(async_res)

    def retrieve(self):
        pass

    def inprogress(self):
        inprog = 0
        for t in self._tasks:
            if t.state in ("PENDING", "STARTED", "RETRY"):
                inprog += 1
        return inprog

    def stop(self):
        for t in self._tasks:
            t.revoke(terminate=True)

    @property
    def ngpu(self):
        return NotImplementedError

    @ngpu.setter
    def ngpu(self, value):
        raise NotImplementedError

    @property
    def ncpu(self):
        return NotImplementedError

    @ncpu.setter
    def ncpu(self, value):
        raise NotImplementedError

    @property
    def memory(self):
        return NotImplementedError

    @memory.setter
    def memory(self, value):
        raise NotImplementedError
