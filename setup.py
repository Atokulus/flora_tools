import setuptools
from setuptools import setup

with open("README.md", "r") as fh:
    long_description = fh.read()

setup(
    name='flora_tools',
    python_requires='>=3.7',
    version='0.1.10',
    packages=setuptools.find_packages(),
    url='https://github.com/Atokulus/flora_tools.git',
    license='MIT',
    author='atokulus',
    author_email='atokulus@gmail.com',
    description='Tool and library for interfacing with the PermaSense Flora nodes, enabling programming, configuring and measuring.',
    long_description=long_description,
    long_description_content_type="text/markdown",
    install_requires=[
        'numpy',
        'pandas',
        'matplotlib',
        'networkx'
        'jupyter',
        'pyserial',
        'pyvisa',
        'intelhex',
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
)
