#! /usr/bin/env python
#-*- coding: utf8 -*-

from settings import SUPERVISOR, NODE

from httplib import FORBIDDEN, NOT_FOUND, OK
from sys import exit
from requests import ConnectionError

import logging
import os
import requests
import json


class NotFoundException(Exception):
    """Raised when there is no problem or tests for the problem
    with a given name, or the Supervisor return no submission to judge."""
    pass


class UnauthorizedException(Exception):
    """Raised when the Node is unauthorised to judge submissions."""
    pass


class UnknownErrorException(Exception):
    """Raised when an unknown error occured."""
    pass


class RESTConnection(object):
    """Class gathering all the REST queries and requests."""

    @classmethod
    def __get(cls, url):
        """Perform a GET request on the given URL."""
        try:
            return requests.get(
                SUPERVISOR['HOST'] + url + '?format=json',
                verify=True,
                headers={'x_token': NODE['TOKEN']}
            )
        except ConnectionError as e:
            logging.critical("Connection failed: {}".format(e))
            exit(1)

    @classmethod
    def __put(cls, url, *args, **kwargs):
        """Perform a POST request on the given URL."""
        headers = {'x_token': NODE['TOKEN']}
        headers.update(kwargs.get('headers', {}))
        del kwargs['headers']
        try:
            return requests.put(
                SUPERVISOR['HOST'] + url + '?format=json',
                verify=True,
                headers=headers,
                *args, **kwargs
            )

        except ConnectionError as e:
            logging.critical("Connection failed: {}".format(e))
            exit(1)

    @classmethod
    def get_submission(cls):
        """Get a new submission for judging."""

        # Prepare the URL
        url = 'submission/'

        response = cls.__get(url)

        if response.status_code == OK:
            # If everything is okay then parse the data and return it
            try:
                data = json.loads(response.text)
            except Exception as e:
                logging.error(
                    "Error while parsing response: {}\n{}.".format(data, e)
                )
                raise

            logging.info(
                "Recived submission id {}.".format(data['id'])
            )
            return data

        elif response.status_code == NOT_FOUND:
            logging.info("No submission recived.")
            raise NotFoundException()
        elif response.status_code == FORBIDDEN:
            logging.warning("Node unauthorized.")
            raise UnauthorizedException()
        else:
            logging.error("Unknown error status code: {}".format(
                response.status_code))
            raise UnknownErrorException()

    @classmethod
    def post_submission(cls, submissionId, submission):
        """Post a judged submission to the Supervisor."""

        url = 'submission/{}/'.format(submissionId)

        # Prepare the submission
        try:
            data = json.dumps(submission)
        except:
            logging.critical("Data malformed {}.".format(submission))
            raise

        response = cls.__put(
            url,
            data=data,
            headers={'Content-Type': 'application/json'}
        )

        if response.status_code == OK and not submission['error']:
            logging.info("The results have been sent.")
        elif response.status_code == OK and submission['error']:
            logging.info("Supervisor has been notified about the failure.")
        elif response.status_code == FORBIDDEN:
            logging.warning("Node unauthorized.")
            raise UnauthorizedException()
        else:
            logging.error("Unknown error status code: {}".format(
                response.status_code))
            raise UnknownErrorException()

    @classmethod
    def get_test_timestamps(cls, problem):
        """Get the timestamps for the tests for the problem with a given id."""

        url = 'problem/{}/test_timestamps'.format(problem)

        response = cls.__get(url)

        if response.status_code == OK:
            try:
                data = json.loads(response.text)
            except Exception as e:
                logging.error(
                    "Error while parsing response: {}\n{}.".format(data, e)
                )
                raise

            logging.info(
                "Recived test timestamps for problem {}.".format(problem)
            )
            return data

        elif response.status_code == NOT_FOUND:
            logging.info(
                "No test timestamps for problem {}.".format(problem)
            )
            raise NotFoundException()
        elif response.status_code == FORBIDDEN:
            logging.warning("Node unauthorized.")
            raise UnauthorizedException()
        else:
            logging.error("Unknown error status code: {}".format(
                response.status_code))
            raise UnknownErrorException()

    @classmethod
    def get_tests(cls, problem, testType, path):
        """Get the tests for the problem with a given id as a file path."""

        # There are only 3 types of test files
        if testType not in ('input', 'output', 'config'):
            raise TypeError("Type not recognized: {}.".format(testType))

        url = 'problem/{}/test_{}/'.format(problem, testType)

        response = cls.__get(url)

        if response.status_code == OK:
            cls.__write_to_file(response, path)
        elif response.status_code == NOT_FOUND:
            logging.info("No tests for problem {}.".format(problem))
            raise NotFoundException()
        elif response.status_code == FORBIDDEN:
            logging.warning("Node unauthorized.")
            raise UnauthorizedException()
        else:
            logging.error("Unknown error status code: {}".format(
                response.status_code))
            raise UnknownErrorException()

    @classmethod
    def __write_to_file(cls, response, path):
        """Writes the response body to a file given by the path."""

        if not os.path.exists(os.path.dirname(path)):
            os.makedirs(os.path.dirname(path))

        if os.path.exists(path):
            os.remove(path)

        with open(path, 'w') as output:
            for chunk in response.iter_content(1024):
                output.write(chunk)
