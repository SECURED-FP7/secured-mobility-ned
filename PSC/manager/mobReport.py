'''   

    File:       mobReport.py
    Created:    1/9/2015
  
    @author:    UPC
  
    Description:
        This Module handles the mobility of the nodes by accepting the
        reporting of AP data, returning whether the system needs to migrate
        or not. 

'''
import falcon
import json
import requests
import threading
import time



class WaitingMigrationThread(threading.Thread):

	def __init__(self,controller):
		super(WaitingMigrationThread, self).__init__(group = None, target = None, name = None, verbose = None)
		self.controller = controller


	def askStateMigration(self):
		data = {'user': self.controller.user}
		response = requests.get(self.controller.migration_uri,params=data)
		print("resp: " + str(response.content))
		r = json.loads(response.content.decode('utf-8'))
		return r["status"]

	def run(self):
		finished = False
		while not finished:
			print("ASK STATE!")
			finished = self.askStateMigration()
			if not finished:
				print("STILL MIGRATING")
			else:
				print("MIGRATION FINISHED!")
			time.sleep(1)
		self.controller.state = "HANDOVER"



class mobReport(object):

	def __init__(self):
		self.N = 4
		self.connections = {}
		self.migration_uri = "http://192.168.1.1:8080/migration"
		self.verify_uri = "http://192.168.1.1:8080/verify"
		#migration_uri = "http://127.0.0.1:8000/migration"
		#migration_uri = "http://www.google.com"

		self.INTERVAL_BETWEEN_HANDOVERS = 10
		self.connectionsSinceLastHandover = 0
		self.ssidMigration = ""
		self.bssidMigration = ""
		self.state = "IDLE"

		self.waitingThread = WaitingMigrationThread(self)

	def existsInArray(self,ssid,aps):
		for ap in aps:
			if ap["ssid"] == ssid:
				return True
		return False

	def getStrongestAP(self,aps):
		#delete from the connections those which are not active
		remainingSsids = [ssid for ssid in self.connections if self.existsInArray(ssid,aps)]

		conn2 = {}

		for ssid in remainingSsids:
			conn2[ssid] = self.connections[ssid]

		self.connections = conn2

		#adding the new signal received to the saved connections
		for ap in aps:
			print (ap["ssid"] + " " + ap["bssid"] + " " + str(ap["signal"]))
			if(str(ap["ssid"]) in self.connections.keys()):
				self.connections[ap["ssid"]]["signals"].append(ap["signal"])
				if(len(self.connections[ap["ssid"]]["signals"]) > self.N):
					self.connections[ap["ssid"]]["signals"].pop(0)
			else:
				self.connections[ap["ssid"]] = {"bssid": ap["bssid"],"signals": []}
				self.connections[ap["ssid"]]["signals"].append(ap["signal"])

		#calculate the new signals mean for each connection and getting the strongest one
		first = True
		m = 0
		for ssid,obj in self.connections.items():
			exp = -1
			final = 0
			signals = obj["signals"]
			for i in range(0,len(signals)) :
				if i < len(signals)-1:
					final += pow(2, exp) * signals[i]
				else:
					final += pow(2, exp+1) * signals[i]
				exp = exp-1

			obj["mean"] = final
			if first:
				m = final
				newAPssid = ssid
				newAPbssid = obj["bssid"]
				first = False
			elif final > m:
				m = final
				newAPssid = ssid
				newAPbssid = obj["bssid"]
		print("Strongest AP: " + newAPssid)

		return newAPbssid, newAPssid

	def get_client_address(self, environ):
		try:
			return environ['HTTP_X_FORWARDED_FOR'].split(',')[-1].strip()
		except KeyError:
			return environ['REMOTE_ADDR']

	def callMigration(self,user,ssid,ip):
		#headers = {'content-type': 'application/json','accept': 'application/json'}
		migration_info = {"token": user, "ssid":ssid, "IP": ip}
		print("MIGRATION REQUEST: " + str(migration_info))
		migration_info = json.dumps(migration_info)
		print ("sending: " + str(migration_info))
		response = requests.post(self.migration_uri, data=migration_info)
		#response = requests.get(migration_uri)
		#print("RESPONSE: " + response.content)


	def destinationNedIsTrusted(self, ssid):
		#verifier_info = {"ssid":ssid}
		#print("VERIFIER REQUEST: " + str(verifier_info))
		#verifier_info = json.dumps(verifier_info)
		verifier_url = "https://147.83.42.137/OAT/attest.php"
		ned_name = "ned"
		digest = "9ca6b5e5038819d7b55c830e95164e028a5cf686"
		used_integrity = "l_req=l4_ima_all_ok|>="
		postData = {"hosts":[ned_name],"analysisType":"load-time+check-cert,"+used_integrity+",cert_digest="+digest}
		postData = json.dumps(postData)
		print("VERIFIER REQUEST: " + str(postData))

		r = requests.post(verifier_url, data=postData, headers={'Content-Type':'application/json'}, verify=False)
		temp = r.json()
		print (str(r.content))
		return temp['results'][0]['trust_lvl'] == "trusted"

	'''	Takes the report JSON and checks if there is a strongest access
		point to connect.
		Also forms the response JSON to send to the client.
	'''

	def processReport(self,req):
		error = False
		errorMessage = ""
		report = None
		try:
			report = json.loads(req.stream.read().decode('utf-8'))
		except:
			error = True
			errorMessage = "Report JSON Malformed"
		if not error:
			responsejson = {}
			handOver = False
			self.user = report["user"]
			if self.state == "HANDOVER":
				handOver = True
				newAPbssid = self.bssidMigration
				newAPssid = self.ssidMigration
				print ("Hand Over needed. The best signal access point ssid is: " + self.ssidMigration)
			elif self.state == "IDLE":
				currentConnection = report["currentConnection"]
				aps = report["ap-list"]
				if not aps:
					error = True
					errorMessage = "Secured access points list is empty"
				else:
					strongestAPbssid, strongestAPssid = self.getStrongestAP(aps)
					if strongestAPssid != currentConnection["ssid"]:
						if self.connectionsSinceLastHandover > self.INTERVAL_BETWEEN_HANDOVERS:
							handOver = True
						else:
							print("Can't make too many handovers continuously")

				allowHandover = report["allowHandover"]
				if allowHandover == "no":
					print("Handover not allowed")
					handOver = False

				if(not error):
					if(handOver):
						trusted = self.destinationNedIsTrusted(strongestAPssid)
						print ("NED is trusted ? %s" % str(trusted))
						if trusted:
							self.state = "MIGRATING"
							print("STARTING MIGRATIOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOON")
							ip = self.get_client_address(req.env)
							self.callMigration(report["user"],strongestAPssid,ip)
							self.ssidMigration = strongestAPssid
							self.bssidMigration = strongestAPbssid
							self.waitingThread.start()
							print ("Migration needed. New AP: " + strongestAPssid + ". Migrating user data to the new access point NED")
						else:
							print ("Migration was triggered to %s but the ned is not trusted" % self.ssidMigration)
							handOver = False
							self.connectionsSinceLastHandover = self.connectionsSinceLastHandover + 1

			if not error:
				if self.state == "MIGRATING":
					responsejson["action"] = 1
					print ("Migrating...")
				elif self.state == "HANDOVER":
					responsejson["action"] = 2
					responsejson["bssid"] = self.bssidMigration
					responsejson["ssid"] = self.ssidMigration
					self.connectionsSinceLastHandover = 0
					print ("Hand Over needed. The strongest signal: " + self.ssidMigration)

                                        ### redefine the thread
                                        self.waitingThread = WaitingMigrationThread(self)
					self.state = "IDLE"
				else:
					print ("Hand Over not needed.")
					responsejson["action"] = 0
					self.connectionsSinceLastHandover = self.connectionsSinceLastHandover + 1
			else:
				print ("ERROR: " + errorMessage)
				responsejson["action"] = 3
				responsejson["error"] = errorMessage
				self.connectionsSinceLastHandover = self.connectionsSinceLastHandover + 1

			print("CONNECTIONS : " + str(self.connections))
			print("Requests since last handover: " + str(self.connectionsSinceLastHandover))
			return responsejson
		else:
			print ("ERROR: " + errorMessage)
			responsejson["action"] = 3
			responsejson["error"] = errorMessage
			self.connectionsSinceLastHandover = self.connectionsSinceLastHandover + 1

	def on_put(self, req, resp):
		print ("\n\n-------------------------PUT RECEIVED-----------------------------")
		responsejson = self.processReport(req)
		print ("SENDING: " + str(responsejson))
		resp.body = json.dumps(responsejson)


app = falcon.API()
mb = mobReport()
app.add_route('/mobReport', mb)
