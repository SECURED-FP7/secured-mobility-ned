import subprocess


def addIPrule(table, addressFrom=None, addressTo=None, pref=None, netns=None):
	'''
	Add an IP rule for a table
	:rtype: object
	'''
	command = ""
	if netns is not None:
		command = command + "ip netns exec " + netns + " ip rule add"
	else:
		command = command + "ip rule add"
	if addressFrom is not None:
		command = command + " from " + addressFrom
	if addressTo is not None:
		command = command + " to " + addressTo
	command = command + " table " + str(table)
	if pref is not None:
		command = command + " pref " + str(pref)
	subprocess.Popen(command, stdout=subprocess.PIPE, shell=True)

def delIPrule(table, addressFrom=None, addressTo=None, pref=None, netns=None):
	'''
	Add an IP rule for a table
	'''
	command = ""
	if netns is not None:
		command = command + "ip netns exec " + netns + " ip rule del"
	else:
		command = command + "ip rule del"
	if addressFrom is not None:
		command = command + " from " + addressFrom
	if addressTo is not None:
		command = command + " to " + addressTo
	command = command + " table " + str(table)
	if pref is not None:
		command = command + " pref " + str(pref)
	subprocess.Popen(command, stdout=subprocess.PIPE, shell=True)

def createNewPort(bridgeName, portName, netNs='default'):
	'''
	Create a new interface on a bridge
	'''
	subprocess.Popen("ip netns exec " + netNs + " ip link add " + portName + " type veth peer name " + portName[:11], stdout=subprocess.PIPE, shell=True).wait()
	subprocess.Popen("ovs-vsctl add-port " + bridgeName + " " + portName, stdout=subprocess.PIPE, shell=True).wait()

def deletePort(bridgeName, portName, netNs='default'):
	'''
	Create a new interface on a bridge
	'''
        subprocess.Popen("ovs-vsctl del-port " + bridgeName + " " + portName, stdout=subprocess.PIPE, shell=True)
	subprocess.Popen("ip netns exec " + netNs + " ip link del " + portName, stdout=subprocess.PIPE, shell=True)

def configureInterface(portName, netNs=None, ipAddr=None, addToNetNs=False, prefix=None, broadcast=None):
	'''
	Configure an interface with an IP address and insert into a specific network namespace
	'''
	if addToNetNs and netNs is not None:
		subprocess.Popen("ip link set " + portName + " netns " + netNs, stdout=subprocess.PIPE, shell=True).wait()
	if ipAddr is not None:
		if netNs is not None:
			subprocess.Popen("ip netns exec "+ netNs +" ip addr add " + ipAddr + "/"+prefix+" broadcast "+broadcast+ " dev " + portName, stdout=subprocess.PIPE, shell=True).wait()
		else:
			subprocess.Popen("ip addr add " + ipAddr + "/"+prefix+" broadcast "+broadcast+" dev " + portName, stdout=subprocess.PIPE, shell=True).wait()

	if netNs is not None:
		subprocess.Popen("ip netns exec "+ netNs +" ip link set " + portName + " up", stdout=subprocess.PIPE, shell=True).wait()
	else:
		subprocess.Popen("ip link set " + portName + " up", stdout=subprocess.PIPE, shell=True).wait()

def generateNewTable(tableID, interface):
	'''
	Generate a new routing table
	'''
	subprocess.Popen("echo \""+str(tableID)+" "+interface+"\" >> /etc/iproute2/rt_tables", shell=True)

###New addroute function with error control
def addRoute(table, addr, dev=None, default=False, via=None, src=None, netNs=None, tries=3):
        '''
        Add a route on the given routing table
        '''
        command = ""
        if netNs is not None:
                command = command + "ip netns exec " + netNs + " ip route add"
        else:
                command = command + "ip route add"
        if default:
                command = command + " default via"
        command = command + " " + addr # + " dev " + dev
        if via is not None and default is False:
            command = command + " via " + via
        if dev is not None:
            command = command + " dev " + dev
        if src is not None:
                command = command + " src " + src
        command = command + " table " + str(table)
        error = None
        for i in xrange(tries):
            try:
                subprocess.check_output(command, shell=True)
                error = None
                break;
            except subprocess.CalledProcessError as e:
                error = e
            except Exception as e:
                error = e
        return error
    
def cleanRouteTable(table, netNs=None):
        '''
        Clean a route table
        '''
        command = ""
        if netNs is not None:
                command = command + "ip netns exec " + netNs + " ip route flush table "
        else:
                command = command + "ip route flush table "
        command = command + str(table)
        subprocess.Popen(command, stdout=subprocess.PIPE, shell=True)

