import ConfigParser
import os
import copy
import ast

class Configuration(object):
    _instance = None
    # (fmignini) Not too meaningful use this var, I should change his name with something else like inizialized = False
    _AUTH_SERVER = None

    def __new__(cls, *args, **kwargs):

        if not cls._instance:
            cls._instance = super(Configuration, cls).__new__(
                cls, *args, **kwargs)
        return cls._instance

    def __init__(self):
        # print 'Configuration - PATH : '+os.getcwd()
        path = copy.copy(os.getcwd())
        path_dirs = path.split("/")
        for path_dir in path_dirs:
            if path_dir == 'tests':
                self.test = True
            else:
                self.test = False
        # print self.test
        if self._AUTH_SERVER is None:
            self.inizialize()

    def inizialize(self):
        """
        Initialised variables from the tvdm.conf configuration file
        """
        self.config = ConfigParser.RawConfigParser()
        self.config.read('tvdm.conf')
        self._LOG_FILE = 'Orchestrator.log'
        self._VERBOSE = 'true'
        self._DEBUG = 'true'
        self._USER_GRAPH_LOCATION = self.config.get('configuration', 'user_graph_location')
        self._ACCESS_INTERFACE = self.config.get('configuration', 'access_interface')
        self._EXIT_INTERFACE = self.config.get('configuration', 'exit_interface')
        self._VM_IMAGES_LOCATION = self.config.get('configuration', 'vm_images_location')
        self._INSTANTIATED_VM_LOCATION = self.config.get('configuration', 'instantiated_vm_location')
        self._SCRIPT_LOCATION = self.config.get('configuration', 'script_location')
        self._PSA_CONF_LOCATION = self.config.get('configuration', 'psa_conf_location')
        self._PSA_MANI_LOCATION = self.config.get('configuration', 'psa_manifest_location')
        self._PSC_DP_IF_IP = self.config.get('configuration', 'psc_dataplane_interface_ip')
        self._TVDM_VERSION = self.config.get('configuration', 'tvdm_version')
        self._GATEWAY_IP = self.config.get('configuration', 'gateway_ip')
        self._DNS_IP = self.config.get('configuration', 'dns_ip')
        self._NETMASK = self.config.get('configuration', 'netmask')
        self._UPR_LOCATION = self.config.get('configuration', 'upr_location')
        self._PSAR_LOCATION = self.config.get('configuration', 'psar_location')
        self._SPM_LOCATION = self.config.get('configuration', 'spm_location')
        self._NED_ID = self.config.get('configuration', 'ned_id')
        self._USE_LOCAL_FILE = self.config.getboolean('configuration', 'use_local_file')
        self._MANAGING_NETWORK_ADDRESS = self.config.get('configuration', 'managing_network_address')
        self._PSA_NETWORK_ADDRESS = self.config.get('configuration', 'psa_network_address')
        self._USER_NETWORK_ADDRESS = self.config.get('configuration', 'user_network_address')
        self._USER_INTERFACE_NETWORK_ADDRESS = self.config.get('configuration', 'user_interface_network_address')

        self._VERIFIER_URL = self.config.get('configuration', 'verifier_url')
        ###start migration code###
        self._DEFAULT_NAME_SPACE = self.config.get('configuration', 'default_name_space')
        self._PSA_IP_ROUTE_TABLE = self.config.get('migration', 'psa_ip_route_table')
        self._MOBILITY = self.config.getboolean('migration', 'mobility')
        self._IP_EXT = self.config.get('migration', 'ip_ext')
        self._DEFAULT_SSID = self.config.get('migration', 'default_ssid')

    def migration_ned_info(self, ssid):
        return self.config.get('migration', str(ssid))

        ###end migration code###
    @property
    def MANAGING_NETWORK_ADDRESS(self):
        """
        Name of the file where to log
        """
        return self._MANAGING_NETWORK_ADDRESS

    @property
    def PSA_NETWORK_ADDRESS(self):
        """
        Network mask of the network used by the PSA for the datapath
        """
        return self._PSA_NETWORK_ADDRESS

    @property
    def USER_NETWORK_ADDRESS(self):
        """
        Network address of the local IP given to the user by the IPSec connection
        """
        return self._USER_NETWORK_ADDRESS

    @property
    def USER_INTERFACE_NETWORK_ADDRESS(self):
        """
        Network address for the interface used as IPSec terminator for each user
        """
        return self._USER_INTERFACE_NETWORK_ADDRESS

    @property
    def PSC_DP_IF_IP(self):
        """
        IP of the PSC for the comunication with the user
        """
        return self._PSC_DP_IF_IP

    @property
    def NETMASK(self):
        """
        Network mask for the PSA addressing
        """
        return self._NETMASK

    @property
    def USER_GRAPH_LOCATION(self):
        """
        Directory of the application graph of the user in case of local files and not UPR
        """
        return self._USER_GRAPH_LOCATION

    @property
    def SCRIPT_LOCATION(self):
        """
        Directory of the initialisation script
        """
        return self._SCRIPT_LOCATION

    @property
    def PSA_CONF_LOCATION(self):
        """
        Directory of the configuration of the PSA in case of using local files and not the UPR
        """
        return self._PSA_CONF_LOCATION

    @property
    def PSA_MANI_LOCATION(self):
        """
        Directory of the manifest of the PSA in case of using local files and not the PSAR
        """
        return self._PSA_MANI_LOCATION

    @property
    def ACCESS_INTERFACE(self):
        """
        The network interface from where the user traffic came in (usually an IPSec terminator)
        """
        return self._ACCESS_INTERFACE

    @property
    def EXIT_INTERFACE(self):
        """
        Network interface where the user traffic should exit (it should be the one connected to the internet)
        """
        return self._EXIT_INTERFACE

    @property
    def VM_IMAGES_LOCATION(self):
        """
        Directory of the base images of the virtual machine (in case of the PSAR will be cached the downloaded images)
        """
        return self._VM_IMAGES_LOCATION

    @property
    def INSTANTIATED_VM_LOCATION(self):
        """
        Directory where the TVDM suould store the disk of the instantiated virtual machine
        """
        return self._INSTANTIATED_VM_LOCATION

    @property
    def LOG_FILE(self):
        return self._LOG_FILE

    @property
    def TVDM_VERSION(self):
        """
        Version of the TVDM
        """
        return self._TVDM_VERSION

    @property
    def GATEWAY_IP(self):
        """
        IP address of the gateway that the PSA should use for access the internet
        """
        return self._GATEWAY_IP

    @property
    def DNS_IP(self):
        """
        IP of the DNS used by the PSA
        """
        return self._DNS_IP

    @property
    def VERBOSE(self):
        """
        Flag to indicates if the output needs to be verbose
        """
        return self._VERBOSE

    @property
    def DEBUG(self):
        """
        flag used to define if it is on debug mode
        """
        return self._DEBUG

    @property
    def UPR_LOCATION(self):
        """
        IP address of the UPR service
        """
        return self._UPR_LOCATION

    @property
    def PSAR_LOCATION(self):
        """
        Address of the PSAR service
        """
        return self._PSAR_LOCATION

    @property
    def USE_LOCAL_FILE(self):
        """
        Flag that indicates if local files will be used instead of remote UPR and PSAR services
        """
        return self._USE_LOCAL_FILE

    @property
    def SPM_LOCATION(self):
        """
        Address of the SECURED SPM service used for the reconciliation process
        """
        return self._SPM_LOCATION

    @property
    def NED_ID(self):
        return self._NED_ID

    ###start migration code###
    @property
    def DEFAULT_NAME_SPACE(self):
        """
        default name space
        """
        return self._DEFAULT_NAME_SPACE

    @property
    def PSA_IP_ROUTE_TABLE(self):
        return self._PSA_IP_ROUTE_TABLE

    @property
    def DEFAULT_SSID(self):
        return self._DEFAULT_SSID

    @property
    def IP_EXT(self):
        return self._IP_EXT

    @property
    def MOBILITY(self):
        return self._MOBILITY

###end migration code###

    def VERIFIER_URL(self):
        return self._VERIFIER_URL

    ###end migration code###





