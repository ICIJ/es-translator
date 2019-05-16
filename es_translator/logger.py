import logging
from logging.handlers import SysLogHandler

logger = logging.getLogger('es-translator')
logger.setLevel(logging.DEBUG)

def add_sysload_handler(address = 'localhost', port = 514, facility = 'local7'):
    sysLogFormatter = logging.Formatter('%(asctime)s :: %(name)s :: %(levelname)s :: %(message)s')
    sysLogHandler = SysLogHandler(address = (address, port), facility = facility)
    sysLogHandler.setLevel(logging.DEBUG)
    sysLogHandler.setFormatter(sysLogFormatter)
    logger.addHandler(sysLogHandler)
