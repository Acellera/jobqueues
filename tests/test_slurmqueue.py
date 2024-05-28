from pytest import fixture
from distutils import dir_util
from jobqueues.slurmqueue import SlurmQueue
import yaml
import re
import os


@fixture
def datadir(tmpdir, request):
    """
    Fixture responsible for searching a folder with the same name of test
    module and, if available, moving all contents to a temporary directory so
    tests can use them freely.
    """
    filename = request.module.__file__
    test_dir, _ = os.path.splitext(filename)

    if os.path.isdir(test_dir):
        dir_util.copy_tree(test_dir, str(tmpdir))

    return tmpdir


def _create_execdir(tmpdir):
    os.makedirs(tmpdir)
    run_sh = os.path.join(tmpdir, "run.sh")
    with open(run_sh, "w") as f:
        f.write("sleep 5\n")
    os.chmod(run_sh, 0o700)
    return tmpdir


def _compare_jobsh(jobsh, expected, datadir):
    with open(expected, "r") as f:
        expected = f.read().strip()

    with open(jobsh, "r") as f:
        jobsh = f.read()
        jobsh = jobsh.replace(str(datadir), "TESTDIR_PLACEHOLDER")
        jobsh = re.sub(
            r"#SBATCH --job-name=\w+\n", "#SBATCH --job-name=XXXXX\n", jobsh
        ).strip()
        jobsh = jobsh.replace("\\", "/")

    assert jobsh == expected


def _test_config(datadir):
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


def _test_submit_command(datadir):
    execdir = str(datadir.join("0"))
    os.makedirs(execdir, exist_ok=True)

    sl = SlurmQueue(_findExecutables=False)
    sl.partition = "jobqueues_test"
    sl.ngpu = 2
    sl.gpumemory = 2000
    sl.exclude = ["node1", "node4"]
    sl.nodelist = ["node2"]
    sl.envvars = "TEST=3"
    sl.useworkdir = False

    sl.submit([execdir], commands=["sleep 5"], _dryrun=True)

    _compare_jobsh(
        os.path.join(execdir, "job.sh"), datadir.join("_submit_command.sh"), datadir
    )


def _test_submit_folder(datadir):
    execdir = _create_execdir(str(datadir.join("0")))

    sl = SlurmQueue(_findExecutables=False)
    sl.partition = "jobqueues_test"
    sl.ngpu = 2
    sl.gpumemory = 2000
    sl.exclude = ["node1", "node4"]
    sl.nodelist = ["node2"]
    sl.envvars = "TEST=3"
    sl.submit(execdir, _dryrun=True)

    _compare_jobsh(
        os.path.join(execdir, "job.sh"), datadir.join("_submit_folder.sh"), datadir
    )


def _test_submit_multi_folder(datadir):
    sl = SlurmQueue(_findExecutables=False)
    sl.partition = "jobqueues_test"
    sl.ngpu = 2
    sl.gpumemory = 2000
    sl.exclude = ["node1", "node4"]
    sl.nodelist = ["node2"]
    sl.envvars = "TEST=3"

    for i in range(2):
        execdir = _create_execdir(os.path.join(datadir, str(i)))

        sl.submit(execdir, _dryrun=True)

        _compare_jobsh(
            os.path.join(execdir, "job.sh"),
            datadir.join("_submit_multi_folder.sh"),
            execdir,
        )


def _test_nvidia_mps(datadir):
    sl = SlurmQueue(_findExecutables=False)
    sl.partition = "test"

    execdirs = [_create_execdir(os.path.join(datadir, str(i))) for i in range(3)]
    sl.submit(execdirs, nvidia_mps=True, _dryrun=True)

    assert os.path.exists(os.path.join(execdirs[0], "job.sh"))
    for i in range(1, 3):
        assert not os.path.exists(os.path.join(execdirs[i], "job.sh"))

    _compare_jobsh(
        os.path.join(execdirs[0], "job.sh"),
        datadir.join("_slurm_queue_nvidia_mps_job.sh"),
        datadir,
    )
