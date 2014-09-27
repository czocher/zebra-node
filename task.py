#! /usr/bin/env python
#-*- coding: utf8 -*-
from test import Test
from settings import NODE
from rest import RESTConnection
import os
import tarfile
import logging
import xmltodict


class Task(object):
    """Represents single task. It is defined by a problem id and
    manages tests for that problem."""

    def __init__(self, pid):
        """Load tests for the given problem id."""
        raise NotImplementedError()

    @property
    def tests(self):
        """Checks if the tests require updating and returns them."""
        raise NotImplementedError()

    def _check_updates(self):
        """Checks if tests need realoading."""
        raise NotImplementedError()

    def _load_tests(self):
        """Loads the tests from the given backend."""
        raise NotImplementedError()

    @staticmethod
    def new(pid):
        """Create a new task object according to the settings."""

        if NODE['TEST_BACKEND'] == 'file':
            return FileTask(pid)
        elif NODE['TEST_BACKEND'] == 'rest':
            return RESTTask(pid)


class FileTask(Task):
    """Task which loads tests from local filesystem files."""
    pass


class RESTTask(Task):
    """Task which loads tests from the REST web service."""

    def __init__(self, pid):
        self.pid = pid
        self._tests = {}
        self.timestamp = [0, 0, 0]

    @property
    def tests(self):
        self._check_updates()
        return self._tests

    @tests.setter
    def tests(self, value):
        self._tests = value

    def _check_updates(self):
        logging.info("Checking if tests are up-to-date.")
        inpt_path = self.__get_test_path(NODE['TEST_PATH'], self.pid, 'in')
        out_path = self.__get_test_path(NODE['TEST_PATH'], self.pid, 'out')
        conf_path = self.__get_test_path(NODE['TEST_PATH'], self.pid, 'conf')

        if not os.path.exists(inpt_path) or not os.path.exists(out_path) or \
           not os.path.exists(conf_path):
            logging.info("Tests for problem {} do not exist.".format(self.pid))
            self._load_tests()
        else:
            data = RESTConnection.get_test_timestamps(self.pid)

            inpt_time = int(data['in'])
            out_time = int(data['out'])
            conf_time = int(data['conf'])

            if int(os.path.getmtime(inpt_path)) < inpt_time or \
               int(os.path.getmtime(out_path)) < out_time or \
               int(os.path.getmtime(conf_path)) < conf_time:
                logging.info("Tests for problem {} outdated.".format(self.pid))
                self._load_tests()
            logging.info(
                "Tests for problem {} are up-to-date.".format(self.pid)
            )

        logging.info("Tests for problem {} loaded.".format(self.pid))
        self.__fill_tests(
            self.__get_test_path(NODE['TEST_PATH'], self.pid, 'conf'),
            self.__get_test_path(NODE['TEST_PATH'], self.pid, 'out'),
            self.__get_test_path(NODE['TEST_PATH'], self.pid, 'in')
        )

    @staticmethod
    def __get_test_path(path, pid, testType):
        """Creates an absolute path to the test file."""
        return os.path.join(path, pid, testType + '.tar.gz')

    def _load_tests(self):
        logging.info("Updating tests for problem {}.".format(self.pid))

        inpt_path = self.__get_test_path(NODE['TEST_PATH'], self.pid, 'in')

        RESTConnection.get_tests(
            problemId=self.pid,
            testType='in',
            path=inpt_path
        )
        out_path = self.__get_test_path(NODE['TEST_PATH'], self.pid, 'out')
        RESTConnection.get_tests(
            problemId=self.pid,
            testType='out',
            path=out_path
        )
        conf_path = self.__get_test_path(NODE['TEST_PATH'], self.pid, 'conf')
        RESTConnection.get_tests(
            problemId=self.pid,
            testType='conf',
            path=conf_path
        )

    def __fill_tests(self, conf_path, out_path, inpt_path):
        """Fill the tests dict with the Test objects from tar files."""

        with tarfile.open(conf_path, mode='r:gz') as conf:
            for tarinfo in conf:
                data = conf.extractfile(tarinfo).read()
                data = xmltodict.parse(data)
                memory = int(data['test']['memory'])
                time = int(data['test']['time'])
                sample = bool(int(data['test']['sample']))
                test = Test(memoryLimit=memory, timeLimit=time,
                            isSampleTest=sample)
                self._tests.update({tarinfo.name: test})

        with tarfile.open(inpt_path, mode='r:gz') as inpt:
            for tarinfo in inpt:
                data = inpt.extractfile(tarinfo).read()
                self._tests[tarinfo.name].input = data

        with tarfile.open(out_path, mode='r:gz') as out:
            for tarinfo in out:
                data = out.extractfile(tarinfo).read()
                self._tests[tarinfo.name].output = data
