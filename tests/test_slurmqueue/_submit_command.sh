#!/bin/bash
#
#SBATCH --job-name=XXXXX
#SBATCH --partition=jobqueues_test
#SBATCH --cpus-per-task=1
#SBATCH --mem=1000
#SBATCH --priority=None
#SBATCH -D /tmp/
#SBATCH --gres=gpu:2,gpu_mem:2000
#SBATCH --export=TEST=3
#SBATCH --nodelist=node2
#SBATCH --exclude=node1,node4




cd TESTDIR_PLACEHOLDER/0
sleep 5
