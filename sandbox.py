# -*- coding: utf-8 -*-
from settings import NODE, LANGUAGES
from subprocess import PIPE
from subprocess import Popen
from six import itervalues
import os
import codecs
import logging


class UnsupportedSandboxException(Exception):
    """Raised when the system cannot run this type of sandbox environment."""
    pass


class Sandbox(object):
    """Abstract sandbox class."""

    def execute(self, command, input, timeout):
        """Execute the given command in the sandbox environment."""
        raise NotImplementedError()

    def test_sandbox(self):
        """Test if the system can run this type of sandbox environment."""
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

    def test_sandbox(self):
        logging.info('Performing sandbox test...')
        for lang in itervalues(LANGUAGES):
            command = 'which ' + lang['compiler']
            c = self.execute(
                command,
                input="",
                memoryLimit=2000000,
                timeLimit=5
            )
            if c[1] != 0:
                raise UnsupportedSandboxException(c)

    def execute(self, command, input, *args, **kwargs):
        # Prepare the command
        memoryLimit = kwargs.get('memoryLimit')
        timeLimit = kwargs.get('timeLimit')

        if memoryLimit:
            ulimitCmd = 'ulimit -v {memoryLimit} -t {timeLimit};'.format(
                memoryLimit=memoryLimit,
                timeLimit=timeLimit
            )
        else:
            ulimitCmd = ''

        timeCmd = '/usr/bin/time -o time.log -f %U'
        cmd = '{ulimit}{sandbox} {time} {command}'.format(
            ulimit=ulimitCmd,
            sandbox=self.sandboxCmd,
            time=timeCmd,
            command=command
        )
        logging.info('Performing {}'.format(cmd))

        # Run the process
        process = Popen(cmd, stdin=PIPE, stdout=PIPE, stderr=PIPE, shell=True)

        output = map(lambda s: s.decode('utf-8'), process.communicate(input))

        # Get the time from the logging
        time = 0
        with open(os.path.join(NODE['SANDBOX']['HOME_DIR'], 'time.log'),
                  'r') as timeLogFile:
            lines = timeLogFile.read().split('\n')
            # File can contain 'Command exited with non-zero exit code'...
            if len(lines) > 2:
                time = float(lines[1])
            else:
                time = float(lines[0])

        return (output, process.returncode, time)
