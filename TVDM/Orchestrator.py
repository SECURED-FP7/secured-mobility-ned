import falcon
import json
from threading import Thread
from threading import Event
import thread
from GraphInstatiator import GraphInstantiator
import logging
import sys
import subprocess
import time


class Orchestrator(object):
    '''
    Orchestrator class that intercept the REST call through the WSGI server
    '''

    def __init__(self, instantiator, TVDMigration):
        '''
        Constructor
        '''
        self.instantiator = instantiator
        self.TVDMigration = TVDMigration
        self.migrate = False
        self.eventList = {}
        self.handoverEvents = {}

    def on_delete(self, request, response):
        try:
            args = request.stream.read()
            self.instantiator.logger.info(request.method + " " + request.uri + " " + args)
            session = json.loads(args, 'utf-8')
            token = self.instantiator.IPandUser[session["IP"]]
            newTVD = Thread(target=self.instantiator.deleteUser, kwargs={"session": session})
            newTVD.start()
            response.status = falcon.HTTP_200
        except Exception as e:
            self.instantiator.logger.exception(sys.exc_info()[0])
            response.status = falcon.HTTP_501

    ######start migration code############

    def on_put(self, request, response):
        '''
        shared by the instantiation and migration of TVD
        '''
        try:
            args = request.stream.read()
            session = json.loads(args, 'utf-8')
            self.instantiator.logger.info(request.method + " " + request.uri + " " + json.dumps(session, indent=4, sort_keys=True))
            newTVD = Thread(target=self.instantiator.instatiateTVD, kwargs={"session": session})
            newTVD.start()
            response.status = falcon.HTTP_200
        except Exception as e:
            self.instantiator.logger.exception(sys.exc_info()[0])
            response.status = falcon.HTTP_501

    def on_post(self, request, response):
        '''
        exclusive for migration
        '''
        try:
            args = request.stream.read()
            self.TVDMigration.instantiator.logger.info(request.method + " " + request.uri + " " + args)
            session = json.loads(args, 'utf-8')
            self.eventList[session["token"]] = Event()
            self.handoverEvents[session["token"]] = Event()
            migration = Thread(name=session["token"], target=self.TVDMigration.init_migration,
                               args=(self.eventList[session["token"]], self.handoverEvents[session["token"]],), kwargs={"session": session})
            migration.start()
            response.status = falcon.HTTP_200
        except:
            self.TVDMigration.instantiator.logger.exception(sys.exc_info()[0])
            response.status = falcon.HTTP_500

    def get_client_address(self, environ):

        try:

            return environ['HTTP_X_FORWARDED_FOR'].split(',')[-1].strip()

        except KeyError:

            return environ['REMOTE_ADDR']



    def on_get(self, request, response):
        '''
        Exclusive for migration, non-bloking query migration
        '''
        try:
            self.TVDMigration.instantiator.logger.info(request.method + " " + request.uri)
            user = request.get_param("user")

            if user in self.eventList.keys():
                self.TVDMigration.instantiator.logger.info("user: %s, eventList: %s" % (str(user), str(self.eventList[user].isSet())))
                obj = {"status": self.eventList[user].isSet()}
                if self.eventList[user].isSet() is True:
                    self.handoverEvents[user].set()

            else:
                obj = {"status": False}

            response.body = json.dumps(obj)
            response.status = falcon.HTTP_200

        except:
            self.instantiator.logger.exception(sys.exc_info()[0])
            response.status = falcon.HTTP_501
    #######end migration code##############
