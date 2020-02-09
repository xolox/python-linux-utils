# linux-utils: Linux system administration tools for Python.
#
# Author: Peter Odding <peter@peterodding.com>
# Last Change: February 9, 2020
# URL: https://linux-utils.readthedocs.io

"""
Python API for Linux networking tools.

The functions in this module make it possible to inspect the current network
configuration of a Linux system, which can provide hints about the physical
location of the system.
"""

# Standard library modules.
import logging

# Modules included in our package.
from linux_utils import coerce_context

# Public identifiers that require documentation.
__all__ = (
    'determine_network_location',
    'find_gateway_ip',
    'find_gateway_mac',
    'find_mac_address',
    'have_internet_connection',
    'logger',
)

# Initialize a logger for this module.
logger = logging.getLogger(__name__)


def determine_network_location(context=None, **gateways):
    """
    Determine the physical location of the current system.

    This works by matching the MAC address of the current gateway against a set
    of known MAC addresses, which provides a simple but robust way to identify
    the current network. Because networks tend to have a physical location,
    identifying the current network tells us our physical location.

    :param gateways: One or more keyword arguments with lists of strings
                     containing MAC addresses of known networks.
    :param context: See :func:`.coerce_context()` for details.
    :returns: The name of the matched MAC address (a string) or :data:`None`
              when the MAC address of the current gateway is unknown.

    Here's an example involving two networks and a physical location with
    multiple gateways:

    .. code-block:: python

       >>> determine_network_location(
       ...    home=['84:9C:A6:76:23:8E'],
       ...    office=['00:15:C5:5F:92:79', 'B6:25:B2:19:28:61'],
       ... )
       'home'

    This is used to tweak my desktop environment based on the physical location
    of my laptop, for example at home my external monitor is to the right of my
    laptop whereas at work it's the other way around, so the :man:`xrandr`
    commands to be run differ between the two locations.
    """
    context = coerce_context(context)
    current_gateway_mac = find_gateway_mac(context)
    if current_gateway_mac:
        for network_name, known_gateways in gateways.items():
            if any(current_gateway_mac.upper() == gateway.upper() for gateway in known_gateways):
                logger.info("%s is connected to the %s network.", context, network_name)
                return network_name
        logger.info(
            "%s isn't connected to a known network (unknown gateway MAC address %s).", context, current_gateway_mac
        )
    else:
        logger.info("Failed to determine gateway of %s, assuming network connection is down.", context)


def find_gateway_ip(context=None):
    """
    Find the IP address of the current gateway using the ``ip route show`` command.

    :param context: See :func:`.coerce_context()` for details.
    :returns: The IP address of the gateway (a string) or :data:`None`.
    """
    context = coerce_context(context)
    logger.debug("Looking for IP address of current gateway ..")
    for line in context.capture("ip", "route", "show").splitlines():
        tokens = line.split()
        logger.debug("Parsing 'ip route show' output: %s", tokens)
        if len(tokens) >= 3 and tokens[:2] == ["default", "via"]:
            ip_address = tokens[2]
            logger.debug("Found gateway IP address: %s", ip_address)
            return ip_address
    logger.debug("Couldn't find IP address of gateway in 'ip route show' output!")


def find_gateway_mac(context=None):
    """
    Find the MAC address of the current gateway using :func:`find_gateway_ip()` and :func:`find_mac_address()`.

    :param context: See :func:`.coerce_context()` for details.
    :returns: The MAC address of the gateway (a string) or :data:`None`.
    """
    context = coerce_context(context)
    ip_address = find_gateway_ip(context)
    if ip_address:
        mac_address = find_mac_address(ip_address, context)
        if mac_address:
            logger.debug("Found gateway MAC address: %s", mac_address)
            return mac_address
    logger.debug("Couldn't find MAC address of gateway in 'arp -n' output!")


def find_mac_address(ip_address, context=None):
    """
    Determine the MAC address of an IP address using the ``arp -n`` command.

    :param ip_address: The IP address we're interested in (a string).
    :param context: See :func:`.coerce_context()` for details.
    :returns: The MAC address of the IP address (a string) or :data:`None`.
    """
    context = coerce_context(context)
    logger.debug("Looking for MAC address of %s ..", ip_address)
    for line in context.capture("arp", "-n").splitlines():
        tokens = line.split()
        logger.debug("Parsing 'arp -n' output: %s", tokens)
        if len(tokens) >= 3 and tokens[0] == ip_address:
            mac_address = tokens[2]
            logger.debug("Found MAC address of %s: %s", ip_address, mac_address)
            return mac_address
    logger.debug("Couldn't find MAC address in 'arp -n' output!")


def have_internet_connection(endpoint="8.8.8.8", context=None):
    """
    Check if an internet connection is available using :man:`ping`.

    :param endpoint: The public IP address to :man:`ping` (a string).
    :param context: See :func:`.coerce_context()` for details.
    :returns: :data:`True` if an internet connection is available,
              :data:`False` otherwise.

    This works by pinging 8.8.8.8 which is one of `Google public DNS servers`_.
    This IP address was chosen because it is documented that Google uses
    anycast_ to keep this IP address available at all times.

    .. _Google public DNS servers: https://developers.google.com/speed/public-dns/
    .. _anycast: https://en.wikipedia.org/wiki/Anycast
    """
    context = coerce_context(context)
    logger.debug("Checking if %s has internet connectivity ..", context)
    if context.test("ping", "-c1", "-w1", "8.8.8.8"):
        logger.debug("Confirmed that %s has internet connectivity.", context)
        return True
    else:
        logger.debug("No internet connectivity detected on %s.", context)
        return False
