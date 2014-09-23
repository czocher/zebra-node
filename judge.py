#! /usr/bin/env python
#-*- coding: utf8 -*-

import threading
import os
import logging
from subprocess import check_call, Popen, PIPE
from settings import LANGS, SANDBOX_HOME_DIR, SANDBOX_TMP_DIR, sandboxCommand
from result import Result
from math import ceil
import codecs


class Judge(threading.Thread):
    """Class with compile, execute and check solutions for specific tasks"""
    def __init__(self, sourceCode, language, task, sampleTests):
        self.task = task
        self.lang = language
        if callable(LANGS[self.lang].fileName):
            try:
                fileName = LANGS[self.lang].fileName(sourceCode)
            except:
                raise ValueError
        else:
            fileName = LANGS[self.lang].fileName
        tmp = fileName.split('.')
        self.fileFullName = fileName
        self.fileName = tmp[0]
        self.fileExtention = tmp[1]
        self.results = []
        self.log = None
        self.sourceCode = sourceCode
        self.sampleTests = sampleTests
        threading.Thread.__init__(self)

    def run(self):
        """Processing judge request - create sandbox, compile, execute and check answers"""
        self.__createSandbox()
        try:
            self.compile()
            self.execute()
        except RuntimeError:
            pass
        except Exception:
            logging.exception("Unexpected error during judging: ")
        finally:
            self.__deleteSandbox()

    def compareFiles(self, out, ref=None):
        """Basic compare function. It basically compare output file with reference file """
        out = out.rstrip()
        ref = ref.rstrip()
        out = out.split('\n')
        ref = ref.split('\n')
        if len(out) != len(ref):
            return False
        for outLine, refLine in zip(out, ref):
            if outLine.rstrip() != refLine.rstrip():
                return False
        return True

    def checkSolution(self, out, ref=None, fun=compareFiles):
        """Compare solution with chosen function."""
        return fun(self, out, ref)

    def compile(self):
        """Compile source code and save compile logs"""
        with open(SANDBOX_HOME_DIR + "/compile.log", "w") as cLog:
            try:
                check_call(sandboxCommand + ' ' + LANGS[self.lang].compiler
                           + ' ' + LANGS[self.lang].compilerArg + ' '
                           + self.fileName + '.' + self.fileExtention,
                           stderr=cLog, stdout=cLog, shell=True)
            except KeyError:
                logging.error("Unknown language %s", self.lang)
                raise RuntimeError
            except:
                logging.info("Compilation error")
                raise RuntimeError
            finally:
                with open(SANDBOX_HOME_DIR + "/compile.log") as cLog:
                    self.log = cLog.read()

    def execute(self):
        """Run program with all tests available for specific task and compare using checkSolution
        Program is limited by execution time and memory also specific for any task"""
        executionPath = LANGS[self.lang].execution
        executionPath = executionPath.replace('FILENAME', self.fileName)
        executionPath = executionPath.replace('FILEXTENTION', self.fileExtention)

        timeCommand = '/usr/bin/time -o time.log -f %U'

        for test in self.task.tests.itervalues():

            if test.sampleTest == False and self.sampleTests == 1:
                continue

            ulimitCommand = 'ulimit -t ' + str(int(ceil(test.timeLimit))) + \
                        ' -v ' + str(test.memoryLimit) + ';'

            proc = Popen(ulimitCommand + sandboxCommand + \
                         ' ' + timeCommand + ' ' + executionPath, \
                         stdin=PIPE, stdout=PIPE, stderr=PIPE, shell=True)
            dataOut = proc.communicate(input=test.input)[0]
            proc.wait()

            if proc.returncode == 0:
                with open(SANDBOX_HOME_DIR + "/time.log", "r") as fTime:
                    timeOfExecution = float(fTime.read().rstrip("\n"))
            else:
                timeOfExecution = 0
            if timeOfExecution > test.timeLimit:
                proc.returncode = 9
            res = Result(proc.returncode,
                         self.checkSolution(dataOut, test.reference) and timeOfExecution < test.timeLimit, timeOfExecution)
            del dataOut
            self.results.append(res)

    def getResults(self):
        """Return compiler logs and results"""
        if self.log == None and len(self.results) == 0:
            return None
        return [self.log, self.results]

    def __deleteDir(self, dirName):
        try:
            for root, dirs, files in os.walk(dirName, topdown=False):
                for name in files:
                    os.remove(os.path.join(root, name))
                for name in dirs:
                    os.rmdir(os.path.join(root, name))
            os.rmdir(dirName)
        except OSError:
            pass

    def __createSandbox(self):
        """Create directories for sandbox purposes (home dir and tmp dir).
        Folders names are specified on settings file"""
        self.__deleteSandbox()
        try:
            os.mkdir(SANDBOX_HOME_DIR)
            os.mkdir(SANDBOX_TMP_DIR)
        except OSError:
            logging.error("Error while creating sandbox directory")
            raise
        with codecs.open(SANDBOX_HOME_DIR + "/" + self.fileFullName, 'w', "utf-8") as source:
            source.write(self.sourceCode)

    def __deleteSandbox(self):
        """Remove all files in sandbox directories. After delete sandbox directories.
        Folder names are specified on settings file"""
        self.__deleteDir(SANDBOX_HOME_DIR)
        self.__deleteDir(SANDBOX_TMP_DIR)
