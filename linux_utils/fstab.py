# linux-utils: Linux system administration tools for Python.
#
# Author: Peter Odding <peter@peterodding.com>
# Last Change: June 21, 2017
# URL: https://linux-utils.readthedocs.io

"""Parsing of ``/etc/fstab`` configuration files."""

# Standard library modules.
import logging

# External dependencies.
from humanfriendly.text import split
from property_manager import lazy_property

# Modules included in our package.
from linux_utils import coerce_device_file
from linux_utils.tabfile import TabFileEntry, parse_tab_file

# Initialize a logger for this module.
logger = logging.getLogger(__name__)


def find_mounted_filesystems(filename='/proc/mounts', context=None):
    """
    Get information about mounted filesystem from ``/proc/mounts``.

    :param filename: The absolute pathname of the file to parse (a string,
                     defaults to ``/proc/mounts``).
    :param context: An execution context created by :mod:`executor.contexts`
                    (coerced using :func:`.coerce_context()`).
    :returns: A generator of :class:`FileSystemEntry` objects.

    This function is a trivial wrapper for :func:`parse_fstab()` that instructs
    it to parse ``/proc/mounts`` instead of ``/etc/fstab``. Here's an
    example:

    >>> from humanfriendly import format_table
    >>> from linux_utils.fstab import find_mounted_filesystems
    >>> print(format_table(
    ...    data=[
    ...        (entry.mount_point, entry.device_file, entry.vfs_type)
    ...        for entry in find_mounted_filesystems()
    ...        if entry.vfs_type not in (
    ...            # While writing this example I was actually surprised to
    ...            # see how many `virtual filesystems' a modern Linux system
    ...            # has mounted by default (based on Ubuntu 16.04).
    ...            'autofs', 'cgroup', 'debugfs', 'devpts', 'devtmpfs', 'efivarfs',
    ...            'fuse.gvfsd-fuse', 'fusectl', 'hugetlbfs', 'mqueue', 'proc',
    ...            'pstore', 'securityfs', 'sysfs', 'tmpfs',
    ...        )
    ...    ],
    ...    column_names=["Mount point", "Device", "Type"],
    ... ))
    ---------------------------------------------------
    | Mount point  | Device                    | Type |
    ---------------------------------------------------
    | /            | /dev/mapper/internal-root | ext4 |
    | /boot        | /dev/sda5                 | ext4 |
    | /boot/efi    | /dev/sda1                 | vfat |
    | /mnt/backups | /dev/mapper/backups       | ext4 |
    ---------------------------------------------------
    """
    return parse_fstab(filename=filename, context=context)


def parse_fstab(filename='/etc/fstab', context=None):
    """
    Parse the Linux configuration file ``/etc/fstab``.

    :param filename: The absolute pathname of the file to parse (a string,
                     defaults to ``/etc/fstab``).
    :param context: An execution context created by :mod:`executor.contexts`
                    (coerced using :func:`.coerce_context()`).
    :returns: A generator of :class:`FileSystemEntry` objects.

    Here's an example:

    >>> from linux_utils.fstab import parse_fstab
    >>> next(e for e in parse_fstab() if e.mount_point == '/')
    FileSystemEntry(
        configuration_file='/etc/fstab',
        line_number=8,
        device_file='UUID=7801a1c2-7ad7-4c0b-9fbb-2a47ae802f71',
        mount_point='/',
        vfs_type='ext4',
        options=['errors=remount-ro'],
        dump_frequency=0,
        check_order=1,
    )
    """
    for entry in parse_tab_file(filename=filename, context=context):
        if len(entry.tokens) >= 4:
            # Transform the object into our type.
            entry.__class__ = FileSystemEntry
            yield entry
        elif len(entry.tokens) > 0:
            logger.warning("Ignoring line %i in %s because I couldn't parse it!",
                           entry.line_number, entry.configuration_file)


class FileSystemEntry(TabFileEntry):

    """
    An entry parsed from ``/etc/fstab``.

    Each entry in the fstab file has six fields, these are mapped to the
    following properties:

    1. :attr:`device`
    2. :attr:`mount_point`
    3. :attr:`vfs_type`
    4. :attr:`options`
    5. :attr:`dump_frequency`
    6. :attr:`check_order`

    Refer to the `fstab man page`_ for more information.

    .. _fstab man page: https://manpages.debian.org/fstab
    """

    @lazy_property
    def check_order(self):
        """The order in which the filesystem should be checked at boot time (an integer number, defaults to 0)."""
        try:
            return int(self.tokens[5])
        except IndexError:
            return 0

    @property
    def device(self):
        """
        The block special device or remote filesystem to be mounted (a string).

        The value of this property may be a ``UUID=...`` expression.
        """
        return self.tokens[0]

    @lazy_property
    def device_file(self):
        """
        The block special device to be mounted (a string).

        The value of this property is computed by passing :attr:`device` to
        :func:`.coerce_device_file()`.
        """
        return coerce_device_file(self.device)

    @lazy_property
    def dump_frequency(self):
        """The dump frequency for the filesystem (an integer number, defaults to 0)."""
        try:
            return int(self.tokens[4])
        except IndexError:
            return 0

    @lazy_property
    def mount_point(self):
        r"""
        The mount point for the filesystem (a string).

        Each occurrence of the escape sequence ``\040`` is replaced by a space.
        """
        return self.tokens[1].replace(r'\040', ' ')

    @lazy_property
    def options(self):
        """The mount options for the filesystem (a list of strings)."""
        return split(self.tokens[3])

    @property
    def vfs_type(self):
        """The type of filesystem (a string like 'ext4' or 'xfs')."""
        return self.tokens[2]