def generateFlow(flowJSON, bridgeName):
	'''
	Generates a flow on a bridge
	INPUT JSON:
	{
	priority: flow priority
	match: {map of match key->value}
	action: {map of actions key->value}
	}
	'''
	command = "ovs-ofctl add-flow " + bridgeName + " "
	noFirst = False
	if 'priority' in flowJSON.keys():
		priority = flowJSON['priority']
	else:
		priority = 1
	command = command + "priority=" + str(priority)
	noFirst = True
	for match in flowJSON['match'].keys():
		if noFirst:
			command = command + ","
		command = command + match + "=" + flowJSON['match'][match]
		noFirst = True
	command = command + ",actions="
	noFirst = False
	for action in flowJSON['action'].keys():
		if noFirst:
			command = command +","
		command = command + action + ":" + flowJSON['action'][action]
		noFirst = True
	subprocess.Popen(command, stdout=subprocess.PIPE, shell=True)

def deleteFlow(flowJSON, bridgeName):
	'''
	Deletes a flow on a bridge
	INPUT JSON:
	{
	match: {map of match key->value}
	}
	'''
	command = "ovs-ofctl del-flows " + bridgeName + " "
	noFirst = False
	for match in flowJSON['match'].keys():
		if noFirst:
			command = command + ","
		command = command + match + "=" + flowJSON['match'][match]
		noFirst = True
	subprocess.Popen(command, stdout=subprocess.PIPE, shell=True)

def findPort(bridgeName, portName):
	'''PUT http://192.168.1.1:8080/migration {"IP": "10.2.1.1", "psaIPaddresses": {"strongswan": "10.2.4.1"}, "vlanID": 1, "PSAs": [{"vcpu": "1", "interfaces": [{"bridge": "brData", "name": "tap3a628587-871"}, {"bridge": "brData", "name": "tapbd8bc573-a21"}, {"bridge": "brCtl", "vlan": 1, "name": "tap85238dee-62c"}], "disk": {"type": "qcow2", "location": "/var/lib/libvirt/images/c925f9c7-5ce8-46e1-8e41-e557f32c3be4.qcow2"}, "name": "c925f9c7-5ce8-46e1-8e41-e557f32c3be4", "memory": "1024"}], "pscName": "d9d32836-59d0-44b0-bd24-3a0f14d0d7e5", "token": "test2", "migration": "True", "psc": {"vcpu": "1", "interfaces": [{"bridge": "brCtl", "mac": "00:16:3e:28:8b:1e", "name": "tapf6226697-0a7"}, {"bridge": "brCtl", "vlan": 1, "name": "tap45bb27aa-e47"}, {"bridge": "brData", "name": "tap7797973e-79e"}], "disk": {"type": "qcow2", "location": "/var/lib/libvirt/images/d9d32836-59d0-44b0-bd24-3a0f14d0d7e5.qcow2"}, "name": "d9d32836-59d0-44b0-bd24-3a0f14d0d7e5", "memory": "512"}, "pscAddr": "192.168.1.101", "userInterface": "tap3b7fc834-93f", "generatedFlows": [{"priority": "10", "action": {"output": "tap7797973e-79e"}, "match": {"dl_type": "0x0806", "in_port": "tap3b7fc834-93f", "nw_dst": "10.2.2.251"}}, {"priority": "10", "action": {"output": "tap7797973e-79e"}, "match": {"dl_type": "0x0800", "in_port": "tap3b7fc834-93f", "nw_dst": "10.2.2.251"}}, {"action": {"output": "tap3b7fc834-93f"}, "match": {"in_port": "tap7797973e-79e"}}, {"action": {"output": "tap3a628587-871"}, "match": {"in_port": "tap3b7fc834-93f"}}, {"action": {"output": "tap3b7fc834-93f"}, "match": {"in_port": "tap3a628587-871"}}, {"action": {"output": "tapNAT"}, "match": {"in_port": "tapbd8bc573-a21"}}, {"priority": "10", "action": {"output": "tapbd8bc573-a21"}, "match": {"dl_type": "0x0806", "in_port": "tapNAT", "nw_dst": "10.2.3.1"}}, {"priority": "10", "action": {"output": "tapbd8bc573-a21"}, "match": {"dl_type": "0x0800", "in_port": "tapNAT", "nw_dst": "10.2.3.1"}}, {"priority": "10", "action": {"output": "tapbd8bc573-a21"}, "match": {"dl_type": "0x0806", "in_port": "tapNAT", "nw_dst": "10.2.4.1"}}, {"priority": "10", "action": {"output": "tapbd8bc573-a21"}, "match": {"dl_type": "0x0800", "in_port": "tapNAT", "nw_dst": "10.2.4.1"}}, {"priority": "10", "action": {"output": "tapbd8bc573-a21"}, "match": {"dl_type": "0x0806", "in_port": "tapNAT", "nw_dst": "10.2.1.1"}}, {"priority": "10", "action": {"output": "tapbd8bc573-a21"}, "match": {"dl_type": "0x0800", "in_port": "tapNAT", "nw_dst": "10.2.1.1"}}]}

	Find port number on a bridge
	'''
	proc = subprocess.Popen("ovs-ofctl show " + bridgeName +" | grep " + portName, stdout=subprocess.PIPE, shell=True)
	(out, err) = proc.communicate()
	return out.split("(").pop(0).split().pop(0)
