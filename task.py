#! /usr/bin/env python
#-*- coding: utf8 -*-
from utils import iso_to_datetime, get_file_modification_date
from test import Test
from settings import NODE
from rest import RESTConnection
import os
import tarfile
import logging
import json


class Task(object):
    """Represents single task. It is defined by a problem id and
    manages tests for that problem."""

    def __init__(self, problem):
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
    def new(problem):
        """Create a new task object according to the settings."""

        if NODE['TEST_BACKEND'] == 'file':
            return FileTask(problem)
        elif NODE['TEST_BACKEND'] == 'rest':
            return RESTTask(problem)


class FileTask(Task):
    """Task which loads tests from local filesystem files."""
    pass


class RESTTask(Task):
    """Task which loads tests from the REST web service."""

    def __init__(self, problem):
        self.problem = problem
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
        """Check if tests are up-to-date, if not download new ones."""
        logging.info("Checking if tests are up-to-date.")
        inpt_path = self.__get_test_path(
            NODE['TEST_PATH'], self.problem, 'input')
        out_path = self.__get_test_path(
            NODE['TEST_PATH'], self.problem, 'output')
        conf_path = self.__get_test_path(
            NODE['TEST_PATH'], self.problem, 'config')

        if not os.path.exists(inpt_path) or not os.path.exists(out_path) or \
           not os.path.exists(conf_path):
            logging.info(
                "Tests for problem {} do not exist.".format(self.problem)
            )
            self._load_tests()
        else:
            data = RESTConnection.get_test_timestamps(self.problem)

            inpt_time = iso_to_datetime(data['input'])
            out_time = iso_to_datetime(data['output'])
            conf_time = iso_to_datetime(data['config'])

            if get_file_modification_date(inpt_path) < inpt_time or \
               get_file_modification_date(out_path) < out_time or \
               get_file_modification_date(conf_path) < conf_time:
                logging.info(
                    "Tests for problem {} outdated.".format(self.problem)
                )
                self._remove_tests()
                self._load_tests()
            logging.info(
                "Tests for problem {} are up-to-date.".format(self.problem)
            )

        logging.info("Tests for problem {} loaded.".format(self.problem))
        self.__fill_tests(
            self.__get_test_path(NODE['TEST_PATH'], self.problem, 'config'),
            self.__get_test_path(NODE['TEST_PATH'], self.problem, 'output'),
            self.__get_test_path(NODE['TEST_PATH'], self.problem, 'input')
        )

    @staticmethod
    def __get_test_path(path, problem, testType):
        """Creates an absolute path to the test file."""
        return os.path.join(path, problem, testType + '.tar.gz')

    def _remove_tests(self):
        """Remove all test files for a given task."""
        logging.info("Removing old tests for problem {}.".format(self.problem))

        inpt_path = self.__get_test_path(
                NODE['TEST_PATH'], self.problem, 'input')
        os.remove(inpt_path)

        out_path = self.__get_test_path(
                NODE['TEST_PATH'], self.problem, 'output')
        os.remove(out_path)

        conf_path = self.__get_test_path(
                NODE['TEST_PATH'], self.problem, 'config')
        os.remove(conf_path)


    def _load_tests(self):
        """Load tests from REST webservice and save them as files."""

        logging.info("Updating tests for problem {}.".format(self.problem))

        inpt_path = self.__get_test_path(
            NODE['TEST_PATH'], self.problem, 'input')
        RESTConnection.get_tests(
            problem=self.problem,
            testType='input',
            path=inpt_path
        )

        out_path = self.__get_test_path(
            NODE['TEST_PATH'], self.problem, 'output')
        RESTConnection.get_tests(
            problem=self.problem,
            testType='output',
            path=out_path
        )

        conf_path = self.__get_test_path(
            NODE['TEST_PATH'], self.problem, 'config')
        RESTConnection.get_tests(
            problem=self.problem,
            testType='config',
            path=conf_path
        )

    def __fill_tests(self, conf_path, out_path, inpt_path):
        """Fill the tests dict with the Test objects from tar files."""

        with tarfile.open(conf_path, mode='r') as conf:
            for tarinfo in conf:
                data = conf.extractfile(tarinfo).read()
                data = json.loads(data.decode('utf-8'))
                memory = int(data['memory'])
                time = int(data['time'])
                sample = bool(int(data['sample']))
                test = Test(memoryLimit=memory, timeLimit=time,
                            isSampleTest=sample)
                self._tests.update({tarinfo.name: test})

        with tarfile.open(inpt_path, mode='r') as inpt:
            for tarinfo in inpt:
                data = inpt.extractfile(tarinfo).read()
                self._tests[tarinfo.name].input = data

        with tarfile.open(out_path, mode='r') as out:
            for tarinfo in out:
                data = out.extractfile(tarinfo).read().decode('utf-8')
                self._tests[tarinfo.name].output = data
