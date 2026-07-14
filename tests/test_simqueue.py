import re
from jobqueues.slurmqueue import SlurmQueue


def _test_get_jobscript_name_default_base():
    sq = SlurmQueue(_findExecutables=False)
    name = sq._getJobScriptName()
    assert re.match(r"^job_\d{8}-\d{6}_[0-9a-f]{8}\.sh$", name)


def _test_get_jobscript_name_custom_base():
    sq = SlurmQueue(_findExecutables=False)
    sq.jobscript = "custom.sh"
    name = sq._getJobScriptName()
    assert re.match(r"^custom_\d{8}-\d{6}_[0-9a-f]{8}\.sh$", name)
