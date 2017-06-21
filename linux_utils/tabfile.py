# linux-utils: Linux system administration tools for Python.
#
# Author: Peter Odding <peter@peterodding.com>
# Last Change: June 21, 2017
# URL: https://linux-utils.readthedocs.io

"""Generic parsing of Linux configuration files like ``/etc/fstab`` and ``/etc/crypttab``."""

# Standard library modules.
import re

# External dependencies.
from property_manager import PropertyManager, mutable_property

# Modules included in our package.
from linux_utils import coerce_context


def parse_tab_file(filename, context=None, encoding='UTF-8'):
    """
    Parse a Linux configuration file like ``/etc/fstab`` or ``/etc/crypttab``.

    :param filename: The absolute pathname of the file to parse (a string).
    :param context: An execution context created by :mod:`executor.contexts`
                    (coerced using :func:`.coerce_context()`).
    :param encoding: The name of the text encoding of the file (a string).
    :returns: A generator of :class:`TabFileEntry` objects.

    This function strips comments (the character ``#`` until the end of
    the line) and splits each line into tokens separated by whitespace.
    """
    context = coerce_context(context)
    contents = context.read_file(filename).decode(encoding)
    for line_number, line in enumerate(contents.splitlines(), start=1):
        # Strip comments.
        line = re.sub('#.*', '', line)
        # Tokenize input.
        tokens = line.split()
        if tokens:
            yield TabFileEntry(
                context=context,
                configuration_file=filename,
                line_number=line_number,
                tokens=tokens,
            )


class TabFileEntry(PropertyManager):

    """Container for the results of :func:`parse_tab_file()`."""

    @mutable_property
    def context(self):
        """The execution context from which the configuration file was retrieved."""

    @mutable_property
    def configuration_file(self):
        """The name of the configuration file from which this entry was parsed (a string)."""

    @mutable_property
    def line_number(self):
        """The line number from which this entry was parsed (an integer)."""

    @mutable_property
    def tokens(self):
        """The tokens split on whitespace (a nonempty list of strings)."""
