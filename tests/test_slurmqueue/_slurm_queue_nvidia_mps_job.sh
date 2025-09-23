#!/bin/bash
#
#SBATCH --job-name=XXXXX
#SBATCH --partition=test
#SBATCH --cpus-per-task=1
#SBATCH --mem=1000
#SBATCH --priority=None
#SBATCH -D TESTDIR_PLACEHOLDER/0
#SBATCH --gres=gpu:1
#SBATCH --output=slurm.%N.%j.out
#SBATCH --error=slurm.%N.%j.err
#SBATCH --export=ACEMD_HOME,HTMD_LICENSE_FILE

trap "touch TESTDIR_PLACEHOLDER/0/jobqueues.done" EXIT SIGTERM


# assume CUDA_VISIBLE_DEVICES has been set by slurm
GPU=$CUDA_VISIBLE_DEVICES

echo "hostname: $(hostname)  GPU: $GPU"

# the CUDA_MPS_PIPE_DIRECTORY is how a program connects to the mps-control and the mps-server
# we can use a unique one for each job
export CUDA_MPS_PIPE_DIRECTORY=~/.nvidia-mps_$(hostname)_gpu_${GPU}
export CUDA_MPS_LOG_DIRECTORY=~/.nvidia-mps-logs_$(hostname)_gpu_${GPU}
echo $CUDA_MPS_PIPE_DIRECTORY
echo $CUDA_MPS_LOG_DIRECTORY

# start the control demon
nvidia-cuda-mps-control -d

# start the server
echo "start_server -uid ${UID}" | nvidia-cuda-mps-control

cd TESTDIR_PLACEHOLDER/0
TESTDIR_PLACEHOLDER/0/run.sh  2>&1 | tee log_1.txt &
cd TESTDIR_PLACEHOLDER/1
TESTDIR_PLACEHOLDER/1/run.sh  2>&1 | tee log_2.txt &
cd TESTDIR_PLACEHOLDER/2
TESTDIR_PLACEHOLDER/2/run.sh  2>&1 | tee log_3.txt &
cd TESTDIR_PLACEHOLDER/0

wait
# quit the server and the control. It will only quit the one corresponding to the CUDA_MPS_PIPE_DIRECTORY env variable
echo quit | nvidia-cuda-mps-control
