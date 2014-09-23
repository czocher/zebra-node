#-*- coding: utf8 -*-
from language import Language
from re import search

#Programming languages
"""Language list.
Key is short name of language.
Arguments in Language constructor:
1. Compiler name
2. Compiler arguments
3. Execution file.
FILENAME, FILEXTENTION are replaced by true file name passed in proper function"""
LANGS = {
         'c': Language("gcc", "-O2 -Wall -oresult", "./result", "prog.c"),
         'c++': Language("g++", "-O2 -Wall -oresult", "./result", "prog.cpp"),
         'pascal': Language("fpc", "-O2 -oresult", "./result", "prog.pas"),
         'python': Language("python", "-m py_compile",
                             "python FILENAME.FILEXTENTIONc", "prog.py"),
         'java': Language("javac", "", "java FILENAME", lambda sourceCode: search("public\s*class\s*(.*)\s*{", sourceCode).group(1) + ".java")
        }

#Sandbox
"""Sandbox temporary directories. They are created before compilation and delete after execution"""
SANDBOX_HOME_DIR = "sandbox_home"
SANDBOX_TMP_DIR = "sandbox_tmp"

"""Sandbox command with is executed when program is compiling and executing"""
sandboxCommand = 'sandbox -M -H ' + SANDBOX_HOME_DIR + ' -T ' + SANDBOX_TMP_DIR


#Node
NODE_NAME = "Test"
NODE_KEY = "666"
NODE_VERSION = "0.01"
REFRESH_TIME = 5

MAX_MEMORY = 262144

#Supervisor
SUPERVISOR_HOST = ""
REST_URL_PREFIX = "/rest/"

#TASK BACKEND
TASK_BACKEND = "file" #possible "file" or "supervisor"

#TEST BACKEND
TEST_BACKEND = "file" #possible "file" or "http" or "S3"
