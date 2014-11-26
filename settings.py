#-*- coding: utf8 -*-
from language import Language
from re import search
import os

PROJECT_ROOT = os.path.abspath(os.path.dirname(__file__))
p = lambda *x: os.path.join(PROJECT_ROOT, *x)

# List of languages supported by the Node.
# Language(compiler name, compiler arguments,
#          execution command, file extension)
LANGUAGES = {
    'C': Language("gcc", "-O2 -Wall -oresult", "./result", "prog.c"),
    'C++': Language("g++", "-O2 -Wall -oresult", "./result", "prog.cpp"),
    'Pascal': Language("fpc", "-O2 -oresult", "./result", "prog.pas"),
    'Python': Language("python", "-m py_compile",
                       "python {fileName}.{fileExtension}", "prog.py"),
    'Java': Language("javac", "", "java FILENAME",
                     lambda sourceCode: search("public\s*class\s*(.*)\s*{",
                                  sourceCode).group(1) + ".java")
}

# Sandbox execution command used when a submission is begin compiled
# and executed

# Node configuration
NODE = {
    # The Node's secret key checked in the Supervisor
    'TOKEN': 'ABCD',
    # The Node's version sent to the Supervisor
    'VERSION': '0.01',
    # The Node's RAM in MiB.
    'MAX_MEMORY': 262144,
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
        'HOME_DIR': p('sandbox_home'),
        'TMP_DIR': p('sandbox_tmp'),
        # Limit for compilation time in seconds
        'COMPILER_TIMELIMIT': 5,
    }
}

# Supervisor configuration
SUPERVISOR = {
    # The address of the Supervisor rest webservice
    'HOST': 'http://localhost:8000/rest/',
}
