#
#   File:       psaInterface.py
#   @author:    BSC, VTT
#   Description:
#       REST interface to receive configuration requests from the PSAs
#

import falcon
import json
import logging
import sys
from pscExceptions import pscExceptions
import threading
from time import sleep

class psaInterface():
    def __init__(self, confsPath):
        self.confsPath = confsPath
        self.psa_list = []
        self.psa_events = {}
    
    # Config is pulled by the PSA, also functions as a PSA UP event.
    # Stores every PSA IP and PSA ID that are up
    def on_get(self, request, response, psa_id):
        try:
            logging.info(request.method+" "+request.uri)
            try:
                fp = open(self.confsPath+"/"+psa_id, 'rb')
                conf = fp.read()
                fp.close()     
            except IOError as exc:
                logging.error("Unable to read file "+self.confsPath+"/"+psa_id)
                raise exc

            # Store current PSA ID and IP, if not present
            res = {"psa_id": psa_id, "ip": self.get_client_address(request.env)}
            if not res in self.psa_list:
                self.psa_list.append(res)
                with open(self.confsPath + "/psa_online", 'wb') as f:            
                    f.write(json.dumps(self.psa_list))
            
            response.data = conf
            response.status = falcon.HTTP_200
            logging.info("PSA "+psa_id+" configuration sent to "+self.get_client_address(request.env))
        
        except Exception as e:
            logging.exception(sys.exc_info()[0])
            response.status = falcon.HTTP_501

    def on_post(self, request, response, psa_id):
        logging.info(request.method+" "+request.uri + " " + psa_id)
        try:
            ev = json.loads(request.stream.read().decode('utf-8'))
            if self.verify_psa(psa_id, self.get_client_address(request.env)):
                if not psa_id in self.psa_events:
                    self.psa_events[psa_id] = []
                self.psa_events[psa_id].append(ev)
                with open(self.confsPath + "/psa_events", 'wb') as f:
                    f.write(json.dumps(self.psa_events))
                response.status = falcon.HTTP_200
            else:
                response.status = falcon.HTTP_403
        except Exception as e:
            logging.exception(sys.exc_info()[0])
            response.status = falcon.HTTP_501

    def verify_psa(self, psa_id, ip):
        logging.info("Verify event from PSA "+psa_id+", " + ip)
        ret = False
        for psa in self.psa_list:
            if psa["psa_id"] == psa_id:
                ret = psa["ip"] == ip
        logging.info("PSA valid: " + str(ret))
        return ret

    def get_client_address(self,environ):
        return environ['REMOTE_ADDR']

