# linux-utils: Linux system administration tools for Python.
#
# Author: Peter Odding <peter@peterodding.com>
# Last Change: June 21, 2017
# URL: https://linux-utils.readthedocs.io

"""
Parsing of ``/etc/crypttab`` configuration files.

The cryptsetup_ program is used to manage LUKS_ based full disk encryption and
Debian provides some niceties around cryptsetup to make it easier to use,
specifically:

- The ``/etc/crypttab`` configuration file contains static information about
  encrypted filesystems and enables unlocking of encrypted filesystems when the
  system is booted. Refer to the `crypttab man page`_ for more information.

- The cryptdisks_start_ and cryptdisks_stop_ commands can be used to manually
  unlock encrypted filesystems that are configured in ``/etc/crypttab`` with
  the ``noauto`` option (meaning the device is ignored during boot).

.. _cryptsetup: https://manpages.debian.org/cryptsetup
.. _LUKS: https://en.wikipedia.org/wiki/Linux_Unified_Key_Setup
.. _crypttab man page: https://manpages.debian.org/crypttab
.. _cryptdisks_start: https://manpages.debian.org/cryptdisks_start
.. _cryptdisks_stop: https://manpages.debian.org/cryptdisks_stop
"""

# Standard library modules.
import logging
import os

# External dependencies.
from humanfriendly.text import split
from property_manager import lazy_property

# Modules included in our package.
from linux_utils import coerce_device_file
from linux_utils.tabfile import TabFileEntry, parse_tab_file

# Initialize a logger for this module.
logger = logging.getLogger(__name__)


def parse_crypttab(filename='/etc/crypttab', context=None):
    """
    Parse the Debian Linux configuration file ``/etc/crypttab``.

    :param filename: The absolute pathname of the file to parse (a string,
                     defaults to ``/etc/crypttab``).
    :param context: An execution context created by :mod:`executor.contexts`
                    (coerced using :func:`.coerce_context()`).
    :returns: A generator of :class:`EncryptedFileSystemEntry` objects.

    Here's an example:

    >>> from linux_utils.crypttab import parse_crypttab
    >>> print(next(parse_crypttab()))
    EncryptedFileSystemEntry(
        configuration_file='/etc/crypttab',
        line_number=3,
        target='ssd',
        source='UUID=31678141-3931-4683-a4d2-09eadec81d01',
        source_device='/dev/disk/by-uuid/31678141-3931-4683-a4d2-09eadec81d01',
        key_file='none',
        options=['luks', 'discard'],
    )
    """
    for entry in parse_tab_file(filename=filename, context=context):
        if len(entry.tokens) >= 4:
            # Transform the object into our type.
            entry.__class__ = EncryptedFileSystemEntry
            yield entry
        elif len(entry.tokens) > 0:
            logger.warning("Ignoring line %i in %s because I couldn't parse it!",
                           entry.line_number, entry.configuration_file)


class EncryptedFileSystemEntry(TabFileEntry):

    """
    An entry parsed from ``/etc/crypttab``.

    Each entry in the crypttab file has four fields, these are mapped to the
    following properties:

    1. :attr:`target`
    2. :attr:`source`
    3. :attr:`key_file`
    4. :attr:`options`

    Refer to the `crypttab man page`_ for more information about these fields.
    The computed properties :attr:`is_available`, :attr:`is_unlocked` and
    :attr:`source_device` are based on the parsed values of the four fields
    above.
    """

    @property
    def is_available(self):
        """:data:`True` if :attr:`source_device` exists, :data:`False` otherwise."""
        return self.context.exists(self.source_device)

    @property
    def is_unlocked(self):
        """:data:`True` if :attr:`target_device` exists, :data:`False` otherwise."""
        return self.context.exists(self.target_device)

    @property
    def key_file(self):
        """
        The file to use as a key for decrypting the data of the source device (a string or :data:`None`).

        When the key file field in ``/etc/crypttab`` is set to ``none`` the
        value of this property will be :data:`None`, this makes checking
        whether an encrypted filesystem has a key file configured much more
        Pythonic.
        """
        return self.tokens[2] if self.tokens[2] != 'none' else None

    @lazy_property
    def options(self):
        """The encryption options for the filesystem (a list of strings)."""
        return split(self.tokens[3])

    @property
    def source(self):
        """
        The block special device or file that contains the encrypted data (a string).

        The value of this property may be a ``UUID=...`` expression instead of
        the pathname of a block special device or file.
        """
        return self.tokens[1]

    @lazy_property
    def source_device(self):
        """
        The block special device or file that contains the encrypted data (a string).

        The value of this property is computed by passing :attr:`source` to
        :func:`.coerce_device_file()`.
        """
        return coerce_device_file(self.source)

    @property
    def target(self):
        """The mapped device name (a string)."""
        return self.tokens[0]

    @lazy_property
    def target_device(self):
        """The absolute pathname of the device file corresponding to :attr:`target` (a string)."""
        return os.path.join('/dev/mapper', self.target)
