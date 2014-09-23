#! /usr/bin/env python
#-*- coding: utf8 -*-
from httplib import HTTPConnection, HTTPException
import logging
import xml.dom.minidom


class UnauthorizedException (StandardError):
    pass


class RESTConnection(object):
    '''
    Class using for communicating with other server using REST
    '''

    def __init__(self, host, name, key):
        self.host = host
        self.name = name
        self.key = key

    def connect(self):
        '''
        Connect using parameters set in constructor
        '''
        #TODO: Zmienić na HTTPS
        try:
            self.connection = HTTPConnection(self.host)
        except:
            raise Exception

    def GET(self, url, body="", notXML=False):
        '''
        Send GET request to server and receive answer
        @param url: specific URL used to specify site
        @param body: body of message in XML
        '''
        try:
            self.connect()
            self.connection.request("GET", url, body)
            response = self.connection.getresponse()
            self.response = response.read()
            self.connection.close()
            if response.status == 404 or response.status == 401:
                raise HTTPException
        except:
            logging.critical("Error during connecting to host")
            raise HTTPException
        try:
            if notXML == False and int(xml.dom.minidom.parseString(self.response).getElementsByTagName("status")[0].childNodes[0].data) == 200:
                raise UnauthorizedException
        except:
            raise UnauthorizedException

    def POST(self, url, body="", notXML=False):
        '''
        Send POST request to server and receive answer
        @param url: specific URL used to specify site
        @param body: body of message in XML
        '''
        try:
            self.connect()
            self.connection.request("POST", url, body)
            response = self.connection.getresponse()
            self.response = response.read()
            self.connection.close()
            if response.status == 404:
                raise HTTPException
        except Exception:
            logging.critical("Error during connecting to host")
            raise HTTPException
        try:
            if notXML == False and int(xml.dom.minidom.parseString(self.response).getElementsByTagName("status")[0].childNodes[0].data) == 200:
                raise UnauthorizedException
        except:
            raise UnauthorizedException
