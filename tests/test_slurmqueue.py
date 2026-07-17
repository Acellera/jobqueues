from pytest import fixture
from distutils import dir_util
from jobqueues.slurmqueue import SlurmQueue
import yaml
import re
import glob
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


def _create_execdir(tmpdir, runscript="run.sh"):
    from jobqueues.util import _makeExecutable

    os.makedirs(tmpdir)
    run_sh = os.path.join(tmpdir, runscript)
    with open(run_sh, "w") as f:
        f.write("sleep 5\n")
    _makeExecutable(run_sh)
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


def _find_jobsh(execdir):
    matches = glob.glob(os.path.join(str(execdir), "job_*.sh"))
    assert len(matches) == 1, f"Expected exactly one job script, found {matches}"
    return matches[0]


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

    _compare_jobsh(_find_jobsh(execdir), datadir.join("_submit_command.sh"), datadir)


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

    _compare_jobsh(_find_jobsh(execdir), datadir.join("_submit_folder.sh"), datadir)


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
            _find_jobsh(execdir),
            datadir.join("_submit_multi_folder.sh"),
            execdir,
        )


def _test_nvidia_mps(datadir):
    sl = SlurmQueue(_findExecutables=False)
    sl.partition = "test"

    execdirs = [_create_execdir(os.path.join(datadir, str(i))) for i in range(3)]
    sl.submit(execdirs, nvidia_mps=True, _dryrun=True)

    assert len(glob.glob(os.path.join(execdirs[0], "job_*.sh"))) == 1
    for i in range(1, 3):
        assert len(glob.glob(os.path.join(execdirs[i], "job_*.sh"))) == 0

    _compare_jobsh(
        _find_jobsh(execdirs[0]),
        datadir.join("_slurm_queue_nvidia_mps_job.sh"),
        datadir,
    )


def _test_nvidia_mps_runscript(datadir):
    sl = SlurmQueue(_findExecutables=False)
    sl.partition = "test"

    execdirs = [
        _create_execdir(os.path.join(datadir, str(i)), runscript=f"run{i}.sh")
        for i in range(3)
    ]
    sl.submit(
        execdirs,
        runscripts=["run0.sh", "run1.sh", "run2.sh"],
        nvidia_mps=True,
        _dryrun=True,
    )

    assert len(glob.glob(os.path.join(execdirs[0], "job_*.sh"))) == 1
    for i in range(1, 3):
        assert len(glob.glob(os.path.join(execdirs[i], "job_*.sh"))) == 0

    _compare_jobsh(
        _find_jobsh(execdirs[0]),
        datadir.join("_slurm_queue_nvidia_mps_job_runscripts.sh"),
        datadir,
    )


def _test_nvidia_mps_scales_resources(tmpdir):
    sl = SlurmQueue(_findExecutables=False)
    sl.partition = "test"
    sl.ncpu = 2
    sl.memory = 1500

    execdirs = [_create_execdir(str(tmpdir.join(str(i)))) for i in range(3)]
    jobsh = sl.submit(execdirs, nvidia_mps=True, _dryrun=True)

    with open(jobsh, "r") as f:
        content = f.read()

    # The single MPS job hosts all three processes: it must request the
    # whole batch's CPUs and memory, without mutating the queue object
    assert "#SBATCH --cpus-per-task=6" in content
    assert "#SBATCH --mem=4500" in content
    assert sl.ncpu == 2
    assert sl.memory == 1500


def _test_dryrun_returns_jobscript_path(tmpdir):
    execdir = str(tmpdir.join("0"))
    os.makedirs(execdir, exist_ok=True)

    sl = SlurmQueue(_findExecutables=False)
    sl.partition = "jobqueues_test"
    ret = sl.submit([execdir], commands=["sleep 5"], _dryrun=True)

    assert ret == _find_jobsh(execdir)

    execdirs = [_create_execdir(str(tmpdir.join(str(i + 1)))) for i in range(2)]
    ret = sl.submit(execdirs, commands=["sleep 5", "sleep 5"], _dryrun=True)

    assert isinstance(ret, list)
    assert ret == [_find_jobsh(d) for d in execdirs]


def _test_dryrun_returns_jobscript_path_nvidia_mps(tmpdir):
    sl = SlurmQueue(_findExecutables=False)
    sl.partition = "test"

    execdirs = [_create_execdir(str(tmpdir.join(str(i)))) for i in range(3)]
    ret = sl.submit(execdirs, nvidia_mps=True, _dryrun=True)

    assert ret == _find_jobsh(execdirs[0])


def _test_unique_jobscript_names_on_concurrent_submission(tmpdir):
    execdir = str(tmpdir.join("0"))
    os.makedirs(execdir, exist_ok=True)

    sl = SlurmQueue(_findExecutables=False)
    sl.partition = "jobqueues_test"
    sl.submit([execdir], commands=["sleep 5"], _dryrun=True)
    sl.submit([execdir], commands=["sleep 5"], _dryrun=True)

    scripts = glob.glob(os.path.join(execdir, "job_*.sh"))
    assert len(scripts) == 2, f"Expected two distinct job scripts, found {scripts}"
