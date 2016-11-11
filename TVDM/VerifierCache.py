import threading
import requests
import ast
import falcon
import time
import json

class VerifierCache(threading.Thread):
    def __init__(self,conf):
        super(VerifierCache, self).__init__(group = None, target = None, name = None, verbose = None)
        self.config = conf
        self.verifier_url = conf.VERIFIER_URL
        self.ssids_cache = {}
        ssids_list = None
        try:
        	ssids_list = open("ssids_list")
        except Exception as e:
        	print ("Error reading ssids list file")
        	print str(e.message)
        if ssids_list:
        	for ssid in ssids_list:
        		self.ssids_cache[ssid.strip()] = "untrusted"
        self.stopevent = threading.Event()

        

    def askVerifier(self):
    	for ssid, t in self.ssids_cache.items():
            info = self.config.migration_ned_info(ssid)
            if type(info) is str:
                info =  ast.literal_eval(info)
            name = info['verifier']['name']
            digest = info['verifier']['digest']
            timeout = 3.0

            try:
                integrity = "l_req=l4_ima_all_ok|>="
                postData = {"hosts":[name],"analysisType":"load-time+check-cert,"+integrity+",cert_digest="+digest}  
                postData = json.dumps(postData)
                r = requests.post(self.verifier_url, data=postData, headers={'Content-Type':'application/json'}, verify=False, timeout=timeout)
            	r = r.json()
                self.ssids_cache[ssid] = r['results'][0]['trust_lvl']
                print "%s: %s" % (ssid, self.ssids_cache[ssid])
            except Exception as e:
            	print ("Error asking verifier for %s" % name)
            	print str(e.message)
            	self.ssids_cache[ssid] = "untrusted"

    def run(self):
    	while not self.stopevent.isSet():
    		self.askVerifier()
                self.stopevent.set()
    		#time.sleep(60)

    def join(self, timeout=None):
        super(VerifierCache, self).join(timeout)
        self.stopevent.set()

    def on_get(self, request, response):
    	ssid = request.get_param("ssid")
    	response.body = self.ssids_cache[ssid]
        response.status = falcon.HTTP_200





