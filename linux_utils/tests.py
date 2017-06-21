# Test suite for the `linux-utils' Python package.
#
# Author: Peter Odding <peter@peterodding.com>
# Last Change: June 21, 2017
# URL: https://linux-utils.readthedocs.io

"""Test suite for the `linux-utils` package."""

# Standard library modules.
import functools
import logging
import os
import tempfile
import unittest

# External dependencies.
import coloredlogs
from executor import ExternalCommandFailed, execute
from executor.contexts import LocalContext
from humanfriendly import compact
from mock import MagicMock

# The module we're testing.
from linux_utils import coerce_context, coerce_device_file, coerce_size
from linux_utils.crypttab import parse_crypttab
from linux_utils.fstab import find_mounted_filesystems, parse_fstab
from linux_utils.luks import (
    TemporaryKeyFile,
    create_encrypted_filesystem,
    create_image_file,
    cryptdisks_start,
    cryptdisks_stop,
    lock_filesystem,
    unlock_filesystem,
)
from linux_utils.tabfile import parse_tab_file

# The following files have fixed locations to enable the configuration file
# /etc/sudoers.d/linux-utils-tests to enable passwordless sudo as selectively
# as possible, to enable running the test suite non-interactively.
TEST_IMAGE_FILE = os.path.join(tempfile.gettempdir(), 'linux-utils.img')
TEST_KEY_FILE = os.path.join(tempfile.gettempdir(), 'linux-utils.key')
TEST_TARGET_NAME = 'linux-utils'
TEST_TARGET_DEVICE = os.path.join('/dev/mapper', TEST_TARGET_NAME)
TEST_UNKNOWN_TARGET = 'linux-utils-invalid'

# Initialize a logger for this module.
logger = logging.getLogger(__name__)


