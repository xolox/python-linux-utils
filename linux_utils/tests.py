# Test suite for the `linux-utils' Python package.
#
# Author: Peter Odding <peter@peterodding.com>
# Last Change: February 9, 2020
# URL: https://linux-utils.readthedocs.io

"""Test suite for the `linux-utils` package."""

# Standard library modules.
import codecs
import functools
import logging
import os
import stat
import tempfile

# External dependencies.
from executor import ExternalCommandFailed, execute
from executor.contexts import LocalContext
from humanfriendly.text import dedent
from humanfriendly.testing import MockedProgram, TemporaryDirectory, TestCase, run_cli
from mock import MagicMock

# The module we're testing.
from linux_utils import coerce_context, coerce_device_file, coerce_size
from linux_utils.atomic import make_dirs, touch, write_contents
from linux_utils.cli import cryptdisks_start_cli, cryptdisks_stop_cli
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
from linux_utils.network import (
    determine_network_location,
    find_gateway_ip,
    find_gateway_mac,
    find_mac_address,
    have_internet_connection,
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


class LinuxUtilsTestCase(TestCase):

    """:mod:`unittest` compatible container for `linux-utils` tests."""

    def tearDown(self):
        """Cleanup the image file created by the test suite."""
        # Tear down our superclass.
        super(LinuxUtilsTestCase, self).tearDown()
        # Cleanup the image file created by the test suite.
        if os.path.exists(TEST_IMAGE_FILE):
            os.unlink(TEST_IMAGE_FILE)

    def test_coerce_context(self):
        """Test coercion of execution contexts."""
        assert isinstance(coerce_context(None), LocalContext)
        instance = LocalContext()
        assert coerce_context(instance) is instance
        self.assertRaises(ValueError, coerce_context, 1)

    def test_coerce_device_file(self):
        """Test coercion of device identifiers to device files."""
        assert coerce_device_file('/dev/mapper/backups') == '/dev/mapper/backups'
        assert (coerce_device_file('LABEL="Linux Boot"') ==
                r'/dev/disk/by-label/Linux\x20Boot')
        assert (coerce_device_file('UUID=1012dd1a-a455-40c4-914f-f3b1b2cf5b86') ==
                '/dev/disk/by-uuid/1012dd1a-a455-40c4-914f-f3b1b2cf5b86')
        self.assertRaises(
            ValueError, coerce_device_file,
            'PARTUUID=e6c021cc-d0d8-400c-8f5c-b10adeff65fe',
        )

    def test_coerce_size(self):
        """Test coercion of data sizes."""
        assert coerce_size(1) == 1
        assert coerce_size('5 KiB') == 5120
        self.assertRaises(ValueError, coerce_size, None)

    def test_make_dirs(self):
        """Test make_dirs()."""
        with TemporaryDirectory() as directory:
            subdirectory = os.path.join(directory, 'a', 'b', 'c')
            make_dirs(subdirectory)
            # Make sure the subdirectory was created.
            assert os.path.isdir(subdirectory)
            # Make sure existing directories don't raise an exception.
            make_dirs(subdirectory)
            # Make sure that errors other than EEXIST aren't swallowed. For the
            # purpose of this test we assume that /proc is the Linux `process
            # information pseudo-file system' whose top level directories
            # aren't writable (with or without superuser privileges).
            self.assertRaises(OSError, make_dirs, '/proc/linux-utils-test')

    def test_touch(self):
        """Test touch()."""
        expected_contents = u"Hello world!"
        with TemporaryDirectory() as directory:
            # Test that touch() creates files.
            filename = os.path.join(directory, 'file-to-touch')
            touch(filename)
            assert os.path.isfile(filename)
            # Test that touch() doesn't change a file's contents.
            with open(filename, 'w') as handle:
                handle.write(expected_contents)
            touch(filename)
            with open(filename) as handle:
                assert handle.read() == expected_contents

    def test_write_contents_create(self):
        """Test write_contents()."""
        expected_contents = u"Hello world!"
        with TemporaryDirectory() as directory:
            # Create the file.
            filename = os.path.join(directory, 'file-to-create')
            assert not os.path.exists(filename)
            write_contents(filename, expected_contents)
            # Make sure the file exists.
            assert os.path.exists(filename)
            # Validate the file's contents.
            with codecs.open(filename, 'r', 'UTF-8') as handle:
                assert handle.read() == expected_contents

    def test_write_contents_update(self):
        """Test write_contents()."""
        initial_contents = u"Hello world!"
        revised_contents = u"Something else"
        with TemporaryDirectory() as directory:
            # Create the file.
            filename = os.path.join(directory, 'file-to-update')
            write_contents(filename, initial_contents, mode=0o770)
            # Validate the file's mode.
            assert stat.S_IMODE(os.stat(filename).st_mode) == 0o770
            # Validate the file's contents.
            with codecs.open(filename, 'r', 'UTF-8') as handle:
                assert handle.read() == initial_contents
            # Update the file.
            write_contents(filename, revised_contents)
            # Validate the file's mode.
            assert stat.S_IMODE(os.stat(filename).st_mode) == 0o770
            # Validate the file's contents.
            with codecs.open(filename, 'r', 'UTF-8') as handle:
                assert handle.read() == revised_contents

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
        # The following entry concerns a local filesystem.
        local_filesystem = dict(
            device='/dev/mapper/backups',
            mount_point='/mnt/backups',
            vfs_type='ext4',
            options=['noauto', 'errors=remount-ro'],
            dump_frequency=1,
            check_order=0,
        )
        # The following entry concerns a directory exported over NFS.
        nfs_directory = '/exported/directory'
        nfs_server = '1.2.3.4'
        nfs_export = dict(
            device='%s:%s' % (nfs_server, nfs_directory),
            mount_point='/mnt/share',
            vfs_type='nfs',
            options=['noauto'],
        )
        # We define the ordered string fields of the entry for the local
        # filesystem here because we will re-use them to test support for
        # `incomplete' entries (without the last two fields).
        local_entry = [
            local_filesystem['device'],
            local_filesystem['mount_point'],
            local_filesystem['vfs_type'],
            ','.join(local_filesystem['options']),
            str(local_filesystem['dump_frequency']),
            str(local_filesystem['check_order']),
        ]
        with tempfile.NamedTemporaryFile() as temporary_file:
            # Create a fake /etc/crypttab file with a valid and complete entry.
            temporary_file.write((' '.join(local_entry) + '\n').encode('ascii'))
            # Also add a valid but incomplete entry.
            temporary_file.write((' '.join(local_entry[:4]) + '\n').encode('ascii'))
            # We also add an entry for a remote directory exported by an NFS server.
            temporary_file.write((' '.join([
                nfs_export['device'],
                nfs_export['mount_point'],
                nfs_export['vfs_type'],
                ','.join(nfs_export['options']),
            ]) + '\n').encode('ascii'))
            # Also add a corrupt entry to the file.
            temporary_file.write('oops!\n'.encode('ascii'))
            # Make sure the contents are on disk.
            temporary_file.flush()
            # Parse the file.
            entries = list(parse_fstab(filename=temporary_file.name))
            # Check the results.
            assert len(entries) == 3
            # Check the first (valid and complete) entry.
            assert entries[0].check_order == local_filesystem['check_order']
            assert entries[0].device == local_filesystem['device']
            assert entries[0].device_file == local_filesystem['device']
            assert entries[0].dump_frequency == local_filesystem['dump_frequency']
            assert entries[0].mount_point == local_filesystem['mount_point']
            assert entries[0].nfs_directory is None
            assert entries[0].nfs_server is None
            assert entries[0].options == local_filesystem['options']
            assert entries[0].vfs_type == local_filesystem['vfs_type']
            # Check the second (valid but incomplete) entry.
            assert entries[1].check_order == 0
            assert entries[1].device == local_filesystem['device']
            assert entries[1].device_file == local_filesystem['device']
            assert entries[1].dump_frequency == 0
            assert entries[1].mount_point == local_filesystem['mount_point']
            assert entries[1].nfs_directory is None
            assert entries[1].nfs_server is None
            assert entries[1].options == local_filesystem['options']
            assert entries[1].vfs_type == local_filesystem['vfs_type']
            # Check the third (remote) entry.
            assert entries[2].device == nfs_export['device']
            assert entries[2].mount_point == nfs_export['mount_point']
            assert entries[2].nfs_directory == nfs_directory
            assert entries[2].nfs_server == nfs_server
            assert entries[2].options == nfs_export['options']
            assert entries[2].vfs_type == nfs_export['vfs_type']

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

         linux-utils /tmp/linux-utils.img /tmp/linux-utils.key discard,luks,noauto,readonly,tries=1
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
            if emulated:
                cryptdisks_start(context=context, target=TEST_TARGET_NAME)
            else:
                returncode, output = run_cli(cryptdisks_start_cli, TEST_TARGET_NAME)
                assert returncode == 0
            # Make sure the mapped device file has appeared.
            assert os.path.exists(TEST_TARGET_DEVICE)
            # Unlock the encrypted filesystem again (this should be a no-op).
            cryptdisks_start(context=context, target=TEST_TARGET_NAME)
            # Make sure the mapped device file still exists.
            assert os.path.exists(TEST_TARGET_DEVICE)
            # Lock the filesystem before we finish.
            if emulated:
                cryptdisks_stop(context=context, target=TEST_TARGET_NAME)
            else:
                returncode, output = run_cli(cryptdisks_stop_cli, TEST_TARGET_NAME)
                assert returncode == 0
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

    def test_cryptdisks_start_stop_usage(self):
        """Test the ``cryptdisks-start-fallback`` usage message."""
        for fallback in cryptdisks_start_cli, cryptdisks_stop_cli:
            returncode, output = run_cli(fallback, merged=True)
            assert returncode == 0
            assert "Usage:" in output

    def test_cryptdisks_start_stop_error_reporting(self):
        """Test the ``cryptdisks-start-fallback`` error reporting."""
        for fallback in cryptdisks_start_cli, cryptdisks_stop_cli:
            returncode, output = run_cli(fallback, TEST_UNKNOWN_TARGET, merged=True)
            assert returncode != 0

    def test_determine_network_location(self):
        """Test :func:`linux_utils.network.determine_network_location()`."""
        with self.mock_arp, self.mock_ip:
            # Make sure the happy path works as intended.
            assert determine_network_location(home=['80:34:58:ad:6c:f5']) == 'home'
            # Make sure nothing bad happens when we're not on a known network.
            assert determine_network_location() is None

    def test_find_gateway_ip(self):
        """Test :func:`linux_utils.network.find_gateway_ip()`."""
        with self.mock_ip:
            assert find_gateway_ip() == '192.168.1.1'

    def test_find_gateway_mac(self):
        """Test :func:`linux_utils.network.find_gateway_mac()`."""
        with self.mock_arp, self.mock_ip:
            assert find_gateway_mac() == '80:34:58:ad:6c:f5'

    def test_find_mac_address(self):
        """Test :func:`linux_utils.network.find_mac_address()`."""
        with self.mock_arp:
            assert find_mac_address('192.168.1.4') == '4b:21:f5:49:88:85'

    def test_have_internet_connection(self):
        """Test :func:`linux_utils.network.have_internet_connection().`"""
        with MockedProgram(name='ping', returncode=0):
            assert have_internet_connection() is True
        with MockedProgram(name='ping', returncode=1):
            assert have_internet_connection() is False

    @property
    def mock_arp(self):
        """Mocked ``arp`` program."""
        return MockedProgram(name='arp', script=dedent("""
            cat << EOF
            Address                  HWtype  HWaddress           Flags Mask            Iface
            192.168.1.4              ether   4b:21:f5:49:88:85   C                     wlp3s0
            192.168.3.28             ether   3d:a6:19:62:9a:83   C                     wlp3s0
            192.168.3.5              ether   c5:4c:8d:56:25:0c   C                     wlp3s0
            192.168.1.1              ether   80:34:58:ad:6c:f5   C                     wlp3s0
            192.168.3.2              ether   20:22:a0:22:0c:db   C                     wlp3s0
            192.168.1.12             ether   ad:12:75:46:e9:70   C                     wlp3s0
            192.168.3.6              ether   08:33:c7:ef:f7:27   C                     wlp3s0
            192.168.1.11             ether   c9:0e:95:24:68:31   C                     wlp3s0
            192.168.3.4              ether   e7:e6:2c:3b:bc:8a   C                     wlp3s0
            192.168.3.3              ether   72:d7:d3:2c:54:93   C                     wlp3s0
            192.168.1.6              ether   95:ef:85:cf:d3:36   C                     wlp3s0
            192.168.3.7              ether   65:c0:be:40:cd:31   C                     wlp3s0
            EOF
        """))

    @property
    def mock_ip(self):
        """Mocked ``ip route show`` program."""
        return MockedProgram(name='ip', script=dedent("""
            cat << EOF
            default via 192.168.1.1 dev wlp3s0 proto dhcp metric 600
            169.254.0.0/16 dev virbr0 scope link metric 1000 linkdown
            192.168.0.0/16 dev wlp3s0 proto kernel scope link src 192.168.2.214 metric 600
            192.168.122.0/24 dev virbr0 proto kernel scope link src 192.168.122.1 linkdown
            EOF
        """))
