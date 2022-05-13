import logging
import sys
from syslog import LOG_LOCAL7

import coloredlogs
from logging.handlers import SysLogHandler

logger = logging.getLogger('es-translator')
logger.setLevel(logging.INFO)

def default_log_formatter() -> logging.Formatter:
    return logging.Formatter('%(asctime)s :: %(name)s :: %(levelname)s :: %(message)s')


def add_syslog_handler(address: str = 'localhost', port: int = 514, facility: int = LOG_LOCAL7) -> None:
    sysLogFormatter = default_log_formatter()
    sysLogHandler = SysLogHandler(address = (address, port), facility = facility)
    sysLogHandler.setLevel(logging.INFO)
    sysLogHandler.setFormatter(sysLogFormatter)
    logger.addHandler(sysLogHandler)


def add_stdout_handler(level: int = logging.ERROR) -> None:
    fmt = '%(levelname)s %(message)s'
    logger.addHandler(logging.StreamHandler(sys.stdout))
    coloredlogs.install(level=level, logger=logger, fmt=fmt)
