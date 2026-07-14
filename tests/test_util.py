import re
from jobqueues.util import _generateUniqueJobScriptName


def _test_generate_unique_jobscript_name():
    name1 = _generateUniqueJobScriptName("job.sh")
    name2 = _generateUniqueJobScriptName("job.sh")
    pattern = r"^job_\d{8}-\d{6}_[0-9a-f]{8}\.sh$"
    assert re.match(pattern, name1)
    assert re.match(pattern, name2)
    assert name1 != name2


def _test_generate_unique_jobscript_name_no_extension():
    name = _generateUniqueJobScriptName("myjob")
    assert re.match(r"^myjob_\d{8}-\d{6}_[0-9a-f]{8}$", name)
