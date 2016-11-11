'''
Created on 04/set/2014

'''
import falcon
import logging
import json
import sys
import upr_client
import base64
import parserXML
from online_workflow_manager import WorkflowManager
from manifestManager import ManifestManager

class GraphInfo(object):
    '''
    Class with the API for the REST call of the TVDM to get the user Graph information
    '''
    def __init__(self, instantiator, userGraphPath, config):
        '''
        Constructor
        '''
        self.instantiator = instantiator
        self.userGraphPath = userGraphPath
        self.config = config
        self.upr_client = upr_client.UPRClient(config.UPR_LOCATION)
	self.manifestManager = ManifestManager(config)
        
    def on_get(self, request, response):
        try:
            args = request.stream.read()
            self.instantiator.logger.info(request.method+" "+request.uri+" "+args)
            token = self.instantiator.TokenIP[self.get_client_address(request.env)]
            self.instantiator.logger.info("token " + token)
            try:
                if self.config.USE_LOCAL_FILE:
                    #self.instantiator.logger.info("entra " + self.config.USE_LOCAL_FILE)
                    fp = open(str(self.userGraphPath+'/'+token), 'r')
                    graph = json.load(fp)
                    fp.close()
                else:
                    #r = self.upr_client.get_user_ag(token)
                    #graph = parserXML.parseXml.parseAG(token, base64.b64decode(r.json()[0]['ag']))

                    # Call online WFM before getting RAG
                    wfm = WorkflowManager(token, "password", self.config.UPR_LOCATION, self.config.SPM_LOCATION, self.config.NED_ID, debug=True)
                    r = self.upr_client.get_user_rag(token)
                    graph = parserXML.parseXml.parseAG(token, base64.b64decode(r.json()['asg']))
            except Exception as exc:
                self.instantiator.logger.error("Unable to read file "+self.userGraphPath+'/'+token)
                raise exc

            self.instantiator.logger.debug("----->>\n\ngraph: %s\n" % (str(graph)))

            # write token in the sg body
            graph['user_token'] = token
	    userTVD = self.instantiator.userTVDs[token]
            userTVD.psaID_first = graph['ingress_flow'][0]
            userTVD.psaID_last = graph['ingress_flow'][-1]
            self.instantiator.logger.info("userTVD" + str(userTVD))
            self.instantiator.logger.info("psaID_first %s \npsaID_last %s" % (str(userTVD.psaID_first), str(userTVD.psaID_last)))
            for newPSA in graph['PSASet']:
                PSAid = newPSA['id']
		PSAdata = self.manifestManager.getManifest(PSAid)
              #  self.instantiator.logger.info("PSAdta---> " + str(PSAdata))
                if "IP" in PSAdata.keys() and PSAdata['IP']:
		    userTVD.associateIPPSA(PSAid)

            response.body = json.dumps(graph)
            response.status = falcon.HTTP_200
        except Exception as e:
            self.instantiator.logger.exception(sys.exc_info()[0])
            response.status = falcon.HTTP_501

    def get_client_address(self,environ):
        """
        Get IP of requestor
        """
        try:
           # self.instantiator.logger.info("get_client" + str(environ) )
               # self.instantiator.logger.info("resposta client:  " + str(environ['HTTP_X_FORWARDED_FOR'].split(',')[-1].strip()) )
            return environ['HTTP_X_FORWARDED_FOR'].split(',')[-1].strip()
        except KeyError:
            return environ['REMOTE_ADDR']        
