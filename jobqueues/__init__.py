from jobqueues.home import home as __home
import os
import logging.config
from jobqueues import _version

__version__ = _version.get_versions()["version"]

try:
    logging.config.fileConfig(
        os.path.join(__home(), "logging.ini"), disable_existing_loggers=False
    )
except Exception:
    print("JobQueues: Logging setup failed")