class LinuxUtilsTestCase(unittest.TestCase):

    """:mod:`unittest` compatible container for `linux-utils` tests."""

    def setUp(self):
        """Enable verbose logging and reset it after each test."""
        coloredlogs.install(level='DEBUG')

    def tearDown(self):
        """Cleanup the image file created by the test suite."""
        if os.path.exists(TEST_IMAGE_FILE):
            os.unlink(TEST_IMAGE_FILE)

    def skipTest(self, text, *args, **kw):
        """
        Enable backwards compatible "marking of tests to skip".

        By calling this method from a return statement in the test to be
        skipped the test can be marked as skipped when possible, without
        breaking the test suite when unittest.TestCase.skipTest() isn't
        available.
        """
        reason = compact(text, *args, **kw)
        try:
            super(LinuxUtilsTestCase, self).skipTest(reason)
        except AttributeError:
            # unittest.TestCase.skipTest() isn't available in Python 2.6.
            logger.warning("%s", reason)

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

    def test_coerce_size(self):
        """Test coercion of data sizes."""
        assert coerce_size(1) == 1
        assert coerce_size('5 KiB') == 5120
        self.assertRaises(ValueError, coerce_size, None)

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
        source = 'UUID=36c44011-999d-4e4d-98cd-43e169b839e7'
        key_file = '/root/keys/backups.key'
        options = ['luks', 'discard', 'noauto']
        fake_entry = [TEST_UNKNOWN_TARGET, source, key_file, ','.join(options)]
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
            assert entries[0].target == TEST_UNKNOWN_TARGET

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

    def test_create_image_file(self):
        """Test image file creation."""
        size = coerce_size('1 MiB')
        create_image_file(TEST_IMAGE_FILE, size)
        # Make sure the image file was created with the correct size.
        assert os.path.getsize(TEST_IMAGE_FILE) == size
        # Make sure the contents of the image file are zero bytes.
        with open(TEST_IMAGE_FILE, 'rb') as handle:
            for byte in iter(functools.partial(handle.read, 1), b''):
                assert byte == b'\x00'

    def test_generate_key_file(self):
        """Test key file generation."""
        context = LocalContext(sudo=True)
        size = coerce_size('4 KiB')
        with TemporaryKeyFile(context=context, filename=TEST_KEY_FILE, size=size):
            # Make sure the key file was created with the correct size.
            assert os.path.getsize(TEST_KEY_FILE) == size
            # Ensure that the key file contains some randomness.
            cat = context.execute('cat', TEST_KEY_FILE, capture=True)
            random_bytes = set(cat.stdout)
            # Although I know that (by definition of randomness) the following
            # assertion can fail I nevertheless feel that it adds value :-p.
            assert len(random_bytes) > 10

    def test_create_encrypted_filesystem(self):
        """Test creation of encrypted filesystems."""
        with TemporaryKeyFile(filename=TEST_KEY_FILE):
            create_image_file(filename=TEST_IMAGE_FILE, size=coerce_size('10 MiB'))
            create_encrypted_filesystem(device_file=TEST_IMAGE_FILE, key_file=TEST_KEY_FILE)
            assert 'LUKS' in execute('file', TEST_IMAGE_FILE, capture=True)

    def test_unlock_encrypted_filesystem(self):
        """Test unlocking of encrypted filesystems."""
        with TemporaryKeyFile(filename=TEST_KEY_FILE):
            create_image_file(filename=TEST_IMAGE_FILE, size=coerce_size('10 MiB'))
            create_encrypted_filesystem(device_file=TEST_IMAGE_FILE, key_file=TEST_KEY_FILE)
            unlock_filesystem(device_file=TEST_IMAGE_FILE, target=TEST_TARGET_NAME, key_file=TEST_KEY_FILE)
            assert os.path.exists(os.path.join('/dev/mapper', TEST_TARGET_NAME))
            lock_filesystem(target=TEST_TARGET_NAME)
            assert not os.path.exists(os.path.join('/dev/mapper', TEST_TARGET_NAME))

    def test_cryptdisks_start_native(self):
        """Test integration with cryptdisks_start."""
        self.cryptdisks_start_helper(emulated=False)

    def test_cryptdisks_start_emulated(self):
        """Test integration with cryptdisks_start."""
        self.cryptdisks_start_helper(emulated=True)

    def cryptdisks_start_helper(self, emulated):
        """
        Test cryptdisks_start integration and emulation.

        This test requires the following line to be present in ``/etc/crypttab``::

         linux-utils /tmp/linux-utils.img /tmp/linux-utils.key luks,noauto
        """
        if not any(entry.target == TEST_TARGET_NAME and
                   entry.source == TEST_IMAGE_FILE and
                   entry.key_file == TEST_KEY_FILE and
                   'luks' in entry.options
                   for entry in parse_crypttab()):
            return self.skipTest("/etc/crypttab isn't set up to test cryptdisks_start!")
        context = LocalContext()
        if emulated:
            # Disable the use of the `cryptdisks_start' program.
            context.find_program = MagicMock(return_value=[])
        # Generate the key file.
        with TemporaryKeyFile(filename=TEST_KEY_FILE):
            # Create the image file and the encrypted filesystem.
            create_image_file(filename=TEST_IMAGE_FILE, size=coerce_size('10 MiB'))
            create_encrypted_filesystem(device_file=TEST_IMAGE_FILE, key_file=TEST_KEY_FILE)
            # Make sure the mapped device file doesn't exist yet.
            assert not os.path.exists(TEST_TARGET_DEVICE)
            # Unlock the encrypted filesystem using `cryptdisks_start'.
            cryptdisks_start(context=context, target=TEST_TARGET_NAME)
            # Make sure the mapped device file has appeared.
            assert os.path.exists(TEST_TARGET_DEVICE)
            # Unlock the encrypted filesystem again (this should be a no-op).
            cryptdisks_start(context=context, target=TEST_TARGET_NAME)
            # Make sure the mapped device file still exists.
            assert os.path.exists(TEST_TARGET_DEVICE)
            # Lock the filesystem before we finish.
            cryptdisks_stop(context=context, target=TEST_TARGET_NAME)
            # Make sure the mapped device file has disappeared.
            assert not os.path.exists(TEST_TARGET_DEVICE)
            # Lock the filesystem again (this should be a no-op).
            cryptdisks_stop(context=context, target=TEST_TARGET_NAME)
            # Make sure the mapped device file is still gone.
            assert not os.path.exists(TEST_TARGET_DEVICE)
            # Test the error handling.
            for function in cryptdisks_start, cryptdisks_stop:
                self.assertRaises(
                    ValueError if emulated else ExternalCommandFailed,
                    function,
                    context=context,
                    target=TEST_UNKNOWN_TARGET,
                )
