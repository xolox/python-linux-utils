# linux-utils: Linux system administration tools for Python.
#
# Author: Peter Odding <peter@peterodding.com>
# Last Change: July 3, 2018
# URL: https://linux-utils.readthedocs.io

"""
Command line interface for :mod:`linux_utils.luks`.

The :mod:`linux_utils.cli` module implements command line interfaces for the
:func:`.cryptdisks_start()` and :func:`.cryptdisks_stop()` functions.
"""

# Standard library modules.
import logging
import sys

# External dependencies.
import coloredlogs
from humanfriendly.terminal import usage, warning
from humanfriendly.text import dedent

# Modules included in our package.
from linux_utils.luks import cryptdisks_start, cryptdisks_stop

# Public identifiers that require documentation.
__all__ = (
    'cryptdisks_start_cli',
    'cryptdisks_stop_cli',
    'logger',
)

# Initialize a logger for this module.
logger = logging.getLogger(__name__)


def cryptdisks_start_cli():
    """
    Usage: cryptdisks-start-fallback NAME

    Reads /etc/crypttab and unlocks the encrypted filesystem with the given NAME.

    This program emulates the functionality of Debian's cryptdisks_start program,
    but it only supports LUKS encryption and a small subset of the available
    encryption options.
    """
    # Enable logging to the terminal and system log.
    coloredlogs.install(syslog=True)
    # Get the name of the encrypted filesystem from the command line arguments
    # and show a simple usage message when no name is given as an argument.
    try:
        target = sys.argv[1]
    except IndexError:
        usage(dedent(cryptdisks_start_cli.__doc__))
    else:
        # Call our Python implementation of `cryptdisks_start'.
        try:
            cryptdisks_start(target)
        except ValueError as e:
            # cryptdisks_start() raises ValueError when the given target isn't
            # listed in /etc/crypttab. This doesn't deserve a traceback on the
            # terminal.
            warning("Error: %s", e)
            sys.exit(1)
        except Exception:
            # Any other exceptions are logged to the terminal and system log.
            logger.exception("Aborting due to exception!")
            sys.exit(1)


def cryptdisks_stop_cli():
    """
    Usage: cryptdisks-stop-fallback NAME

    Reads /etc/crypttab and locks the encrypted filesystem with the given NAME.

    This program emulates the functionality of Debian's cryptdisks_stop program,
    but it only supports LUKS encryption and a small subset of the available
    encryption options.
    """
    # Enable logging to the terminal and system log.
    coloredlogs.install(syslog=True)
    # Get the name of the encrypted filesystem from the command line arguments
    # and show a simple usage message when no name is given as an argument.
    try:
        target = sys.argv[1]
    except IndexError:
        usage(dedent(cryptdisks_stop_cli.__doc__))
    else:
        # Call our Python implementation of `cryptdisks_stop'.
        try:
            cryptdisks_stop(target)
        except ValueError as e:
            # cryptdisks_stop() raises ValueError when the given target isn't
            # listed in /etc/crypttab. This doesn't deserve a traceback on the
            # terminal.
            warning("Error: %s", e)
            sys.exit(1)
        except Exception:
            # Any other exceptions are logged to the terminal and system log.
            logger.exception("Aborting due to exception!")
            sys.exit(1)
