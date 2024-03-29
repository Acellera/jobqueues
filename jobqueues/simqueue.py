# (c) 2015-2018 Acellera Ltd http://www.acellera.com
# All Rights Reserved
# Distributed under HTMD Software License Agreement
# No redistribution in whole or part
#
from abc import ABC, abstractmethod
from protocolinterface import ProtocolInterface, val
from jobqueues.util import ensurelist
import logging
import enum

logger = logging.getLogger(__name__)


@enum.unique
class QueueJobStatus(enum.IntEnum):
    """Job status codes"""

    RUNNING = 0
    COMPLETED = 1
    FAILED = 2
    TIMEOUT = 3
    CANCELLED = 4
    PENDING = 5
    OUT_OF_MEMORY = 6

    def describe(self):
        codes = {
            0: "Running",
            1: "Completed",
            2: "Failed",
            3: "Timeout",
            4: "Cancelled",
            5: "Pending",
            6: "Out of memory error",
        }
        return codes[self.value]

    def __str__(self):
        return self.describe()


_inProgressStatus = (QueueJobStatus.RUNNING, QueueJobStatus.PENDING)


class RetrieveError(Exception):
    def __init__(self, value):
        self.value = value

    def __str__(self):
        return repr(self.value)


class SubmitError(Exception):
    def __init__(self, value):
        self.value = value

    def __str__(self):
        return repr(self.value)


class InProgressError(Exception):
    def __init__(self, value):
        self.value = value

    def __str__(self):
        return repr(self.value)


class ProjectNotExistError(Exception):
    def __init__(self, value):
        self.value = value

    def __str__(self):
        return repr(self.value)


class SimQueue(ABC, ProtocolInterface):
    def __init__(self):
        super().__init__()
        ProtocolInterface.__init__(self)
        self._sentinel = "jobqueues.done"
        # For synchronous
        self._dirs = None
        self._arg(
            "runscript",
            "str",
            "Name of the run script to execute",
            "run.sh",
            val.String(),
        )
        self._arg(
            "jobscript",
            "str",
            "Name of the automatically generated job script",
            "job.sh",
            val.String(),
        )

    @abstractmethod
    def retrieve(self):
        """Subclasses need to implement this method"""
        pass

    @abstractmethod
    def submit(self, dirs, commands=None):
        """Subclasses need to implement this method"""
        pass

    def _submitinit(self, dirs):
        dirs = ensurelist(dirs)
        if self._dirs is None:
            self._dirs = []
        self._dirs += dirs
        return dirs

    @abstractmethod
    def inprogress(self):
        """Subclasses need to implement this method"""
        pass

    def wait(self, sentinel=False, sleeptime=5, reporttime=None, reportcallback=None):
        """Blocks script execution until all queued work completes

        Parameters
        ----------
        sentinel : bool
            If False, it relies on the queueing system reporting to determine the number of running jobs. If True, it
            relies on the filesystem, in particular on the existence of a sentinel file for job completion.
        sleeptime : float
            The number of seconds to sleep before re-checking for completed jobs.
        reporttime : float
            If set to a number it will report every `reporttime` seconds the number of non-completed jobs.
            If this argument is larger than `sleepttime`, the method will adjust it to the closest multiple of
            `sleepttime`. If it is shorter than `sleepttime` it will override the `sleepttime` value.
        reportcallback : method
            If not None, the reportcallback method will receive as it's first argument the number of non-completed
            jobs.

        Examples
        --------
        >>> self.wait()
        """
        from time import sleep
        import sys

        if reporttime is not None:
            if reporttime > sleeptime:
                from math import round

                reportfrequency = round(reporttime / sleeptime)
            else:
                reportfrequency = 1
                sleeptime = reporttime

        i = 1
        while True:
            inprog = self.inprogress() if not sentinel else self.notcompleted()
            if reporttime is not None:
                if i == reportfrequency:
                    if reportcallback is not None:
                        reportcallback(inprog)
                    else:
                        logger.info("{} jobs are pending completion".format(inprog))
                    i = 1
                else:
                    i += 1
            self.retrieve()

            if inprog == 0:
                break

            sys.stdout.flush()
            sleep(sleeptime)

    def notcompleted(self):
        """Returns the sum of the number of job directories which do not have the sentinel file for completion.

        Returns
        -------
        total : int
            Total number of directories which have not completed
        """
        import os

        total = 0
        if self._dirs is None:
            raise RuntimeError("This method relies on running synchronously.")
        for i in self._dirs:
            if not os.path.exists(os.path.join(i, self._sentinel)):
                total += 1
        return total

    def _cleanSentinel(self, d):
        import os

        if os.path.exists(os.path.join(d, self._sentinel)):
            try:
                os.remove(os.path.join(d, self._sentinel))
            except Exception:
                logger.warning(f"Could not remove {self._sentinel} sentinel from {d}")
            else:
                logger.debug(f"Removed existing {self._sentinel} sentinel from {d}")

    def _getRunScript(self, d):
        import os

        runscript = os.path.abspath(os.path.join(d, self.runscript))
        if not os.path.exists(runscript):
            raise FileExistsError(f"File {runscript} does not exist.")
        if not os.access(runscript, os.X_OK):
            raise PermissionError(
                f"File {runscript} does not have execution permissions."
            )
        return runscript

    @abstractmethod
    def stop(self):
        """Subclasses need to implement this method"""
        pass

    @property
    @abstractmethod
    def ncpu(self):
        """Subclasses need to have this property"""
        pass

    @ncpu.setter
    @abstractmethod
    def ncpu(self, value):
        """Subclasses need to have this setter"""
        pass

    @property
    @abstractmethod
    def ngpu(self):
        """Subclasses need to have this property"""
        pass

    @ngpu.setter
    @abstractmethod
    def ngpu(self, value):
        """Subclasses need to have this setter"""
        pass

    @property
    @abstractmethod
    def memory(self):
        """Subclasses need to have this property. This property is expected to return a integer in MiB"""
        pass

    @memory.setter
    @abstractmethod
    def memory(self, value):
        """Subclasses need to have this setter"""
        pass
