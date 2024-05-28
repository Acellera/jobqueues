#!/bin/bash
#
#SBATCH --job-name=XXXXX
#SBATCH --partition=jobqueues_test
#SBATCH --cpus-per-task=1
#SBATCH --mem=1000
#SBATCH --priority=None
#SBATCH -D TESTDIR_PLACEHOLDER
#SBATCH --gres=gpu:2,gpu_mem:2000
#SBATCH --output=slurm.%N.%j.out
#SBATCH --error=slurm.%N.%j.err
#SBATCH --export=TEST=3
#SBATCH --nodelist=node2
#SBATCH --exclude=node1,node4

trap "touch TESTDIR_PLACEHOLDER/jobqueues.done" EXIT SIGTERM



cd TESTDIR_PLACEHOLDER
TESTDIR_PLACEHOLDER/run.sh

