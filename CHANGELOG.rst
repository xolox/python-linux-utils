Changelog
=========

The purpose of this document is to list all of the notable changes to this
project. The format was inspired by `Keep a Changelog`_. This project adheres
to `semantic versioning`_.

.. contents::
   :local:

.. _Keep a Changelog: http://keepachangelog.com/
.. _semantic versioning: http://semver.org/

`Release 0.6`_ (2018-07-03)
---------------------------

- **Bug fix:** Don't raise an exception in ``parse_crypttab()`` when
  ``/etc/crypttab`` doesn't exist. I ran into the exception that used to be
  raised when I ran ``upgrade-remote-system`` (in debuntu-tools_) against a
  server without any encrypted filesystems and was unpleasantly surprised that
  my "upgrade && reboot && cleanup kernels" had aborted halfway 😇.

- **Miscellaneous changes:** (lots of them)

  - Added this changelog and restructured the documentation.
  - Integrated ``property_manager.sphinx`` to improve documentation.
  - Minor changes to the ``setup.py`` script:

    - Added the ``license='MIT'`` key.
    - Changed alpha trove classifier to beta.
    - Added some additional trove classifiers.

  - Added usage messages of ``cryptdisks-start-fallback`` and
    ``cryptdisks-stop-fallback`` to readme.
  - Changed ``MANIFEST.in`` to include documentation in source distributions.
  - Minor improvements to documentation of ``linux_utils.cli`` module.
  - Bumped copyright to 2018.


.. _Release 0.6: https://github.com/xolox/python-linux-utils/compare/0.5...0.6
.. _debuntu-tools: https://pypi.python.org/pypi/debuntu-tools

`Release 0.5`_ (2017-06-24)
---------------------------

- Added ``linux_utils.atomic`` module (atomic filesystem operations).
- Expose parsed NFS information in ``FileSystemEntry`` objects.
- Test coverage improvements and minor code changes.
- Consistently define ``__all__`` for modules.

.. _Release 0.5: https://github.com/xolox/python-linux-utils/compare/0.4.1...0.5

`Release 0.4.1`_ (2017-06-23)
-----------------------------

A "vanity release" to add missing links in the README because the missing links
caused PyPI to render the readme on the project page as plain text instead of
reStructuredText converted to HTML :-).

.. _Release 0.4.1: https://github.com/xolox/python-linux-utils/compare/0.4...0.4.1

`Release 0.4`_ (2017-06-22)
---------------------------

Added the command line programs ``cryptdisks-start-fallback`` and
``cryptdisks-stop-fallback``. My reason for adding these was so that I could
refer to them in the documentation of my rsync-system-backup_ package:
`How to set up unattended backups to an encrypted USB disk
<http://rsync-system-backup.readthedocs.io/en/latest/howto/encrypted-usb-disk.html#unlock-the-encrypted-disk>`_.

.. _Release 0.4: https://github.com/xolox/python-linux-utils/compare/0.3...0.4

`Release 0.3`_ (2017-06-21)
---------------------------

Improved ``/etc/crypttab`` compatibility:

- Support for ``LABEL="..."`` device identifiers.
- Respect the ``/etc/crypttab`` options ``discard``, ``readonly`` and ``tries``.
- Ignore encrypted filesystems that aren't LUKS.

.. _Release 0.3: https://github.com/xolox/python-linux-utils/compare/0.2...0.3

`Release 0.2`_ (2017-06-21)
---------------------------

Added a Python API for ``cryptsetup`` (to control LUKS full disk encryption)
including Python emulation of ``cryptdisks_start`` and ``cryptdisks_stop``.

This functionality is making it easier for me to write test suites for Python
projects that involve disk encryption, for example crypto-drive-manager_ and
rsync-system-backup_.

.. _Release 0.2: https://github.com/xolox/python-linux-utils/compare/0.1...0.2
.. _crypto-drive-manager: https://pypi.python.org/pypi/crypto-drive-manager
.. _rsync-system-backup: https://pypi.python.org/pypi/rsync-system-backup

`Release 0.1`_ (2017-06-21)
---------------------------

The initial release of ``linux-utils`` supports parsing of the ``/etc/fstab``
(``/proc/mounts``) and ``/etc/crypttab`` configuration file formats based on a
"generic tabfile" parser. The :ref:`history` section of the readme explains why
this project came to be.

.. _Release 0.1: https://github.com/xolox/python-linux-utils/tree/0.1
