import commands
import json

from manifestManager import ManifestManager


class UserTVD(object):
    '''
    User TVD class in case of IPSEC NED configuration
    '''

    def __init__(self, userName, vlanID, networkManager, computeManager, config, logger, userInterface,
                 migration=False, mobility=False):

        self.logger = logger
        self.networkManager = networkManager
        ###start migration code###
        if migration:
            self.userInterface = userInterface
            commands.createNewPort('brData', self.userInterface)
            self.logger.info("entra migracio")
        else:
            ###end migration code###
            self.userInterface = self.networkManager.generatePort('brData')
            self.logger.info("entra intanciacio")

        self.interfaceIP, result = self.networkManager.generateRoutingTable(self.userInterface)
        self.logger.debug("\n\n->>> [RoutingTable] Interface %s, IP %s result: \n %s" % (str(self.userInterface), str(self.interfaceIP), str(result)))
        self.userName = userName
        self.userIP = []
        self.vlanID = vlanID
        self.pscAddr = None
        self.psc = None
        self.generatedFlows = []
        self.computeManager = computeManager
        self.config = config
        self.psaList = []
        self.psaIPaddresses = {}
        self.manifestManager = ManifestManager(config)
        self.migration = migration
        self.iprules = {}
        self.psaID_first = None
        self.psaID_last = None
        self.mobility = mobility
        self.ofPorts = {}
       
    def addNewIP(self, newIP):
        '''
            Add a new machine on the TVD with the given IP
        '''
        if newIP not in self.userIP:
            self.userIP.append(newIP)
            commands.addIPrule(table=self.userInterface, addressFrom=newIP + "/32", pref=2, netns="default")
            commands.addIPrule(table=self.userInterface, addressTo=newIP + "/32", pref=2, netns="default")

    def delUserIP(self, newIP):
        '''
        Remove the flow for the given IP
        '''
        self.userIP.remove(newIP)
        commands.delIPrule(table=self.userInterface, addressFrom=newIP + "/32", pref=2, netns="default")
        commands.delIPrule(table=self.userInterface, addressTo=newIP + "/32", pref=2, netns="default")

    def setPSC(self, newPSC, pscAddr):
        '''
    Configure the PSC of the TVD
    '''
        self.psc = newPSC
        self.pscAddr = pscAddr
        self.logger.info("User " + self.userName + " PSC addr: " + pscAddr)

    def generatePSCflows(self):
        '''
        Generete the flow for the PSC
        '''
        flow = {}
        bridgeName = 'brData'
        flow['priority'] = "10"
        match = {}
        match['in_port'] = self.userInterface
        self.ofPorts[self.userInterface] = commands.findPort(bridgeName, self.userInterface) 
        match['dl_type'] = "0x0806"
        match['nw_dst'] = self.config.PSC_DP_IF_IP
        flow['match'] = match
        action = {}
        action['output'] = self.psc['interfaces'][2]['name']
        self.ofPorts[self.psc['interfaces'][2]['name']] = commands.findPort(bridgeName, self.psc['interfaces'][2]['name'])
        flow['action'] = action
        self.networkManager.generateFlow('brData', flow)
        self.generatedFlows.append(flow)

        flow = {}
        flow['priority'] = "10"
        match = {}
        match['in_port'] = self.userInterface
        match['dl_type'] = "0x0800"
        match['nw_dst'] = self.config.PSC_DP_IF_IP
        flow['match'] = match
        action = {}
        action['output'] = self.psc['interfaces'][2]['name']
        flow['action'] = action
        self.networkManager.generateFlow('brData', flow)
        self.generatedFlows.append(flow)

        flow = {}
        match = {}
        match['in_port'] = self.psc['interfaces'][2]['name']
        flow['match'] = match
        action = {}
        action['output'] = self.userInterface
        flow['action'] = action
        self.networkManager.generateFlow('brData', flow)
        self.generatedFlows.append(flow)

    def deleteAllTVD(self):
        '''
        Delete the TVD
        '''
        self.logger.info("Deleting " + self.userName + " TVD")
        for ip in self.userIP:
            self.deleteTVD(ip)

    def deleteTVD(self, IPaddr, migration=False):
        '''
        Remove an IP from the TVD in case of the last IP the TVD will be deleted
        '''
        self.logger.info("Removing IP " + IPaddr)
        self.delUserIP(IPaddr)
        if len(self.userIP) > 0:
            return False
        self.logger.info("Deleting flows: %s" % (str(self.generatedFlows)))
        for flow in self.generatedFlows:
            if migration is False:
                self.networkManager.deleteFlow('brData', flow)
            else:
                self.networkManager.deleteFlow_migration('brData', flow, ofPorts=self.ofPorts)


        self.logger.info("Deleting the user Interface")
        self.networkManager.deletePort('brData', self.userInterface)

        ##self.logger.info("Deleting PSC %s\n" % (json.dumps(self.psc, indent=4, sort_keys=True)))
        if self.psc is not None:
            self.computeManager.deleteNF(self.psc['name'])

        self.logger.info("Deleting PSA")
        for psa in self.psaList:
            self.computeManager.deleteNF(psa['name'])

        logLine = "PSA:"
        for ipAddr in self.psaIPaddresses.values():
            logLine = logLine + " " + ipAddr
        logLine = logLine + ", PSC: " + self.pscAddr + " removed"
        self.logger.info(logLine)
        return True

    def deleteFlows(self,IPaddr):

        for flow in self.generatedFlows:
            self.networkManager.deleteFlow_migration('brData', flow)
            self.generatedFlows.remove(flow)

    def associateIPPSA(self, psaID, ip=None):
        '''
        Associate an IP on a PSA
        '''

        ###start migration code####
        if self.migration:
            ipAddr = ip
            self.psaIPaddresses[psaID] = ip
        else:
        ###end migration code###
            ipAddr = self.networkManager.getPSAnewAddress()
            self.psaIPaddresses[psaID] = ipAddr
        self.logger.info("User " + self.userName + " PSA " + psaID + " addr: " + ipAddr)


    def definePSA(self, psaID):
        '''
        Define a new PSA for the TVD
        '''
        manifest = self.manifestManager.getManifest(psaID)
        properties = {}
        properties['memory'] = manifest['memory']
        properties['vcpu'] = manifest['vcpu']
        properties['interfaces'] = []

        interface = {}
        interface['bridge'] = "brData"
        interface['name'] = self.networkManager.generateVMPort()
        properties['interfaces'].append(interface)

        interface = {}
        interface['bridge'] = "brData"
        interface['name'] = self.networkManager.generateVMPort()
        properties['interfaces'].append(interface)

        interface = {}
        interface['vlan'] = self.vlanID
        interface['bridge'] = "brCtl"
        interface['name'] = self.networkManager.generateVMPort()
        properties['interfaces'].append(interface)

        return properties

    def instantiatePSA(self, PSAList):
        '''
        Instantiate the PSAs for the TVD
        '''
        for psa in PSAList:
            ###start migration code####
            if self.migration:
                psaProperties = psa
            else:
                ###end migration code###
                psaProperties = self.definePSA(psa['id'])
            ###start migration code###
            if self.migration:
                psaName = psa['name']
                for interface in psa['interfaces']:
                    self.logger.info("psa interface " + interface['bridge'] + " " + interface['name'])
                    #commands.createNewPort(interface['bridge'], interface['name'])
            else:
                ###end migration code###
                psaName = self.computeManager.instantiateNF(psa['id'], psaProperties)
            psaProperties['name'] = psaName
            for interface in psaProperties['interfaces']:
                self.logger.info("psa interface " + interface['bridge'] + " " + interface['name'])
                self.logger.info("lastinterface " + self.userInterface)
            self.psaList.append(psaProperties)

        self.logger.info("\n\n [userTVD] PSAList:\n%s" % (json.dumps(self.psaList, indent=4, sort_keys=True)))
        lastInterface = self.userInterface
        for psa in self.psaList:
            flow = {}
            bridgeName = 'brData'
            match = {}
            match['in_port'] = lastInterface
            self.ofPorts[lastInterface] = commands.findPort(bridgeName, lastInterface)
            flow['match'] = match
            action = {}
            action['output'] = psa['interfaces'][0]['name']
            self.ofPorts[psa['interfaces'][0]['name']] = commands.findPort(bridgeName, psa['interfaces'][0]['name'])
            flow['action'] = action
            self.networkManager.generateFlow('brData', flow)
            self.generatedFlows.append(flow)
            flow = {}
            match = {}
            match['in_port'] = psa['interfaces'][0]['name']
            flow['match'] = match
            action = {}
            action['output'] = lastInterface
            flow['action'] = action
            self.logger.info("flows2 " + str(flow))
            self.networkManager.generateFlow('brData', flow)
            self.generatedFlows.append(flow)
            lastInterface = psa['interfaces'][1]['name']
        flow = {}
        bridgeName = 'brData'
        match = {}
        match['in_port'] = lastInterface
        self.ofPorts[lastInterface] = commands.findPort(bridgeName, lastInterface)
        flow['match'] = match
        action = {}
        action['output'] = self.config.EXIT_INTERFACE
        self.ofPorts[self.config.EXIT_INTERFACE] = commands.findPort(bridgeName, self.config.EXIT_INTERFACE)
        flow['action'] = action
        self.logger.info("flows3 " + str(flow))
        self.networkManager.generateFlow('brData', flow)
        self.generatedFlows.append(flow)

        flow = {}
        flow['priority'] = "10"
        bridgeName = 'brData'
        match = {}
        match['in_port'] = self.config.EXIT_INTERFACE
        match['dl_type'] = "0x0806"
        match['nw_dst'] = self.interfaceIP
        flow['match'] = match
        action = {}
        action['output'] = lastInterface
        self.ofPorts[lastInterface] = commands.findPort(bridgeName, lastInterface)
        flow['action'] = action
        self.logger.info("flows4 " + str(flow))
        self.networkManager.generateFlow('brData', flow)
        self.generatedFlows.append(flow)

        flow = {}
        flow['priority'] = "10"
        bridgeName = 'brData'
        match = {}
        match['in_port'] = self.config.EXIT_INTERFACE
        match['dl_type'] = "0x0800"
        match['nw_dst'] = self.interfaceIP
        flow['match'] = match
        action = {}
        action['output'] = lastInterface
        self.ofPorts[lastInterface] = commands.findPort(bridgeName, lastInterface)
        flow['action'] = action
        self.logger.info("flows5 " + str(flow))
        self.networkManager.generateFlow('brData', flow)
        self.generatedFlows.append(flow)

        for ipAddr in self.psaIPaddresses.values():
            flow = {}
            bridgeName = 'brData'
            flow['priority'] = "10"
            match = {}
            match['in_port'] = self.config.EXIT_INTERFACE
            match['dl_type'] = "0x0806"
            match['nw_dst'] = ipAddr
            flow['match'] = match
            action = {}
            action['output'] = lastInterface
            self.ofPorts[lastInterface] = commands.findPort(bridgeName, lastInterface)
            flow['action'] = action
            self.logger.info("flows6 " + str(flow))
            self.networkManager.generateFlow('brData', flow)
            self.generatedFlows.append(flow)

            flow = {}
            flow['priority'] = "10"
            match = {}
            match['in_port'] = self.config.EXIT_INTERFACE
            match['dl_type'] = "0x0800"
            match['nw_dst'] = ipAddr
            flow['match'] = match
            action = {}
            action['output'] = lastInterface
            flow['action'] = action
            self.logger.info("flows7 " + str(flow))
            self.networkManager.generateFlow('brData', flow)
            self.generatedFlows.append(flow)

        for ipAddr in self.userIP:
            flow = {}
            flow['priority'] = "10"
            match = {}
            match['in_port'] = self.config.EXIT_INTERFACE
            match['dl_type'] = "0x0806"
            match['nw_dst'] = ipAddr
            flow['match'] = match
            action = {}
            action['output'] = lastInterface
            flow['action'] = action
            self.logger.info("flows8 " + str(flow))
            self.networkManager.generateFlow('brData', flow)
            self.generatedFlows.append(flow)

            flow = {}
            flow['priority'] = "10"
            match = {}
            match['in_port'] = self.config.EXIT_INTERFACE
            match['dl_type'] = "0x0800"
            match['nw_dst'] = ipAddr
            flow['match'] = match
            action = {}
            action['output'] = lastInterface
            flow['action'] = action
            self.logger.info("flows9 " + str(flow))
            self.networkManager.generateFlow('brData', flow)
            self.generatedFlows.append(flow)

