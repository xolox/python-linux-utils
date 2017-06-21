# Test suite for the `linux-utils' Python package.
#
# Author: Peter Odding <peter@peterodding.com>
# Last Change: June 21, 2017
# URL: https://linux-utils.readthedocs.io

"""Test suite for the `linux-utils` package."""

# Standard library modules.
import logging
import tempfile
import unittest

# External dependencies.
import coloredlogs
from executor.contexts import LocalContext

# The module we're testing.
from linux_utils import coerce_context, coerce_device_file
from linux_utils.crypttab import parse_crypttab
from linux_utils.fstab import find_mounted_filesystems, parse_fstab
from linux_utils.tabfile import parse_tab_file

# Initialize a logger for this module.
logger = logging.getLogger(__name__)


class LinuxUtilsTestCase(unittest.TestCase):

    """:mod:`unittest` compatible container for `linux-utils` tests."""

    def setUp(self):
        """Enable verbose logging and reset it after each test."""
        coloredlogs.install(level='DEBUG')

    def test_coerce_context(self):
        """Test coercion of execution contexts."""
        assert isinstance(coerce_context(None), LocalContext)
        instance = LocalContext()
        assert coerce_context(instance) is instance
        self.assertRaises(ValueError, coerce_context, 1)

    def test_coerce_device_file(self):
        """Test coercion of device identifiers to device files."""
        assert coerce_device_file('/dev/mapper/backups') == '/dev/mapper/backups'
        assert (coerce_device_file('UUID=1012dd1a-a455-40c4-914f-f3b1b2cf5b86') ==
                '/dev/disk/by-uuid/1012dd1a-a455-40c4-914f-f3b1b2cf5b86')
        self.assertRaises(ValueError, coerce_device_file, 'LABEL=test')

    def test_parse_tab_file(self):
        """Test the generic tab file parsing."""
        fake_entry = [
            'backups',
            'UUID=1012dd1a-a455-40c4-914f-f3b1b2cf5b86',
            '/root/keys/backups.key',
            'luks,discard,noauto',
        ]
        with tempfile.NamedTemporaryFile() as temporary_file:
            # Create a fake /etc/crypttab file.
            temporary_file.write(' '.join(fake_entry).encode('ascii'))
            # Make sure the contents are on disk.
            temporary_file.flush()
            # Parse the file.
            entries = list(parse_tab_file(filename=temporary_file.name))
            # Check the results.
            assert len(entries) == 1
            assert entries[0].configuration_file == temporary_file.name
            assert entries[0].line_number == 1
            assert entries[0].tokens == fake_entry

    def test_parse_crypttab(self):
        """Test the ``/etc/crypttab`` parsing."""
        target = 'this-should-not-exist'
        source = 'UUID=36c44011-999d-4e4d-98cd-43e169b839e7'
        key_file = '/root/keys/backups.key'
        options = ['luks', 'discard', 'noauto']
        fake_entry = [target, source, key_file, ','.join(options)]
        with tempfile.NamedTemporaryFile() as temporary_file:
            # Create a fake /etc/crypttab file with a valid entry.
            temporary_file.write((' '.join(fake_entry) + '\n').encode('ascii'))
            # Also add a corrupt entry to the file.
            temporary_file.write('oops!\n'.encode('ascii'))
            # Make sure the contents are on disk.
            temporary_file.flush()
            # Parse the file.
            entries = list(parse_crypttab(filename=temporary_file.name))
            # Check the results.
            assert len(entries) == 1
            assert entries[0].is_available is False
            assert entries[0].is_unlocked is False
            assert entries[0].key_file == key_file
            assert entries[0].options == options
            assert entries[0].source == source
            assert entries[0].source_device.startswith('/dev/disk/by-uuid/')
            assert entries[0].target == target

    def test_parse_fstab(self):
        """Test the ``/etc/fstab`` parsing."""
        device_file = '/dev/mapper/backups'
        mount_point = '/mnt/backups'
        vfs_type = 'ext4'
        options = ['noauto', 'errors=remount-ro']
        dump_frequency = 1
        check_order = 0
        fake_entry = [device_file, mount_point, vfs_type, ','.join(options),
                      str(dump_frequency), str(check_order)]
        with tempfile.NamedTemporaryFile() as temporary_file:
            # Create a fake /etc/crypttab file with a valid and complete entry.
            temporary_file.write((' '.join(fake_entry) + '\n').encode('ascii'))
            # Also add a valid but incomplete entry.
            temporary_file.write((' '.join(fake_entry[:4]) + '\n').encode('ascii'))
            # Also add a corrupt entry to the file.
            temporary_file.write('oops!\n'.encode('ascii'))
            # Make sure the contents are on disk.
            temporary_file.flush()
            # Parse the file.
            entries = list(parse_fstab(filename=temporary_file.name))
            # Check the results.
            assert len(entries) == 2
            # Check the first (valid and complete) entry.
            assert entries[0].device_file == device_file
            assert entries[0].mount_point == mount_point
            assert entries[0].vfs_type == vfs_type
            assert entries[0].options == options
            assert entries[0].dump_frequency == dump_frequency
            assert entries[0].check_order == check_order
            # Check the second (valid but incomplete) entry.
            assert entries[1].dump_frequency == 0
            assert entries[1].check_order == 0

    def test_find_mounted_filesystems(self):
        """Test the ``/proc/mounts`` parsing."""
        assert any(entry.mount_point == '/' for entry in find_mounted_filesystems())
