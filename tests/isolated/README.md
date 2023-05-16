# Running the isolated tests

These tests are designed to run as isolated units, each starting an AQ broker with a copy of a database in a known state.

This is an evolution of the unit tests under tests/broker which are linked and run against a single database, but are inheritently brittle if one test injects unexpected data into the database (perhaps through adding or modifying a test mid-way through the sequence), which then causes later tests to fail. To run the isolated tests:

`train test -t isolated`

## Running individual tests

To run individual tests:

```
export AQDCONF=tests/unittest.conf
python tests/isolated/test_add_interface_address.py TestAddInterfaceAddress.test_300_add_address_ipfromip_success
```

Or to run all tests using unittest:

```
python -m unittest discover -s tests/isolated
```

# Connecting to an isolated database

The easiest way is to add the following to your test:

import pdb
pdb.set_trace()

and using the aq command to connect to the local broker:

aq status --aqport 6902 --aqservice $USER


# Setting up yourself as aqd_admin

Most of the AQ commands excercised by the test requires aqd_admin role. This can be configured by running the following command.

```commandline
/ms/dist/aquilon/PROJ/aqd/$AQVER/sbin/aqdb_set_role --debug --role aqd_admin
```