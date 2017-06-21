# linux-utils: Linux system administration tools for Python.
#
# Author: Peter Odding <peter@peterodding.com>
# Last Change: June 21, 2017
# URL: https://linux-utils.readthedocs.io

"""Linux system administration tools for Python."""

# Standard library modules.
import numbers
import os

# External dependencies.
from executor.contexts import AbstractContext, LocalContext
from humanfriendly import parse_size
from six import string_types

__version__ = '0.2'
"""Semi-standard module versioning."""


def coerce_context(value):
    """
    Coerce a value to an execution context.

    :param value: The value to coerce (an execution context created
                  by :mod:`executor.contexts` or :data:`None`).
    :returns: An execution context created by :mod:`executor.contexts`.
    :raises: :exc:`~exceptions.ValueError` when `value` isn't :data:`None`
             but also isn't a valid execution context.
    """
    if value is None:
        value = LocalContext()
    if not isinstance(value, AbstractContext):
        msg = "Expected execution context or None, got %r instead!"
        raise ValueError(msg % type(value))
    return value


def coerce_device_file(expression):
    """
    Coerce a device identifier to a device file.

    :param expression: The device identifier (a string).
    :returns: The pathname of the device file (a string).
    :raises: :exc:`~exceptions.ValueError` when an unsupported device
             identifier is encountered.

    If you pass in a ``UUID=...`` expression (as found in e.g. ``/etc/fstab``)
    you will get back a pathname starting with ``/dev/disk/by-uuid``:

    >>> from linux_utils import coerce_device_file
    >>> coerce_device_file('UUID=7801a1c2-7ad7-4c0b-9fbb-2a47ae802f71')
    '/dev/disk/by-uuid/7801a1c2-7ad7-4c0b-9fbb-2a47ae802f71'

    If `expression` is already a pathname it will pass through untouched:

    >>> coerce_device_file('/dev/mapper/backups')
    '/dev/mapper/backups'

    Unsupported device identifiers raise an exception:

    >>> coerce_device_file('LABEL=backups')
    Traceback (most recent call last):
      File "linux_utils/__init__.py", line 34, in coerce_device_file
        raise ValueError(msg % name)
    ValueError: Unsupported device identifier! ('LABEL')
    """
    if '=' in expression:
        name, _, value = expression.partition('=')
        if name.upper() == 'UUID':
            return os.path.join('/dev/disk/by-uuid', value.lower())
        else:
            msg = "Unsupported device identifier! (%r)"
            raise ValueError(msg % name)
    return expression


def coerce_size(value):
    """
    Coerce a human readable data size to the number of bytes.

    :param value: The value to coerce (a number or string).
    :returns: The number of bytes (a number).
    :raises: :exc:`~exceptions.ValueError` when `value` isn't a number or
             a string supported by :func:`~humanfriendly.parse_size()`.
    """
    if isinstance(value, string_types):
        value = parse_size(value)
    if not isinstance(value, numbers.Number):
        msg = "Unsupported data size! (%r)"
        raise ValueError(msg % value)
    return value
