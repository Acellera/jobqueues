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
        from jobqueues.celeryfiles.celery import app

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
        self._arg("jobname", "str", "Job name (identifier)", None, val.String())
        self._app = app
        self._workers = list(app.control.inspect().ping().keys())
        if len(self._workers) == 0:
            logger.error("CeleryQueue found no active workers...")
        else:
            logger.info(
                f"CeleryQueue found the following active workers: {self._workers}"
            )

        self._insp = self._app.control.inspect(self._workers)

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
                dirname,
                0,
                self._sentinel,
                self.datadir,
                self.copy,
                jobname=self.jobname,
            )

    def retrieve(self):
        pass

    def _getTasks(self):
        active = self._insp.active()
        scheduled = self._insp.scheduled()
        reserved = self._insp.reserved()
        tasks = []
        for worker in active.keys():
            tasks += active[worker]
            tasks += scheduled[worker]
            tasks += reserved[worker]
        return tasks

    def inprogress(self):
        tasks = self._getTasks()

        inprog = 0
        for task in tasks:
            if task["kwargs"]["jobname"] == self._jobname:
                inprog += 1
        return inprog

    def stop(self):
        tasks = self._getTasks()

        for task in tasks:
            if task["kwargs"]["jobname"] == self._jobname:
                self._app.control.revoke(task["id"], terminate=True)

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
