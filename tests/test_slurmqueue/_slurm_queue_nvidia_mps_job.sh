#!/bin/bash
#
#SBATCH --job-name=XXXXX
#SBATCH --partition=test
#SBATCH --cpus-per-task=3
#SBATCH --mem=3000
#SBATCH --priority=None
#SBATCH -D TESTDIR_PLACEHOLDER/0
#SBATCH --output=slurm.%N.%j.out
#SBATCH --error=slurm.%N.%j.err
#SBATCH --export=ACEMD_HOME,HTMD_LICENSE_FILE

# Job-private MPS daemon keyed on the SLURM job id: unique no matter whether
# CUDA_VISIBLE_DEVICES contains cgroup-relative or physical GPU indices
export CUDA_MPS_PIPE_DIRECTORY=/tmp/nvidia-mps-${SLURM_JOB_ID}
export CUDA_MPS_LOG_DIRECTORY=/tmp/nvidia-mps-logs-${SLURM_JOB_ID}

cleanup() {
    # Shut down the MPS daemon on any exit, including cancellation and timeout
    echo quit | nvidia-cuda-mps-control 2> /dev/null
    touch TESTDIR_PLACEHOLDER/0/jobqueues.done
    touch TESTDIR_PLACEHOLDER/1/jobqueues.done
    touch TESTDIR_PLACEHOLDER/2/jobqueues.done
}
trap cleanup EXIT SIGTERM


mkdir -p $CUDA_MPS_PIPE_DIRECTORY $CUDA_MPS_LOG_DIRECTORY
echo "hostname: $(hostname)  CUDA_VISIBLE_DEVICES: $CUDA_VISIBLE_DEVICES"
echo $CUDA_MPS_PIPE_DIRECTORY
echo $CUDA_MPS_LOG_DIRECTORY

# start the control daemon
nvidia-cuda-mps-control -d

# start the server
echo "start_server -uid ${UID}" | nvidia-cuda-mps-control

# Abort if the MPS server did not come up: clients would otherwise silently
# fall back to direct GPU access, ignoring the job's GPU allocation
if ! echo get_server_list | nvidia-cuda-mps-control | grep -q .; then
    echo "Error: NVIDIA MPS server failed to start" >&2
    exit 1
fi

# The MPS server remaps the allocated GPUs to devices 0..N-1 so the clients
# must not inherit the job's CUDA_VISIBLE_DEVICES indices
unset CUDA_VISIBLE_DEVICES

# Propagate the MPS pipe/log dirs into apptainer/singularity containers: with
# --cleanenv only *ENV_-prefixed variables cross the container boundary, and a
# client which cannot find the pipe silently falls back to time-slicing the GPU
export APPTAINERENV_CUDA_MPS_PIPE_DIRECTORY=$CUDA_MPS_PIPE_DIRECTORY
export APPTAINERENV_CUDA_MPS_LOG_DIRECTORY=$CUDA_MPS_LOG_DIRECTORY
export SINGULARITYENV_CUDA_MPS_PIPE_DIRECTORY=$CUDA_MPS_PIPE_DIRECTORY
export SINGULARITYENV_CUDA_MPS_LOG_DIRECTORY=$CUDA_MPS_LOG_DIRECTORY

cd TESTDIR_PLACEHOLDER/0
TESTDIR_PLACEHOLDER/0/run.sh  2>&1 | tee log_1.txt &
cd TESTDIR_PLACEHOLDER/1
TESTDIR_PLACEHOLDER/1/run.sh  2>&1 | tee log_2.txt &
cd TESTDIR_PLACEHOLDER/2
TESTDIR_PLACEHOLDER/2/run.sh  2>&1 | tee log_3.txt &
cd TESTDIR_PLACEHOLDER/0

wait
