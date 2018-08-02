import os

import setuptools
from setuptools import setup

with open("README.md", "r") as fh:
    long_description = fh.read()


def package_files(directory):
    paths = []
    for (path, directories, filenames) in os.walk(directory):
        for filename in filenames:
            paths.append(os.path.join('..', path, filename))
    return paths


data_files = [('data', ['data/*.csv']),
              ('doc/img', ['doc/img/*']),
              ('flora_tools/flocklab', ['flora_tools/flocklab/*.xml', 'flora_tools/flocklab/*.png']),
              ('flora_tools/analysis', ['flora_tools/analysis/*.ipynb']),
              ('flora_tools/codegen/templates', ['flora_tools/codegen/templates/*']),
              ('flora_tools/trace_visualizer/templates', ['flora_tools/trace_visualizer/templates']),]

package_data = {'': package_files('flora_tools/trace_visualizer/static')}

setup(
    name='flora_tools',
    python_requires='>=3.7',
    version='0.2.0',
    packages=setuptools.find_packages(),
    url='https://github.com/Atokulus/flora_tools.git',
    license='MIT',
    author='atokulus',
    author_email='atokulus@gmail.com',
    description='Tool and library for interfacing with the PermaSense Flora nodes,'
                ' enabling programming, configuring and measuring.',
    long_description=long_description,
    long_description_content_type="text/markdown",
    install_requires=[
        'setuptools',
        'numpy',
        'pandas',
        'matplotlib',
        'networkx',
        'jupyter',
        'pyserial',
        'pyvisa',
        'intelhex',
        'coloredlogs',
        'flask',
        'requests',
    ],
    classifiers=(
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ),
    entry_points={
        'console_scripts': [
            'flora_tools = flora_tools.__main__:main'
        ]
    },

    package_data=package_data,
    data_files=data_files,

)
