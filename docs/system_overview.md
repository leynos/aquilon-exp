# System Overview

This document describes Aquilon's major components and how they fit together.

## Core components

Aquilon requires three core pieces of infrastructure in order to manage a host:

1. **Database** – provides the Aquilon data model. The Primer notes that this
   database is currently Oracle but other databases are possible.
2. **Broker** – accepts user requests and combines database information with
   configuration policy to generate host profiles.
3. **Data warehouse** – exports realized views of the data model so they can be
   consumed easily at scale.

The database, broker and data warehouse may run centrally while bootservers are
located close to managed hosts. Multiple boot servers are typically deployed in
all data centers while a single database and broker operate centrally.

## Technologies

- The broker daemon (`aqd`) is a Twisted application written in Python.
- Data is stored in a relational database accessed via SQLAlchemy.
- Client commands use Kerberos for authentication and manage template changes
  in Git sandboxes.
- Notification services are implemented with a separate daemon
  (`aq_notifyd.py`).

## Domain Concepts

Aquilon terminology includes:

- **Archetype** – grouping of hosts that defines the build process and
  available templates.
- **Cluster** – collection of hosts built using a different schema than
  individual hosts.
- **Domain** – branch of shared Quattor templates used to configure
  entities.
- **Feature** – reusable snippet of configuration, similar to a recipe.
- **Personality** – describes the services a host requires but not the
  specific instance.
- **Sandbox** – development area for editing PAN templates.
- **Service** – network-based service with clients and servers such as DNS
  or DHCP.

