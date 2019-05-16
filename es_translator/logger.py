import logging
from logging.handlers import SysLogHandler

logger = logging.getLogger('es-translator')
logger.setLevel(logging.DEBUG)

sysLogFormatter = logging.Formatter('%(asctime)s :: %(name)s :: %(levelname)s :: %(message)s')
sysLogHandler = SysLogHandler()
sysLogHandler.setLevel(logging.DEBUG)
sysLogHandler.setFormatter(sysLogFormatter)

logger.addHandler(sysLogHandler)
