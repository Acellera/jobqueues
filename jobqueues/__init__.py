from jobqueues.home import home as __home
import os
import logging.config
from importlib.metadata import version, PackageNotFoundError

# from importlib.resources import files

try:
    __version__ = version("jobqueues")
except PackageNotFoundError:
    pass


try:
    logging.config.fileConfig(
        os.path.join(__home(), "logging.ini"), disable_existing_loggers=False
    )
except Exception:
    print("JobQueues: Logging setup failed")
