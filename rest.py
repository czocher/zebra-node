#! /usr/bin/env python
#-*- coding: utf8 -*-

from settings import SUPERVISOR, NODE, LANGUAGES
from utils import get_free_memory, get_free_diskspace, get_processor_frequency

from httplib import UNAUTHORIZED, NOT_FOUND, BAD_REQUEST, OK, CONFLICT
from datetime import datetime
from sys import exit
from xmltodict import parse, unparse

import logging
import os
import requests
from requests import ConnectionError


class NotFoundException(Exception):
    """Raised when there is no problem or tests for the problem
    with a given name, or the Supervisor return no submission to judge."""
    pass


class SessionExpiredException(Exception):
    """Raised when the session expires."""
    pass


class UnauthorizedException(Exception):
    """Raised when the Node is unauthorised to judge submissions."""
    pass


class RESTConnection(object):
    """Class gathering all the REST queries and requests."""

    URL = None
    SESSION_ID = None

    @classmethod
    def __get(cls, url):
        try:
            return requests.get(SUPERVISOR['HOST'] + url, verify=True)
        except ConnectionError as e:
            logging.critical("Connection failed: {}".format(e))
            exit(1)

    @classmethod
    def __post(cls, url, *args, **kwargs):
        try:
            return requests.post(SUPERVISOR['HOST'] + url, verify=True,
                                 *args, **kwargs)
        except ConnectionError as e:
            logging.critical("Connection failed: {}".format(e))
            exit(1)

    @classmethod
    def is_session_valid(cls):
        """Check if the Node has a valid session id. Raise exceptions if
        there is no session id or if the session id has expired."""

        if not cls.SESSION_ID:
            logging.warning(
                "Tried to perform a request but no session exists."
            )
            raise UnauthorizedException()

        if int(datetime.now().strftime('%s')) >= cls.SESSION_EXPIRATION_TIME:
            logging.info("Session {} expired.".format(cls.SESSION_ID))
            raise SessionExpiredException()

    @classmethod
    def get_session(cls):
        """Get a new Supervisor REST session id. Retry if required."""

        # Setup the URL for this request
        url = 'getsession/nodename/{name}/nodekey/{key}/'.format(
            name=NODE['NAME'],
            key=NODE['KEY']
        )

        logging.info("Trying to acquire session id from {}.".format(
            SUPERVISOR['HOST']
        ))

        response = cls.__get(url)

        if response.status_code == UNAUTHORIZED:
            # If not authorized rise an exception
            logging.info("Node unauthorized.")
            raise UnauthorizedException()
        elif response.status_code == OK:
            # Parse the recived data
            try:
                data = response.text
                data = parse(data)

                cls.SESSION_ID = data['session']['id']
                cls.SESSION_EXPIRATION_TIME = int(data['session']['expires'])
            except ValueError as e:
                logging.error(
                    "Error while parsing session expiration time: {}.".format(
                        e)
                )
            except Exception as e:
                logging.error(
                    "Error while parsing response: {}\n{}.".format(data, e)
                )
                raise

        logging.info(
            "Successfully acquired session id {}.".format(cls.SESSION_ID)
        )
        logging.info(
            "Session will expire on {}.".format(datetime.fromtimestamp(
                cls.SESSION_EXPIRATION_TIME).strftime('%c'))
        )

    @classmethod
    def end_session(cls):
        """End the Supervisor REST session if there is any. If not fail
        silently."""

        # If the session isn't valid then job finished ;)
        try:
            cls.is_session_valid()
        except:
            logging.warning(
                "Tried to end session but no active session exist."
            )
            return

        # Otherwise prepare the URL and perform the request
        url = 'endsession/sessionid/{}/'.format(cls.SESSION_ID)

        logging.info("Trying to end session {}.".format(cls.SESSION_ID))

        response = cls.__get(url)

        if response.status_code == NOT_FOUND:
            logging.warning(
                "There was no session with the given id."
            )
        elif response.status_code == OK:
            logging.info("Session ended successfully.")

    @classmethod
    def post_report(cls):
        """Post the Node report to the Supervisor."""

        cls.is_session_valid()

        # Prepare the URL
        url = 'postreport/sessionid/{}/'.format(cls.SESSION_ID)

        # Prepare the report
        report = {
            'report': {
                'version': NODE['VERSION'],
                'memory': get_free_memory(),
                'disk': get_free_diskspace(),
                'frequency': get_processor_frequency(),
                'languages': {
                    'language': LANGUAGES.keys(),
                }
            }
        }

        # Generate the XML
        report = unparse(report)

        response = cls.__post(
            url,
            data=report,
            headers={'Content-Type': 'application/xml'}
        )

        if response.status_code == UNAUTHORIZED:
            logging.warning("Node unauthorized.")
            raise UnauthorizedException()
        elif response.status_code == CONFLICT:
            logging.warning("Session expired while performing the request.")
            raise SessionExpiredException()
        elif response.status_code == OK:
            logging.info("Succesfully posted Node report.")
        elif response.status_code == BAD_REQUEST:
            # This should never happen
            logging.critical("Request malformed. Exiting.\n{}".format(report))
            exit(1)

    @classmethod
    def get_submission(cls):
        """Get a new submission for judging."""

        cls.is_session_valid()

        # Prepare the URL
        url = 'getsubmission/sessionid/{}/'.format(cls.SESSION_ID)

        response = cls.__get(url)

        if response.status_code == OK:
            # If everyhing is okay then parse the data and return it
            try:
                data = response.text
                data = parse(data)
            except Exception as e:
                logging.error(
                    "Error while parsing response: {}\n{}.".format(data, e)
                )
                raise

            logging.info(
                "Recived submission id {}.".format(data['submission']['sid'])
            )
            return data['submission']

        elif response.status_code == NOT_FOUND:
            logging.info("No submission recived.")
            raise NotFoundException()
        elif response.status_code == UNAUTHORIZED:
            logging.warning("Node unauthorized.")
            raise UnauthorizedException()
        elif response.status_code == CONFLICT:
            logging.warning("Session expired while performing the request.")
            raise SessionExpiredException()

    @classmethod
    def post_submission(cls, submissionId, submission):
        """Post a judged submission to the Supervisor."""

        cls.is_session_valid()

        url = 'postsubmission/sessionid/{}/submissionid/{}/'.format(
            cls.SESSION_ID,
            submissionId
        )

        # Prepare the submission
        data = {
            'submission': submission,
        }

        # Change it to XML and send
        try:
            data = unparse(data)
        except:
            logging.critical("Data malformed {}.".format(data))
            raise

        response = cls.__post(
            url,
            data=data,
            headers={'Content-Type': 'application/xml'}
        )

        if response.status_code == OK:
            logging.info("The results have been sent.")
        elif response.status_code == UNAUTHORIZED:
            logging.warning("Node unauthorized.")
            raise UnauthorizedException()
        elif response.status_code == CONFLICT:
            logging.warning("Session expired while performing the request.")
            raise SessionExpiredException()
        elif response.status_code == BAD_REQUEST:
            # This should never happen
            logging.critical("Request malformed. Exiting.\n{}".format(data))
            exit(1)

    @classmethod
    def get_test_timestamps(cls, problemId):
        """Get the timestamps for the tests for the problem with a given id."""

        cls.is_session_valid()

        url = 'gettesttimestamps/sessionid/{}/problemid/{}/'.format(
            cls.SESSION_ID,
            problemId
        )

        response = cls.__get(url)

        if response.status_code == OK:
            try:
                data = response.text
                data = parse(data)
            except Exception as e:
                logging.error(
                    "Error while parsing response: {}\n{}.".format(data, e)
                )
                raise

            logging.info(
                "Recived test timestamps for problem {}.".format(problemId)
            )
            return data['test']

        elif response.status_code == NOT_FOUND:
            logging.info(
                "No test timestamps for problem {}.".format(problemId)
            )
            raise NotFoundException()
        elif response.status_code == UNAUTHORIZED:
            logging.warning("Node unauthorized.")
            raise UnauthorizedException()
        elif response.status_code == CONFLICT:
            logging.warning("Session expired while performing the request.")
            raise SessionExpiredException()

    @classmethod
    def get_tests(cls, problemId, testType, path):
        """Get the tests for the problem with a given id as a file path."""

        # There are only 3 types of test files
        if testType not in ('in', 'out', 'conf'):
            raise TypeError("Type not recognized: {}.".format(testType))

        cls.is_session_valid()

        url = 'gettests/sessionid/{}/problemid/{}/{}/'.format(
            cls.SESSION_ID,
            problemId,
            testType
        )

        response = cls.__get(url)

        if response.status_code == OK:
            cls.__write_to_file(response, path)
        elif response.status_code == NOT_FOUND:
            logging.info("No tests for problem {}.".format(problemId))
            raise NotFoundException()
        elif response.status_code == UNAUTHORIZED:
            logging.warning("Node unauthorized.")
            raise UnauthorizedException()
        elif response.status_code == CONFLICT:
            logging.warning("Session expired while performing the request.")
            raise SessionExpiredException()

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
