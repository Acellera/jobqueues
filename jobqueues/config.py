# (c) 2015-2018 Acellera Ltd http://www.acellera.com
# All Rights Reserved
# Distributed under HTMD Software License Agreement
# No redistribution in whole or part
#
import os
import logging

logger = logging.getLogger(__file__)

_config = {
    'lsf': None, 
    'slurm': None
    }


def config(lsf=_config['lsf'],
           slurm=_config['slurm']):
    """
    Function to temporarily change configuration variables.

    Parameters
    ----------
    lsf : str
        Defines a YAML file that can contain default profile configurations for an LsfQueue
    slurm : str
        Defines a YAML file that can contain default profile configurations for an SlurmQueue
    """
    _config['lsf'] = lsf
    _config['slurm'] = slurm
