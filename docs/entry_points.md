# Entry Points

This document summarizes the top-level scripts that start the main components of the Aquilon system.

## Client commands

- `bin/aq.py` – command line client for communicating with the broker. It uses Kerberos by default and
  exposes many subcommands defined under `etc/input.xml`.
- `bin/aq_compile.py` – helper used mainly in testing to compile templates without running the broker.
- `bin/aqd_config.py` – reads `aqd.conf` and prints configuration values in various formats.

## Broker and utilities

- `sbin/aqd.py` – Twisted application that starts the broker daemon.
- `sbin/aq_notifyd.py` – notification daemon that processes events from the broker.
- `sbin/aqd_consistency_check.py` – runs database consistency checks.
- `sbin/aqdb_shell.py` – launches an interactive shell against the Aquilon database.
- `sbin/aqdb_migrate.py` – copies the database contents to another backend engine.
- `sbin/aqdb_set_role.py` – grants roles to database users.

Several one-off upgrade scripts under `upgrade/` also contain a `__main__` block so they can be executed
individually when migrating between versions.

Refer to `etc/README.dev` for examples of launching `aqd.py` and using the client.
