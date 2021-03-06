from jobqueues.home import home as __home
import os
import logging.config

__version__ = "unpackaged"

try:
    logging.config.fileConfig(
        os.path.join(__home(), "logging.ini"), disable_existing_loggers=False
    )
except:
    print("JobQueues: Logging setup failed")
