Installation
============

You can install JobQueues either using pip or conda.

We generally advise to use a conda installation regardless if installing jobqueues over pip or conda
as well as creating a separate conda environment for the installation to avoid conflicts with other libraries
or python version. If you however prefer to install it to your system python you can ignore the following two steps
related to conda installation and environments at your own risk.

Downloading miniconda
---------------------
Miniconda is a lightweight installer of conda containing just a few basic python libraries.
Download miniconda from the following URL https://docs.conda.io/en/latest/miniconda.html
and install it following the given instructions.

Create a conda environment
--------------------------
After installing miniconda you can create a conda environment for JobQueues with the following command::

   conda create -n jobqueues

This will not install JobQueues, it simply creates a clean empty python environment named `jobqueues`.
To now operate within this new environment use the following command to activate it. Anything installed with
conda or pip after this command will be installed into this clean python environment.:: 

   conda activate jobqueues

Install jobqueues with conda
------------------------------
::

   conda install jobqueues python=3.10 -c acellera -c conda-forge

This will install jobqueues alongside python 3.10 version which is the currently developed version of jobqueues.