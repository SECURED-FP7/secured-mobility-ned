#
#   File:       switch.py
#   @author:    UPC
#   Description:
#       NAT controller switch
#
import falcon
import json
import os
import sys
import subprocess


class Switch(object):

    def __init__(self, logger):

        self.logger = logger

    def on_delete(self, request, response):
        pass

    def on_post(self, request, response):
        try:
            args = request.stream.read()
            self.logger.info(request.method+" "+request.uri+" "+args)
            session = json.loads(args, 'utf-8')
            #target_host = session['target']
            route = session['route']
            cmd1 = "ip route del %s" % str(route['net'])
            cmd2 = "ip route add %s via %s" % (str(route['net']), str(route['nexthop']))
            try:
                result = subprocess.check_output(cmd1, shell=True)
                response.status = falcon.HTTP_200
            except Exception as e:
                self.logger.info("error: " + str(e))
            try:
                result2 = subprocess.check_output(cmd2, shell=True)
            except Exception as e:
                self.logger.info("error2: " + str(e))
                response.status = falcon.HTTP_500
            #response.status = falcon.HTTP_200
        except Exception as e:
            self.logger.exception(sys.exc_info()[0])
            response.status = falcon.HTTP_500

    def on_get(self, request, response):
        pass
