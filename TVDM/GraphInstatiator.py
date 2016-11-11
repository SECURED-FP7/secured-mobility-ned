'''
Created on 29/lug/2014

'''
import json
import subprocess, shlex
from Compute import Compute
from Network import Network
from userTVD import UserTVD
from userTVDIPSECLess import UserTVD as UserTVDIPSECLess
import requests
import ast
import commands

class GraphInstantiator(object):
    '''
    Class used to instantiate the TVD and the Profile Graph
    '''

    def __init__(self, configure, logger, useIPSEC=False):
        '''
        Constructor
        '''

        self.client_ip = None
        subprocess.call(["bash", configure.SCRIPT_LOCATION + "emptyDHCP.sh"])
        self.useIPSEC = useIPSEC
        self.IPandUser = {}  # Used to associate the token to the IP (for the logoutelf.IPandUser = {}  # Used to associate the token to the IP (for the logout
        self.logger = logger
        self.config = configure
        self.networkManager = Network(configure)
        self.computeManager = Compute(configure)
        self.userTVDs = {}  # All the generated TVD
        self.TokenIP = {}  # Associate the PSC IP to a specifc user
        self.sigTerm = False
        self.migration = False #flag migration
        self.psa_ip_route_table = int(configure.PSA_IP_ROUTE_TABLE)
        self.default_ssid = configure.DEFAULT_SSID
        self.local_info = configure.migration_ned_info(self.default_ssid)
        if type(self.local_info) is str:
            self.local_info = ast.literal_eval(self.local_info)
        self.local_host = self.local_info['ned_ip']
        self.local_port = int(self.local_info['ned_port'])
        self.defaultnamespace = configure.DEFAULT_NAME_SPACE
        self.default_ssid = configure.DEFAULT_SSID
        self.mobility = configure.MOBILITY
        self.ip_ext = configure.IP_EXT
        self.gw_ip = self.config.GATEWAY_IP


    def instatiateTVD(self, session):
        '''
        Intantiate the TVD for a logged user.
        In case for a TVD already instatiated it will generate the flows used for reedirecting the traffic of the
        new defice on it
        '''
        self.client_ip = str(session['IP'])


        if 'migration' in session:
            self.migration = bool(session['migration'])
            self.logger.info("INSTANTIATE TVD WITH migration=%s" % (str(session['migration'])))

        ###start migration code###
        if self.migration:
            self.logger.info("migration TVD " + str(session['IP']))
        else:
            self.logger.info("instantiation TVD")
        ###end migration code###

        self.logger.info("IP " + session['IP'])
        if not self.migration:
            if session['IP'] in self.IPandUser.keys():
                self.logger.info("Machine already logged")
                return

        self.IPandUser[session['IP']] = session['token']

        if session['token'] in self.userTVDs.keys():
            self.logger.info("psaLIST %s" % (str(session['PSAs'])))

            userTVD = self.userTVDs[session['token']]
            if self.migration:
                userTVD.migration = self.migration

            if userTVD.migration:
                self.logger.info("userTVD migration %s" % (str(userTVD.migration)))
            userTVD.addNewIP(str(session['IP']))
            userTVD.generatePSCflows()
            self.instantiatePSA(session)
            return

       ###start migraton Code###
        if self.migration:  # If the user TVD migrated
            vlanID = session['vlanID']
        else:
        ###end migration code###
            # If the user have no TVD instantiated
            vlanID = self.networkManager.getNewVLANID()

        ###start migraton Code###
        if self.migration:
            userInterface = session['userInterface']
            self.logger.info("userInterface   " + userInterface)
        else:
        ###end migration code###
            userInterface = None

        if self.useIPSEC:
            ###migration code->added parameters: userInterface and self.migration###
            newTVD = UserTVD(session['token'], vlanID, self.networkManager, self.computeManager, self.config,
                             self.logger, userInterface, self.migration, self.mobility)

        else:
            ###migration code->added parameters: userInterface and self.migration###
            newTVD = UserTVDIPSECLess(session['token'], vlanID, self.networkManager, self.computeManager, self.config,
                                      self.logger, userInterface, self.migration)


        self.userTVDs[session['token']] = newTVD

        # Generates the PSC for the user
        ###start migration code###
        if self.migration:
            mac = session['psc']['interfaces'][0]['mac']
        else:
        ###end migration code###
            mac = self.networkManager.generateMACaddress()

        ###start migration code###
        if self.migration:
            newPSC = session['psc']
        else:
        ###end migration code###
            newPSC = self.definePSC(vlanID, mac)

        ###start migration code###
        if self.migration:
            pscAddr = session['pscAddr']
        else:
        ###end migration code###
            pscAddr = self.networkManager.configureNewIPOnDHCP(mac, session['token'])

        self.logger.info("PSC address for user " + session['token'] + " " + pscAddr)
        self.TokenIP[pscAddr] = session['token']
        ###start migration code###
        if self.migration:
            pscName = session['pscName']
        else:
        ###end migration code###
            pscName = self.computeManager.instantiateNF('psc', newPSC)

        ##newPSC['name'] = pscName
        ##newTVD.setPSC(newPSC, pscAddr)
        ##self.logger.info("PSC created")

        newPSC['name'] = pscName
        newTVD.setPSC(newPSC, pscAddr)
        newTVD.generatePSCflows()
        self.logger.info("PSC created")

        newTVD.addNewIP(str(session['IP']))

        ###start migration code###
        if self.mobility:
            try:
                #self.logger.info("Session %s" % json.dumps(parsed, indent=4, sort_keys=True))
                headers = {'Content-Type': 'application/json', 'Accept': 'application/json'}

                if not 'ssid' in session:
                    info = self.local_info
                else:
                    info = self.config.migration_ned_info(session['ssid'])

                if type(info) is str:
                        info = ast.literal_eval(info)
                nat = info['nat']
                url = "http://%s:%s/switch" % (str(nat['server'][0]),str(nat['server'][1]))
                payload = {'route': nat['route']}
                self.logger.info("NAT Request URL: %s" % url)
                self.logger.info("NAT Request Payload: %s" % str(payload))
                r = requests.post(url, json=payload, headers=headers )
                self.logger.info("NAT request Response: %s" % str(r.status_code))
            except Exception as e:
                self.logger.error("NAT request error\n%s" % (str(e)))

        if self.migration:
            psaIPaddresses = session['psaIPaddresses'].items()
            for psa in  psaIPaddresses:
                psaID = psa[0]
                ip = psa[1]
                newTVD.associateIPPSA(psaID, ip)


        if self.migration:
            self.instantiatePSA(session)
        ###end migration code###



    def definePSC(self, vlanID, mac):
        '''
        Define the template for the PSC of the TVD
        '''

        properties = {}
        properties['memory'] = "512"
        properties['vcpu'] = "1"
        properties['interfaces'] = []

        interface = {}
        interface['mac'] = mac
        interface['bridge'] = "brCtl"
        interface['name'] = self.networkManager.generateVMPort()
        properties['interfaces'].append(interface)

        interface = {}
        interface['vlan'] = vlanID
        interface['bridge'] = "brCtl"
        interface['name'] = self.networkManager.generateVMPort()
        properties['interfaces'].append(interface)

        interface = {}
        interface['bridge'] = "brData"
        interface['name'] = self.networkManager.generateVMPort()
        properties['interfaces'].append(interface)

        return properties

    def deleteUser(self, session, migration=False):
        '''
        This function is used for the user log out. If there are multiple devices connected it will be deleted only the
        flows for the specifc device that did the log out.
        If the last device for that specific user is disconnected the graph will be destroyed
        '''
        if session['IP'] not in self.IPandUser.keys():
            self.logger.info("Machine not logged in")
            return
        token = self.IPandUser[session['IP']]

        if self.mobility:
            self.mobility_iprules(session, "delete", token)

        del self.IPandUser[session['IP']]
        userTVD = self.userTVDs[token]


        if userTVD.deleteTVD(session['IP'], migration=migration):
            del self.TokenIP[userTVD.pscAddr]
            del self.userTVDs[token]

    def instantiatePSA(self, session):
        '''
        Instantiate the PSA of the TVD
        '''
        global err, err
        PSAList = session['PSAs']
        self.logger.info("------> PSAList %s \n" %(json.dumps(PSAList)))
        oup = "egress flow: "
        if 'egress_flow' in session:
            for psa in session['egress_flow']:
                oup = oup + str(psa) + ", "
        oup = oup + "\n ingress flow: "
        if 'ingress_flow' in session:
            for psa in session['ingress_flow']:
                oup = oup + str(psa) + ", "
        self.logger.info("\n%s\n" %(str(oup)))

        userTVD = self.userTVDs[session['token']]
        userTVD.instantiatePSA(PSAList)
        
        self.logger.info("\n\n--> of FLOWS\n %s \n" %(json.dumps(userTVD.generatedFlows)))
        self.logger.info("\n\n--> ofPorts\n %s \n" %(json.dumps(userTVD.ofPorts)))      
  
        #######start migration code########
        if self.mobility:
            self.mobility_iprules(session, "add", None)
        #######stop migration code#########


    def signal_term_handler(self):
        '''
        Used on SIGTERM signal to destroy all the instantiated TVD
        '''
        if not self.sigTerm:
            self.sigTerm = True
            for userTVD in self.userTVDs.values():
                userTVD.deleteAllTVD()
            return True
        return False

    def get_default_gw(self, netns="default"):
        '''
        function to return the default gw ip
        '''
        strs = subprocess.check_output(shlex.split('ip netns exec '+ str(netns)+' ip r l'))
        gateway = strs.split('default via')[-1].split()[0]
        return gateway

    def mobility_iprules(self,session, adddel, token):

        if (adddel == "add"):
            userTVD = self.userTVDs[session['token']]
        else:
            userTVD = self.userTVDs[token]

        psaIPaddresses = userTVD.psaIPaddresses.items()
        ssid = self.config.DEFAULT_SSID
        info = self.config.migration_ned_info(ssid)
        if type(info) is str:
            info = ast.literal_eval(info)
        nat = info['nat']
        try:
            if 'default_gw' in nat:
                self.gw_ip = str(nat['default_gw'])
            else:
                self.gw_ip = str(nat['server'][0])
        except Exception as err:
            self.logger.info("----> error getting the default gw " + str(err))
            self.gw_ip = str(nat['server'][0])

        for psa in psaIPaddresses:
            psaID = psa[0]
            ip_psa = psa[1]
            self.logger.info("psaID " + psaID + " ip " + ip_psa)
            if (adddel == "add"):
                self.psa_ip_route_table += 1
                if session['token'] not in userTVD.iprules or type(userTVD.iprules[session['token']]) is not dict:
                    userTVD.iprules[session['token']] = {}
                if not ip_psa in userTVD.iprules[session['token']]:
                    userTVD.iprules[session['token']][ip_psa] = []
                self.logger.info("[Mobility] ip_psa %s tables %s" % (str(ip_psa), str(userTVD.iprules[session['token']][ip_psa])))
                if not self.psa_ip_route_table in userTVD.iprules[session['token']][ip_psa]:
                    self.logger.info("Cleaning ip route table %s ip_psa %s" % (str(self.psa_ip_route_table),str(ip_psa)))
                    commands.cleanRouteTable(table=str(self.psa_ip_route_table), netNs="default") 
                userTVD.iprules[session['token']][ip_psa].append(self.psa_ip_route_table)
                ##add ip rule from
                commands.addIPrule(table=self.psa_ip_route_table, addressFrom=ip_psa, pref=self.psa_ip_route_table, netns="default")
                ##add ip rule to
                commands.addIPrule(table=self.psa_ip_route_table, addressTo=ip_psa, pref=self.psa_ip_route_table, netns="default")
                ##add ip routes to the table
                result = commands.addRoute(table=self.psa_ip_route_table, addr=str(self.gw_ip), default=True, netNs="default")
                if result is not None: self.logger.warning("\n\n[mobility ip route] error add default route via %s table %s" % (str(self.gw_ip), str(self.psa_ip_route_table)))
                result = commands.addRoute(table=self.psa_ip_route_table, addr=str(ip_psa), via=str(self.ip_ext), netNs="default")
                if result is not None: self.logger.warning("\n\n[mobility ip route] error add route to %s via %s" % (str(self.ip_ext), str(ip_psa)))
            else:
                tables = []
                if ip_psa in userTVD.iprules[token]:
                    tables = userTVD.iprules[token][ip_psa]
                    self.logger.info("Cleaning ip route table and rules ip_psa %s tables %s" % (str(ip_psa), str(tables)))
                for table in tables:
                    commands.delIPrule(table=table, addressFrom=ip_psa, netns="default")
                    commands.delIPrule(table=table, addressTo=ip_psa, netns="default")
                    commands.cleanRouteTable(table=str(table), netNs="default")
