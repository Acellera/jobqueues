#!/usr/bin/env bash

# Build for conda from PyPI
conda deactivate test

export TAG_DESCRIBE=$(git describe)
export BUILD_VERSION=$(echo $TAG_DESCRIBE | sed 's/-/ /g'  | awk '{print $1}')
export BUILD_NUMBER=0

conda build --python $CONDA_PY package/jobqueues/ -c acellera

bash -x ./ci/travis/conda_upload.sh;
