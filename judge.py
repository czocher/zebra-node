#! /usr/bin/env python
#-*- coding: utf8 -*-

from math import ceil
from settings import LANGUAGES, NODE
from sandbox import Sandbox
from result import Result
import threading
import logging


class Judge(threading.Thread):
    """Compiles, executes and checks solutions for a specific task."""

    def __init__(self, task, submission):
        self.task = task
        self.language = submission['language']
        fileName = LANGUAGES[self.language].get('sourceFilename')
        if callable(fileName):
            fileName = fileName(submission['source'])
        self.fileFullName = fileName
        self.fileName, self.fileExtension = fileName.split('.')
        self._results = []
        self._compilation_log = None
        self.source = submission['source']

        # If the submission was sent in an active contest
        # judge sample tests only
        self.sampleTests = bool(int(submission['active']))
        threading.Thread.__init__(self)

    def run(self):
        """Process the judge request - create the sandbox,
        compile the source, execute and generate results."""

        with Sandbox.new() as sandbox:
            with sandbox.file(self.fileFullName) as sourceFile:
                sourceFile.write(self.source)
            self.compile(sandbox)
            self.execute(sandbox)

    def compare_files(self, out, ref=None):
        """Basic comparation function.
        Compares output file with reference file."""

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

    def check_solution(self, out, ref=None, fun=compare_files):
        """Compare solution with chosen function."""
        return fun(self, out, ref)

    def compile(self, sandbox):
        """Compile source code and save compile logs"""
        logging.info("Compiling the submission source.")
        cmd = '{compiler} {compilerOptions} {fileName}.{fileExtension}'.format(
            compiler=LANGUAGES[self.language].get('compiler'),
            compilerOptions=LANGUAGES[self.language].get('compilerOptions'),
            fileName=self.fileName,
            fileExtension=self.fileExtension
        )

        ret = sandbox.execute(
            cmd,
            None,
            timeLimit=NODE['SANDBOX']['COMPILER_TIMELIMIT']
        )

        self._compilation_log = '{} {}'.format(*ret[0])
        logging.info("Compilation finished.")

    def execute(self, sandbox):
        """Run program with all tests available for specific task
        and compare using check_solution. Program is limited by execution time
        and memory depending od information taken from the task."""
        logging.info("Executing the submission.")
        executionPath = LANGUAGES[self.language].get('runCommand').format(
            fileName=self.fileName,
            fileExtension=self.fileExtension,
            sandboxHome=NODE['SANDBOX']['HOME_DIR'],
        )

        for test in self.task.tests.itervalues():
            if not test.isSampleTest and self.sampleTests:
                continue

            (out, err), returncode, runTime = sandbox.execute(
                executionPath,
                test.input,
                timeLimit=int(ceil(test.timeLimit)),
                memoryLimit=test.memoryLimit
            )

            if not returncode == 0:
                runTime = 0

            if runTime > test.timeLimit:
                returncode = 9

            res = Result(
                returncode,
                int(self.check_solution(out, test.output) and returncode != 9),
                runTime)
            del out
            self._results.append(res)
        logging.info("Execution finished.")

        if err:
            logging.warning("There were errors during execution:\n{}".format(
                err
            ))

    @property
    def results(self):
        """Return compiler logs and results"""
        if len(self._results) == 0:
            return None
        return self._results

    @property
    def compilation_log(self):
        if not self._compilation_log:
            return None
        return self._compilation_log
