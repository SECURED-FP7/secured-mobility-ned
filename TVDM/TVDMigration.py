import ast
import datetime
import json
import libvirt
import requests
import socket
import subprocess
import threading
import time
from threading import Event
from threading import Thread
import paramiko

from libvirtManager import ComputeManager


class TVDMigration(object):
    '''
       Class used to migrate user's TVD and VMs
    '''

    def __init__(self, instantiator, configure, logger):
        self.user = None
        self.userTVDs = instantiator.userTVDs  # All the generated TVD
        self.remote_conn_string = ""
        self.local_conn_string = ""
        self.conn = ""
        self.remote_conn = ""

        self.default_ssid = configure.DEFAULT_SSID
        self.local_info = configure.migration_ned_info(self.default_ssid)
        if type(self.local_info) is str:
            self.local_info = ast.literal_eval(self.local_info)
        self.local_host = self.local_info['ned_ip']
        self.local_port = int(self.local_info['ned_port'])

        self.config = configure
        self.computeManager = ComputeManager(configure)
        self.__last_bytes = -1
        self.__last_time = datetime.time()
        self.logger = logger
        self.PSAList = {}
        self.TVD = {}
        self.namePSC = None
        self.instantiator = instantiator
        self.TokenIP = instantiator.TokenIP
        self.ssh = None
        self.PSC = None
        self.disk_base = None
        self.local_conn_string = "qemu:///system"
        self.conn = libvirt.open(self.local_conn_string)
        self.local_dom = None

    def init_migration(self, e, he, session):
        '''
        Inicialitzation class and call migration functions
        '''

        self.logger.info("ssid " + session['ssid'])
        self.logger.info("token " + str(session['token']))

        self.remote_info = self.config.migration_ned_info(session['ssid'])
        if type(self.remote_info) is str:
            self.remote_info = ast.literal_eval(self.remote_info)
        self.remote_host = self.remote_info['ned_ip']
        self.remote_port = int(self.remote_info['ned_port'])
        self.logger.info("remote host %s:%s" % (self.remote_host, self.remote_port))
        self.PSAList = self.userTVDs[session['token']].psaList
        self.user = self.userTVDs[session['token']].userName
        self.namePSC = self.userTVDs[session['token']].psc['name']
        self.PSC = self.instantiator.userTVDs[session['token']].psc
        try:
            self.ssh = self.createSSHClient(self.remote_host, self.remote_port, 'root', 'secured')
        except:
            self.logger.info("Error to generate ssh")
        i = Event()
        self.TsendTVD = Thread(target=self.sendTVD, kwargs={"session": session})
        Migration = Thread(target=self.migration, args=(i, he, ))
        Migration.start()
        i.wait()
        e.set()
        Migration.join()
        self.logger.info("Migration FINISHED. Deleting remaining user data... ")

        #self.instantiator.networkManager.deletePort('brData', self.instantiator.userTVDs[session['token']].userInterface)
        #userTVD = self.instantiator.userTVDs[session['token']]
        #self.instantiator.mobility_iprules(session, "del", session[token])

        self.logger.info("calling instantiator.deleteUser with session: \n%s" % (json.dumps(session, indent=4, sort_keys=True)))
        self.instantiator.deleteUser(session, migration=True)
        self.logger.info("\n\nUSER DELETED... SHOULD BE CLEAN... \n")

        #del self.instantiator.IPandUser[session['IP']]
        #del self.instantiator.TokenIP[userTVD.pscAddr]
        #del self.instantiator.userTVDs[session['token']]

    def sendTVD(self, session):
        '''
        Obtain user's TVD and migrate this
        '''

        self.TVD['token'] = self.instantiator.userTVDs[session['token']].userName
        self.TVD['IP'] = session['IP']
        self.TVD['userInterface'] = self.instantiator.userTVDs[session['token']].userInterface
        self.instantiator.logger.info("userIsessionnterface " + str(self.TVD['userInterface']))
        self.TVD['vlanID'] = self.instantiator.userTVDs[session['token']].vlanID
        self.TVD['pscAddr'] = self.instantiator.userTVDs[session['token']].pscAddr
        self.TVD['psc'] = self.instantiator.userTVDs[session['token']].psc
        self.TVD['pscName'] = self.instantiator.userTVDs[session['token']].psc['name']
        self.TVD['generatedFlows'] = self.instantiator.userTVDs[session['token']].generatedFlows
        self.TVD['PSAs'] = self.instantiator.userTVDs[session['token']].psaList
        self.TVD['psaIPaddresses'] = self.instantiator.userTVDs[session['token']].psaIPaddresses
        self.TVD['migration'] = "True"

        try:
            TVD = json.dumps(self.TVD)
            self.logger.info("TVD: " + str(TVD))
        except:
            self.logger.info("Error to created TVD json")

        try:
            cmd = "ip netns exec orchNet curl -X PUT --header Accept: application/json --header Content-Type: application/json -d '" + TVD + "' http://192.168.1.1:8080/migration"
            (results, errors) = self.execute_command(self.ssh, cmd, False)
        except:
            self.logger.info(errors)

    def migration(self, i, he):
        '''
        Prepare PSC and PSAs migration
        '''
        '''
        PSAs migration
        '''
        tpsas = []
        for psa in self.PSAList:
            self.original = self.obtain_disk_base(psa['disk']['location'])
            self.generate_remote_disk(self.original, psa['disk']['type'], psa['disk']['location'], psa['name'])
            tpsa = TMigration(vm=psa['name'], sleep=0,
                              local_host=self.local_host,
                              remote_host=self.remote_host,
                              remote_port=self.remote_port,
                              logger=self.logger)
            tpsa.start()
            tpsas.append(tpsa)

        while 1:
            avgr = 0
            for tpsa in tpsas:
                remaining = tpsa.vm_status()
                if remaining[0] > 0:
                    avgr += remaining[0]
            if len(tpsas) > 0:
                if avgr / len(tpsas) >= 80:
                    i.set()
                    self.logger.info("---> PSAs migrated [event: %s]" % (str(i.isSet())))
                    break

        self.logger.info("---> waiting for handover ack to the PSC [event: %s]" % (str(i.isSet())))
        he.wait()  # wait for the handover answer to the PSC
        '''
        PSC migration
        '''
        self.original_psc = (self.obtain_disk_base(self.PSC['disk']['location']))
        self.generate_remote_disk(self.original_psc, self.PSC['disk']['type'], self.PSC['disk']['location'], self.namePSC)
        tMigration = TMigration(vm=self.namePSC,
                                sleep=2,
                                local_host=self.local_host,
                                remote_host=self.remote_host,
                                remote_port=self.remote_port,
                                logger=self.logger)
        tMigration.start()

        '''
        TVD migration
        '''
        try:
            nat = self.remote_info['nat']
            headers = {'Content-Type': 'application/json', 'Accept': 'application/json'}
            payload = {'route': nat['route']}
            url = "http://%s:%s/switch" % (str(nat['server'][0]), str(nat['server'][1]))
            self.logger.info("NAT Request URL: %s" % url)
            r = requests.post(url, json=payload, headers=headers)
            self.logger.info("NAT request Response: %s" % str(r.status_code))
        except Exception as e:
            self.logger.error("NAT request error\n%s" % (str(e)))

        time.sleep(1)

        self.TsendTVD.start()  # pass TVD, after init PSC migration

        while 1:
            if tMigration.executed:
                break
        remaining = tMigration.vm_status()
        while remaining:
            if not remaining:
                self.logger.info("No migration in progress")
            else:
                self.logger.info("remaining to migrate %s, psa: %s " % (str(remaining), str(tMigration.vm)))
            time.sleep(1)
            remaining = tMigration.vm_status()
            if remaining[0] >= 80:
                # subprocess.check_call()
                break

        for tpsa in tpsas:
            tpsa.join()
        self.TsendTVD.join()
        tMigration.join()

        for psa in self.PSAList:
            self.undefined_vm(psa['name'])

        self.undefined_vm(self.namePSC)
        self.logger.info("PSC migrated")


    def undefined_vm(self, vm):
        self.local_dom = self.conn.lookupByName(vm)
        self.local_dom.undefine()


    def obtain_disk_base(self, path):
        '''
        obtain path VM disk base
        '''
        try:
            proc = subprocess.Popen("qemu-img info " + path, stdout=subprocess.PIPE, shell=True)
            (out, err) = proc.communicate()
            returnedValue = str(out)
            start = 'file: '
            end = '\n'
            disk_base = ((returnedValue.split(start))[1].split(end)[0])

        except subprocess.CalledProcessError as e:
            self.logger.info("Calledprocerr:" + e)

        return disk_base

    def generate_remote_disk(self, original, disk_type, path, vm):
        """
        Generate remote disk
        """
        stderr = ""

        try:
            cmd = "[  -f " + path + "/" + vm + " ] || qemu-img create -b " + original + " -f " + disk_type + " " + path
            stdin, stdout, stderr = self.ssh.exec_command(cmd)
            stdin.close()
        except Exception as e:
            self.logger.info("Error to create remote disk " + str(e) + " " + str(stderr))

    def rename_remote_disk(self, path, vm):

        stderr = ""

        try:
            cmd = "mv " + path + "/" + vm + " " + path + "/" + vm + "backup"
            stdin, stdout, stderr = self.ssh.exec_command(cmd)
            stdin.close()

        except Exception as e:
            self.logger.info("Error to create remote disk " + str(e) + " " + str(stderr))


    def createSSHClient(self, server, port, user, password):

        client = paramiko.SSHClient()
        client.load_system_host_keys()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(server, port, user, password)
        return client

    def execute_command(self, ssh, cmd, sudo):
        '''
        Create remote conection
        '''
        try:
            if sudo:
                cmd = "sudo -S -u qemu '' %s" % cmd
            stdin, stdout, stderr = ssh.exec_command(cmd)
            if sudo:
                stdin.write('xxx\n')
            stdin.write('x\n')
            stdin.flush()

        except socket.timeout as serr:
            self.logger.info("Error1: %s" % serr)

        except socket.error as serr:
            print "Error2: %s" % serr

        except:
            print "ANY1"
        return (stdout.readlines(), stderr.readlines())


