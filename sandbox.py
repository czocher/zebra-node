# -*- coding: utf-8 -*-
from settings import NODE
from command import Command
from subprocess import PIPE
import os
import codecs
import logging


class Sandbox(object):
    """Abstract sandbox class."""

    def execute(self, command, input, timeout):
        """Execute the given command in the sandbox environment."""
        raise NotImplementedError()

    @staticmethod
    def new():
        """Create a new Sandbox instance according to the configuration."""
        if NODE['SANDBOX']['BACKEND'] == 'selinux':
            return SELinuxSandbox()
        else:
            return Sandbox()

    def _delete_dir(self, dirName):
        """Delete a given directory tree."""
        try:
            for root, dirs, files in os.walk(dirName, topdown=False):
                for name in files:
                    os.remove(os.path.join(root, name))
                for name in dirs:
                    os.rmdir(os.path.join(root, name))
            os.rmdir(dirName)
        except OSError:
            pass

    def _create_sandbox(self):
        """Create directories for sandbox purposes (home_dir and tmp_dir).
        Folder names are specified on settings file."""

        # Delete just to make sure
        self._delete_sandbox()
        try:
            os.mkdir(NODE['SANDBOX']['HOME_DIR'])
            os.mkdir(NODE['SANDBOX']['TMP_DIR'])
        except OSError:
            logging.error("Error while creating sandbox directory.")
            raise

    def file(self, name):
        """Return a file object created inside the sandbox."""
        path = os.path.join(NODE['SANDBOX']['HOME_DIR'], name)
        return codecs.open(path, 'w', 'utf-8')

    def _delete_sandbox(self):
        """Delete the sandbox dirs."""
        self._delete_dir(NODE['SANDBOX']['HOME_DIR'])
        self._delete_dir(NODE['SANDBOX']['TMP_DIR'])

    def __enter__(self):
        self._create_sandbox()
        return self

    def __exit__(self, *args, **kwargs):
        self._delete_sandbox()


class SELinuxSandbox(Sandbox):
    """SELinux-based sandbox implementation."""

    def __init__(self):
        self.sandboxCmd = 'sandbox -t sandbox_t' +\
            ' -M -H {sandboxHome} -T {sandboxTmp}'.format(
            sandboxHome=NODE['SANDBOX']['HOME_DIR'],
            sandboxTmp=NODE['SANDBOX']['TMP_DIR'])

    def execute(self, command, input, *args, **kwargs):

        memoryLimit = kwargs.get('memoryLimit')
        timeLimit = kwargs.get('timeLimit')

        if memoryLimit:
            ulimitCmd = 'ulimit -v {memoryLimit};'.format(
                memoryLimit=memoryLimit
            )
        else:
            ulimitCmd = ''

        c = Command('{ulimit}{sandbox} {command}'.format(
            ulimit=ulimitCmd,
            sandbox=self.sandboxCmd,
            command=command
        ), stdin=PIPE, stdout=PIPE, stderr=PIPE, shell=True)

        c.run(input, timeLimit)
        return (c.output, c.returncode, c.time)
