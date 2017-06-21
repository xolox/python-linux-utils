#!/bin/bash -e

# Install the required Python packages.
pip install pip-accel
pip-accel install coveralls
pip-accel install --requirement=requirements.txt
pip-accel install --requirement=requirements-checks.txt
pip-accel install --requirement=requirements-tests.txt

# Install the project itself, making sure that potential character encoding
# and/or decoding errors in the setup script are caught as soon as possible.
LC_ALL=C pip-accel install .

# Let apt-get, dpkg and related tools know that we want the following
# commands to be 100% automated (no interactive prompts).
export DEBIAN_FRONTEND=noninteractive

# Update apt-get's package lists.
sudo -E apt-get update -qq

# Use apt-get to install cryptdisks_start, cryptdisks_stop, cryptsetup,
# mkfs.ext4 and rsync.
sudo -E apt-get install --yes cryptsetup cryptsetup-bin

if [ "$TRAVIS" != true ]; then
  cat >&2 << EOF

    Error: I'm refusing to touch /etc/fstab and /etc/crypttab because this
    shell script was written specifically for Travis CI where each build
    starts from a clean virtual machine image or snapshot!

    If you really know what you're getting yourself into you can set the
    environment variable TRAVIS=true to bypass this sanity check ...

EOF
  exit 1
fi

# Append our crypto device to /etc/crypttab.
sudo tee -a /etc/crypttab >/dev/null << EOF
linux-utils /tmp/linux-utils.img /tmp/linux-utils.key luks,noauto
EOF