class TMigration(threading.Thread):
    def __init__(self, vm, sleep, local_host, remote_host, remote_port, logger, group=None, target=None, name=None,
                 args=(),
                 kwargs=None, verbose=None):
        super(TMigration, self).__init__(group=group, target=target, name=name, verbose=verbose)
        self.vm = vm
        self.sleep = sleep
        self.local_host = local_host
        self.remote_host = remote_host
        self.remote_port = remote_port
        self.logger = logger
        self.local_conn_string = "qemu:///system"
        __last_bytes = -1
        __last_time = datetime.time()

        try:
            self.remote_conn_string = "qemu+ssh://" + self.remote_host + ":" + str(self.remote_port) + "/system"
        except:
            self.logger.info("Error Connecting remote VM " + self.remote_host)

        try:
            self.conn = libvirt.open(self.local_conn_string)
        except:
            self.logger.info("Error Connecting to VM hypervisor " + self.local_conn_string)
        try:
            self.remote_conn = libvirt.open(self.remote_conn_string)
        except:
            self.logger.info("Error connecting to remote hypervisor: " + self.remote_conn_string)

        if (self.sleep > 0): self.logger.info(time.sleep(self.sleep))

        self.logger.info(
            "Starting migration of VM domain '" + self.vm + "' from " + self.local_host + " to " + self.remote_host + "...")
        try:
            self.local_dom = self.conn.lookupByName(self.vm)
        except:
            self.logger.info("VM does not exist: " + self.vm)
        self.executed = False
        return

    def run(self):

        try:
            self.logger.info("RUN DE TMIGRATION")
            self.local_dom.migrate(self.remote_conn, libvirt.VIR_MIGRATE_LIVE | libvirt.VIR_MIGRATE_COMPRESSED, None,
                                   None, 0)
            self.logger.info(
                "Migration of VM domain '" + self.vm + "' from " + self.local_host + " to " + self.remote_host + "triggered OK!!")
            self.executed = True
        except Exception as e:
            self.logger.info("Error to migrate " + self.vm)
            self.logger.error(str(e))

        try:
            remaining = self.vm_status()
            while remaining[0] != 100:
                if not remaining:
                    self.logger.info("No migration in progress")
                else:
                    self.logger.info("tmigration remaining to migrate %, psa: " % (str(remaining), str(self.vm)))
                time.sleep(1)
                remaining = self.vm_status()
        except Exception as e:
            self.logger.info("Error GETTING STATUS " + self.vm)
            self.logger.error(str(e))
        return

    def vm_job_stats(self):
        if self.local_dom.info()[0] != 5:
            return self.local_dom.jobStats()
        else:
            return {}

    def __update_migration_status(self):
        dictionary = self.vm_job_stats()
        if dict:
            if not 'data_remaining' in dictionary:  # No migration in progress
                if self.executed:
                    return [100]
                return [-1]
            remaining_bytes = dictionary['data_remaining']
            total_bytes = dictionary['data_total']
            if total_bytes == 0:
                if self.executed:
                    return [100]
                return [-1]
            if self.__last_bytes < 0:
                self.__last_bytes = remaining_bytes
                self.__last_time = datetime.datetime.now();
                eta = datetime.timedelta()
            elif remaining_bytes == 0:
                self.__last_bytes = 0
                self.__last_time = datetime.datetime.time();
            else:
                byte_rate = self.__last_bytes - remaining_bytes
                time_now = datetime.datetime.now()
                # time_now=datetime.timedelta(hours=datetime_now.hour, minutes=datetime_now.minute, seconds=datetime_now.second, microseconds=datetime_now.microseconds)
                time_between_queries = time_now - self.__last_time
                eta_microsec = self.timedelta2microseconds(time_between_queries) * int(remaining_bytes / byte_rate)
                eta = self.microseconds2timedelta(eta_microsec)
                self.__last_time = time_now
                self.__last_bytes = remaining_bytes
            percent_done = remaining_bytes / total_bytes * 100
            return [percent_done, eta.days, eta.seconds, eta.microseconds]
        else:
            if self.executed:
                return [100]
            return [-1]

    def vm_status(self):
        try:
            if not self.executed:
                return [-1]
            return self.__update_migration_status()
        except Exception as e:
            self.logger.info("vm_status vm not found %s" % (str(e.message)))
            return [100]

    def timedelta2microseconds(self, time):
        if not time:
            return -1
        return (((24 * 60 * 60 * time.days) + time.seconds)) * 10 ** 6 + time.microseconds

    def time2microseconds(self, time):
        if not time:
            return -1
        return (((60 * time.hours) + time.minutes) * 60 + time.seconds) * 1000000 + time.microseconds

    def microseconds2timedelta(self, pass_microseconds):
        given_microseconds = int(pass_microseconds)
        microseconds = given_microseconds % (10 ** 6)
        rest = int(given_microseconds / 10 ** 6)
        seconds = int(rest % (60 * 60 * 24))
        days = int(rest / (60 * 60 * 24))
        return datetime.timedelta(days=days, seconds=seconds, microseconds=microseconds)

    def microseconds2time(self, given_microseconds):
        microseconds = given_microseconds % (10 ** 6)
        rest = int(given_microseconds / 10 ** 6)
        seconds = int(rest % 60)
        rest = int(rest / 60)
        minutes = int(rest % 60)
        rest = int(rest / 60)
        hours = int(rest % 60)
        return datetime.time(hours=hours, minutes=minutes, seconds=seconds, microseconds=microseconds)
