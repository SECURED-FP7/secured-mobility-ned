import falcon
import logging
from  switch import Switch
import datetime as dt


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



logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

fh = logging.FileHandler("switch.log")
fh.setLevel(logging.DEBUG)

console = logging.StreamHandler()

formatter = MyFormatter(fmt='%(asctime)s %(message)s',datefmt='%Y-%m-%d,%H:%M:%S.%f')
fh.setFormatter(formatter)
console.setFormatter(formatter)

logger.addHandler(console)
logger.addHandler(fh)

logger.info("--------")
logger.info("NED / TVDM init.")
logger.info("NED / TVDM VERSION: ")
logger.info("--------")
# Falcon starts
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

app = falcon.API()
sw = Switch(logger)
app.add_route('/switch', sw)


