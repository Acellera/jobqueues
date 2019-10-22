import setuptools
import unittest


with open('requirements.txt') as f:
    requirements = f.read().splitlines()

if __name__ == '__main__':
    with open('README.md', 'r') as fh:
        long_description = fh.read()

    setuptools.setup(
        name='jobqueues',
        version='unpackaged',
        author='Acellera',
        author_email='info@acellera.com',
        description='Wrappers for various queueing systems in python.',
        long_description=long_description,
        long_description_content_type='text/markdown',
        url='https://github.com/acellera/jobqueues/',
        classifiers=[
            'Programming Language :: Python :: 3',
            'Operating System :: POSIX :: Linux',
        ],

        packages=setuptools.find_packages(include=['jobqueues*'], exclude=['test-data']),

        package_data={
            'jobqueues': ['config_*.yml'],
        },
        install_requires=requirements
    )