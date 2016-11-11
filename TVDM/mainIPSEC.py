'''
Created on 23/mag/2014

@author: rbonafiglia

Main script to launch from gunicorn to star the orchestrator WSGI server
'''
import falcon
import Config
from Orchestrator import Orchestrator
from GraphInstatiator import GraphInstantiator
from PSAcreation import PSAcreation
from GraphInfo import GraphInfo
from PSAConf import PSAConf
###migration code###
from TVDMigration import TVDMigration
###
from VerifierCache import VerifierCache
import logging
import datetime as dt
import signal
import sys

# TODO: control if there are sessions open, if true close them
class MyFormatter(logging.Formatter):
    converter=dt.datetime.fromtimestamp
    def formatTime(self, record, datefmt=None):
        ct = self.converter(record.created)
        if datefmt:
            s = ct.strftime(datefmt)
        else:
            t = ct.strftime("%Y-%m-%d %H:%M:%S")
            s = "%s,%03d" % (t, record.msecs)
        return s


conf = Config.Configuration()
#logging.config.fileConfig(conf.LOG_FILE)
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

fh = logging.FileHandler(conf.LOG_FILE)
fh.setLevel(logging.DEBUG)

console = logging.StreamHandler()

formatter = MyFormatter(fmt='%(asctime)s %(message)s',datefmt='%Y-%m-%d,%H:%M:%S.%f')
fh.setFormatter(formatter)
console.setFormatter(formatter)

logger.addHandler(console)
logger.addHandler(fh)
#logging.basicConfig(filename=conf.LOG_FILE,level=logging.DEBUG,format='%(asctime)s %(message)s', datefmt='%m/%d/%Y %I:%M:%S %p')
logger.info("--------")
logger.info("NED / TVDM init.")
logger.info("NED / TVDM VERSION: " + str(conf.TVDM_VERSION)) 
logger.info("--------")
# Falcon starts

app = falcon.API()
instantiator = GraphInstantiator(conf, logger, True)
###start migration code###
migration = TVDMigration(instantiator, conf, logger)
###end migration code###
def signal_term_handler(signal, frame):
	logger.info("SIG TERM")
	if instantiator.signal_term_handler():
		logger.info("FINISH DESTROY ALL TVD")
        	sys.exit(0)

signal.signal(signal.SIGTERM, signal_term_handler)
###migration code -> added parameter migration###
orch = Orchestrator(instantiator, migration)
###

### Verifier cache
vc = VerifierCache(conf)
vc.start()
app.add_route('/verify', vc)

app.add_route('/instantiateTVD', orch)
###migration code -> added new call###
app.add_route('/migration', orch)
###
psa = PSAcreation(instantiator)
app.add_route('/createPSA', psa)

graph = GraphInfo(instantiator,conf.USER_GRAPH_LOCATION, conf)
app.add_route('/getGraph', graph)

psaConfRes = PSAConf(conf.PSA_CONF_LOCATION, logger, conf, instantiator)
app.add_route('/getConf/{psa_id}/{conf_id}', psaConfRes)




