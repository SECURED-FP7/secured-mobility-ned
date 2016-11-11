Mobility
========

Introduction
=============

Scenario
--------
This readme describes the testbed setup for the mobility case scenario. If you want configure NED please check the [README.md](https://gitlab.secured-fp7.eu/secured/ned) in the SECURED/Ned branch master.

![Environment[fig:proto]](images/esquema_testned.png)

This test consists of two neds, each one on a different local network. The first ned is in the network 172.19.0.0/24 and the second ned is in network 172.18.0.0/24.The neds are interconnected by a third host that NAT to internet.

Usage scenario
--------------
  1. The client connects to secured1 wifi and obtains the IP assigned by the corresponding access point.
  2. The client starts the tunnel 'ned1' (ipsec up ned1).
  3. Initialize migration and wait few seconds (see the proces in test) work in progress...
  4. The client changes to the  secured2 wifi 
  5. The client starts the tunnel 'ned2' (ipsec down ned1 && ipsec up ned2).



Setup guide
===================

NAT Configuration
-------------------
We use the following script to configure iptables in "NAT":

  	#variable
  	IF_INTERNET=eth0
  	IF_LAN1=eth1
   	IF_LAN2=eth2
  	IP_PUBLICA = 147.83.42.250
  	NETWORK1 = 172.19.0.0/24
  	NETWORK2 = 172.18.0.0/24
  	#eth1 <-> eth0
  	iptables -t nat -A POSTROUTING -s $NETWORK1 -o $IF_INTERNET -j MASQUERADE
  	iptables -A FORWARD -i $IF_LAN1 -o $IF_INTERNET -j ACCEPT
  	iptables -A FORWARD -i $IF_INTERNET -o $IF_LAN1 -m state --state RELATED,ESTABLISHED -j ACCEPT
  	#eth2 <-> eth0
  	iptables -t nat -A POSTROUTING -s $NETWORK2 -o $IF_INTERNET -j MASQUERADE
  	iptables -A FORWARD -i $IF_LAN2 -o $IF_INTERNET -j ACCEPT
  	iptables -A FORWARD -i $IF_INTERNET -o $IF_LAN1 -m state --state RELATED,ESTABLISHED -j ACCEPT
  	
Test neds configuration
------------------

For configuration test ned 1 we use the following script to configure the static routes:

	# add ip route 172.18.0.0/24 via 172.19.0.1

For configuration test ned 2 we use the following script to configure the static routes:
	
	# add ip route 172.19.0.0/24 via 172.18.0.1
	
Strongswan
==========
We assume that the neds and client have the strongswan configurate. If not case please check the [README.md](https://gitlab.secured-fp7.eu/secured/ned) in the SECURED/Ned repository.

neds configuration:
--------------------
both neds same configuration:



Client configuration:
---------------------
Add connections to file ipsec.conf will connect with Neds. The base configuration is the same for all neds, but the connections that only changes:


	conn ned2 #tunnel toward test ned 2
        left=%any
        leftid=userterminal
        leftfirewall=yes
        leftsourceip=%config
        leftauth=eap-md5
        leftsubnet=0.0.0.0/0
        right=172.18.0.10
        rightid="C=CH, O=strongSwan, CN=ned"
        rightsubnet=0.0.0.0/0
        rightauth=pubkey
        auto=start

	conn ned1 #tunnel toward test ned 1
        left=%any
        leftid=userterminal
        leftfirewall=yes
        leftsourceip=%config
        leftauth=eap-md5
        leftsubnet=0.0.0.0/0
        right=172.19.0.10
        rightid="C=CH, O=strongSwan, CN=ned"
        rightsubnet=0.0.0.0/0
        rightauth=pubkey
        auto=start


Tests {working progress}
=====

We login with one of the following test profiles:

-   **test2:** tests has been used by this user

Both accounts have the following password: **test2**

 For execute migration we use following command for initialize migration:

	# curl -H "Accept: application/json" -H "Content-Type: application/json" -vX POST -d '{"user":"test2"}' http://10.2.2.253:8080/migration




