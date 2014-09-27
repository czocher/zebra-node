#! /usr/bin/env python
#-*- coding: utf8 -*-

from settings import SUPERVISOR, NODE, LANGUAGES
from utils import get_free_memory, get_free_diskspace, get_processor_frequency

from httplib import HTTPConnection, HTTPException, UNAUTHORIZED, NOT_FOUND, \
    BAD_REQUEST, OK, CONFLICT
from datetime import datetime
from sys import exit
from xmltodict import parse, unparse

import logging
import os

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

    CONNECTION = None
    SESSION_ID = None

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
    def _get_connection(cls):
        """Get the HTTPConnection object, create it if needed."""

        if not cls.CONNECTION:
            try:
                cls.CONNECTION = HTTPConnection(SUPERVISOR['HOST'])
            except HTTPException as e:
                logging.critical("Connection failed: {}".format(e))
                exit(1)

        return cls.CONNECTION

    @classmethod
    def get_session(cls):
        """Get a new Supervisor REST session id. Retry if required."""

        c = RESTConnection._get_connection()

        # Setup the URL for this request
        url = SUPERVISOR['REST_URL_PREFIX'] + 'getsession/nodename/' \
            + NODE['NAME'] + '/nodekey/' + NODE['KEY'] + '/'

        logging.info(
            "Trying to acquire session id from {}.".format(
                "http://" + SUPERVISOR['HOST'] + SUPERVISOR['REST_URL_PREFIX']
            )
        )

        try:
            c.request('GET', url)
            response = c.getresponse()
        except Exception as e:
            logging.critical(
                "Request failed: {}.".format(e)
            )
            exit(1)

        if response.status == UNAUTHORIZED:
            # If not authorized rise an exception
            logging.info("Node unauthorized. Retrying in {} seconds.".format(
                NODE['QUERY_TIME'])
            )
            raise UnauthorizedException()
        elif response.status == OK:
            # Parse the recived data
            try:
                data = response.read()
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

        c = RESTConnection._get_connection()

        # If the session isn't valid then job finished ;)
        try:
            cls.is_session_valid()
        except:
            logging.warning(
                "Tried to end session but no active session exist."
            )
            return

        # Otherwise prepare the URL and perform the request
        url = SUPERVISOR['REST_URL_PREFIX'] + 'endsession/sessionid/' \
            + cls.SESSION_ID + '/'

        logging.info("Trying to end session {}.".format(cls.SESSION_ID))

        c.request('GET', url)
        response = c.getresponse()

        if response.status == NOT_FOUND:
            logging.warning(
                "There was no session with the given id."
            )
        elif response.status == OK:
            logging.info("Session ended successfully.")

    @classmethod
    def post_report(cls):
        """Post the Node report to the Supervisor."""

        c = RESTConnection._get_connection()

        cls.is_session_valid()

        # Prepare the URL
        url = SUPERVISOR['REST_URL_PREFIX'] + 'postreport/sessionid/' \
            + cls.SESSION_ID + '/'

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

        c.request('POST', url, body=report,
                  headers={'Content-Type': 'application/xml'})
        response = c.getresponse()

        if response.status == UNAUTHORIZED:
            logging.warning("Node unauthorized.")
            raise UnauthorizedException()
        elif response.status == CONFLICT:
            logging.warning("Session expired while performing the request.")
            raise SessionExpiredException()
        elif response.status == OK:
            logging.info("Succesfully posted Node report.")
        elif response.status == BAD_REQUEST:
            # This should never happen
            logging.critical("Request malformed. Exiting.\n{}".format(report))
            exit(1)

    @classmethod
    def get_submission(cls):
        """Get a new submission for judging."""

        c = RESTConnection._get_connection()

        cls.is_session_valid()

        # Prepare the URL
        url = SUPERVISOR['REST_URL_PREFIX'] + 'getsubmission/sessionid/' \
            + cls.SESSION_ID + '/'

        c.request('GET', url)
        response = c.getresponse()

        if response.status == OK:
            # If everyhing is okay then parse the data and return it
            try:
                data = response.read()
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

        elif response.status == NOT_FOUND:
            logging.info("No submission recived.")
            raise NotFoundException()
        elif response.status == UNAUTHORIZED:
            logging.warning("Node unauthorized.")
            raise UnauthorizedException()
        elif response.status == CONFLICT:
            logging.warning("Session expired while performing the request.")
            raise SessionExpiredException()

    @classmethod
    def post_submission(cls, submissionId, submission):
        """Post a judged submission to the Supervisor."""

        c = RESTConnection._get_connection()

        cls.is_session_valid()

        url = SUPERVISOR['REST_URL_PREFIX'] + 'postsubmission/sessionid/' \
            + cls.SESSION_ID + '/submissionid/' + submissionId + '/'

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

        c.request('POST', url, body=data,
                  headers={'Content-Type': 'application/xml'})
        response = c.getresponse()

        if response.status == OK:
            logging.info("The results have been sent.")
        elif response.status == UNAUTHORIZED:
            logging.warning("Node unauthorized.")
            raise UnauthorizedException()
        elif response.status == CONFLICT:
            logging.warning("Session expired while performing the request.")
            raise SessionExpiredException()
        elif response.status == BAD_REQUEST:
            # This should never happen
            logging.critical("Request malformed. Exiting.\n{}".format(data))
            exit(1)

    @classmethod
    def get_test_timestamps(cls, problemId):
        """Get the timestamps for the tests for the problem with a given id."""

        c = RESTConnection._get_connection()

        cls.is_session_valid()

        url = SUPERVISOR['REST_URL_PREFIX'] + 'gettesttimestamps/sessionid/' \
            + cls.SESSION_ID + '/problemid/' + problemId + '/'

        c.request('GET', url)
        response = c.getresponse()

        if response.status == OK:
            try:
                data = response.read()
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

        elif response.status == NOT_FOUND:
            logging.info(
                "No test timestamps for problem {}.".format(problemId)
            )
            raise NotFoundException()
        elif response.status == UNAUTHORIZED:
            logging.warning("Node unauthorized.")
            raise UnauthorizedException()
        elif response.status == CONFLICT:
            logging.warning("Session expired while performing the request.")
            raise SessionExpiredException()

    @classmethod
    def get_tests(cls, problemId, testType, path):
        """Get the tests for the problem with a given id as a file path."""

        # There are only 3 types of test files
        if testType not in ('in', 'out', 'conf'):
            raise TypeError("Type not recognized: {}.".format(testType))

        c = RESTConnection._get_connection()

        cls.is_session_valid()

        url = SUPERVISOR['REST_URL_PREFIX'] + 'gettests/sessionid/' \
            + cls.SESSION_ID + '/problemid/' + problemId + '/' + testType + '/'

        c.request('GET', url)
        response = c.getresponse()

        if response.status == OK:
            cls.__write_to_file(response, path)
        elif response.status == NOT_FOUND:
            logging.info("No tests for problem {}.".format(problemId))
            raise NotFoundException()
        elif response.status == UNAUTHORIZED:
            logging.warning("Node unauthorized.")
            raise UnauthorizedException()
        elif response.status == CONFLICT:
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
            while True:
                data = response.read(1024)
                if not data:
                    break
                output.write(data)
