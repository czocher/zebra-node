#-*- coding: utf8 -*-
from re import search
import os

PROJECT_ROOT = os.path.abspath(os.path.dirname(__file__))
p = lambda *x: os.path.join(PROJECT_ROOT, *x)

# List of languages supported by the Node
LANGUAGES = {
    'C': {
        'compiler': 'gcc',
        'compilerOptions': '-O2 -Wall -oresult',
        'runCommand': '{sandboxHome}/result',
        'sourceFilename': 'prog.c',
    },
    'C++': {
        'compiler': 'g++',
        'compilerOptions': '-O2 -Wall -oresult',
        'runCommand': '{sandboxHome}/result',
        'sourceFilename': 'prog.cpp'
    },
    'Pascal': {
        'compiler': 'fpc',
        'compilerOptions': '-O2 -oresult',
        'runCommand': '{sandboxHome}/result',
        'sourceFilename': 'prog.pas'
    },
    'Python': {
        'compiler': 'python',
        'compilerOptions': '-m py_compile',
        'runCommand': 'python {fileName}.{fileExtension}',
        'sourceFilename': 'prog.py'
    },
    'Java': {
        'compiler': 'javac',
        'compilerOptions': "",
        'runCommand': 'java  -Xmx2000k {fileName}',
        'sourceFilename': lambda sourceCode: search('public\s*class\s*(.*)\s*{',
                                  sourceCode).group(1) + '.java'
    }
}

# Node configuration
NODE = {
    # The Node's secret key checked in the Supervisor
    'TOKEN': 'ABCD',
    # The minimal time in seconds between Node's query to the Supervisor
    'QUERY_TIME': 5,
    # Can be 'file', 'http' or 'S3'
    # 'file' - get all the tests from the local file system
    # Warning! The tests won't be downloaded if they're not found
    # 'http' - like file but also download the tests from the Supervisor if not
    # found in the local file system
    # 'S3' - get the tests from a Amazon S3 backend if they're not found in the
    # local file system
    'TEST_BACKEND': 'rest',
    # Absolute path to the folder containing the tests
    'TEST_PATH': p('tests'),
    # Sandbox configuration
    'SANDBOX': {
        # Sandbox backend, only 'selinux' supported now
        'BACKEND': 'selinux',
        # Sandbox temporary directories used while sandboxing
        # and deleted soon after
        'HOME_DIR': './sandbox_home',
        'TMP_DIR': './sandbox_tmp',
        # Limit for compilation time in seconds
        'COMPILER_TIMELIMIT': 5,
    }
}

# Supervisor configuration
SUPERVISOR = {
    # The address of the Supervisor REST webservice
    'HOST': 'http://localhost:8000/rest/',
}
