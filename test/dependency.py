try:
    # noinspection PyUnresolvedReferences
    import ms.version
except ImportError:
    pass
else:
    ms.version.addpkg('mock', '1.0.1')
    ms.version.addpkg('setuptools', '0.6c11')
    ms.version.addpkg('protobuf', '3.6.1')
    ms.version.addpkg('zope.interface', '4.5.0')
    ms.version.addpkg('twisted', '12.0.0')
    ms.version.addpkg('coverage', '3.6')
    ms.version.addpkg('ipaddress', '1.0.6')
    ms.version.addpkg('mako', '0.7.2')
    ms.version.addpkg('cdb', '0.34')
    ms.version.addpkg('six', '1.9.0')
    ms.version.addpkg('jsonschema', '2.3.0')
    ms.version.addpkg('sqlalchemy', '1.0.11')
    ms.version.addpkg('cx_Oracle', '5.1-11.2.0.1.0')
    ms.version.addpkg('psycopg2', '2.5-9.2.4')
    ms.version.addpkg('ms.modulecmd', '1.0.4')
    ms.version.addpkg('dateutil', '1.5')
    ms.version.addpkg('cdb', '0.34')
