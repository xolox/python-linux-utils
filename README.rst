linux-utils: Linux system administration tools for Python
=========================================================

.. image:: https://travis-ci.org/xolox/python-linux-utils.svg?branch=master
   :target: https://travis-ci.org/xolox/python-linux-utils

.. image:: https://coveralls.io/repos/xolox/python-linux-utils/badge.svg?branch=master
   :target: https://coveralls.io/r/xolox/python-linux-utils?branch=master

The Python package `linux-utils` provides utility functions that make it easy
to script system administration tasks on Linux_ systems in Python. At the
moment only parsing of the ``/etc/fstab`` and ``/etc/crypttab`` configuration
files is implemented, but more functionality will soon be released. The package
is currently tested on cPython 2.6, 2.7, 3.4, 3.5, 3.6 and PyPy (2.7).

.. contents::
   :local:

Installation
------------

The `linux-utils` package is available on PyPI_ which means installation should
be as simple as:

.. code-block:: sh

   $ pip install linux-utils

There's actually a multitude of ways to install Python packages (e.g. the `per
user site-packages directory`_, `virtual environments`_ or just installing
system wide) and I have no intention of getting into that discussion here, so
if this intimidates you then read up on your options before returning to these
instructions ;-).

Usage
-----

Please refer to the API documentation available on `Read the Docs`_.

History
-------

Back in 2015 I wrote some Python code to parse the Linux configuration files
``/etc/fstab`` and ``/etc/crypttab`` for use in crypto-drive-manager_. Fast
forward to 2017 and I found myself wanting to use the same functionality
in rsync-system-backup_. Three options presented themselves to me:

1. **Copy/paste the relevant code.** Having to maintain the same code in
   multiple places causes lower quality code because having to duplicate the
   effort of writing documentation, developing tests and fixing bugs is a very
   demotivating endeavor.

   In fact sometime in 2016 I *did* copy/paste parts of this code into a
   project at work, because I needed similar functionality there. Of course
   since then the two implementations have started diverging :-p.

2. **Make crypto-drive-manager a dependency of rsync-system-backup.** Although
   this approach is less ugly than copy/pasting the code, it still isn't
   exactly elegant because the two projects have nothing to do with each other
   apart from working with LUKS encrypted disks on Linux.

3. **Extract the functionality into a new package.** In my opinion this is
   clearly the most elegant approach, unfortunately it also requires the most
   work from me :-). On the plus side I'm publishing the new package with a
   test suite which means less untested code remains in crypto-drive-manager_
   (which doesn't have a test suite at the time of writing).

While extracting the code I shortly considered integrating the functionality
into debuntu-tools_, however the ``/etc/fstab`` and ``/etc/crypttab`` parsing
isn't specific to Debian or Ubuntu at all and debuntu-tools_ has several
dependencies that aren't relevant to Linux configuration file parsing.

Tangentially related: The reason I went with the extremely generic name
`linux-utils` is because I will be adding more *"specific to Linux but not
Debian"* functionality to this package in the very near future :-).

Contact
-------

The latest version of `linux-utils` is available on PyPI_ and GitHub_. The
documentation is hosted on `Read the Docs`_. For bug reports please create an
issue on GitHub_. If you have questions, suggestions, etc. feel free to send me
an e-mail at `peter@peterodding.com`_.

License
-------

This software is licensed under the `MIT license`_.

© 2017 Peter Odding.

.. External references:

.. _crypto-drive-manager: https://pypi.python.org/pypi/crypto-drive-manager
.. _debuntu-tools: https://pypi.python.org/pypi/debuntu-tools
.. _GitHub: https://github.com/xolox/python-linux-utils
.. _Linux: https://en.wikipedia.org/wiki/Linux
.. _MIT license: http://en.wikipedia.org/wiki/MIT_License
.. _per user site-packages directory: https://www.python.org/dev/peps/pep-0370/
.. _peter@peterodding.com: peter@peterodding.com
.. _PyPI: https://pypi.python.org/pypi/linux-utils
.. _Python Package Index: https://pypi.python.org/pypi/linux-utils
.. _Python: https://www.python.org/
.. _Read the Docs: https://linux-utils.readthedocs.org
.. _rsync-system-backup: https://pypi.python.org/pypi/rsync-system-backup
.. _virtual environments: http://docs.python-guide.org/en/latest/dev/virtualenvs/
