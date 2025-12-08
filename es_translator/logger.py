"""Logging configuration for es-translator.

This module provides logging setup utilities for the es-translator application,
including syslog and stdout handlers with colored output.
"""

import logging
import sys
from logging.handlers import SysLogHandler
from syslog import LOG_LOCAL7

import coloredlogs

logger = logging.getLogger('es-translator')
logger.setLevel(logging.INFO)


def default_log_formatter() -> logging.Formatter:
    """Create the default log formatter.

    Returns:
        Formatter with timestamp, name, level, and message.
    """
    return logging.Formatter('%(asctime)s :: %(name)s :: %(levelname)s :: %(message)s')


def add_syslog_handler(address: str = 'localhost', port: int = 514, facility: int = LOG_LOCAL7) -> None:
    """Add a syslog handler to the logger.

    Args:
        address: Syslog server address.
        port: Syslog server port.
        facility: Syslog facility code.
    """
    syslog_formatter = default_log_formatter()
    syslog_handler = SysLogHandler(address=(address, port), facility=facility)
    syslog_handler.setLevel(logging.INFO)
    syslog_handler.setFormatter(syslog_formatter)
    logger.addHandler(syslog_handler)


def add_stdout_handler(level: int = logging.ERROR) -> None:
    """Add a colored stdout handler to the logger.

    Args:
        level: Minimum log level to display.
    """
    fmt = '%(levelname)s %(message)s'
    logger.addHandler(logging.StreamHandler(sys.stdout))
    coloredlogs.install(level=level, logger=logger, fmt=fmt)
