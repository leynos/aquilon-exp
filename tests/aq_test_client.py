import logging
import os
import re
import sys
from subprocess import Popen, PIPE

from google.protobuf.message import DecodeError
from aquilon.config import Config

LOGGER = logging.getLogger(__name__)

class AqTestClient():

    msversion_dev_re = re.compile(r'WARNING:msversion:Loading \S* from dev\n')
    config = Config()

    def runcommand(self, command, auth=True, **kwargs):
        aq = os.path.join(self.config.get("broker", "srcdir"), "../install/common/bin", "aq")
        if auth:
            port = self.config.get("broker", "kncport")
        else:
            port = self.config.get("broker", "openport")
        if isinstance(command, list):
            args = [str(cmd) for cmd in command]
        else:
            args = [command]
        args.insert(0, sys.executable)
        args.insert(1, aq)
        if "--aqport" not in args:
            args.append("--aqport")
            args.append(port)
        if auth:
            args.append("--aqservice")
            args.append(self.config.get("broker", "service"))
        else:
            args.append("--noauth")
        if "env" in kwargs:
            # Make sure that kerberos tickets are still present if the
            # environment is being overridden...
            env = {}
            for (key, value) in list(kwargs["env"].items()):
                env[key] = value
            for (key, value) in list(os.environ.items()):
                if key.find("KRB") == 0 and key not in env:
                    env[key] = value
            if 'USER' not in env:
                env['USER'] = os.environ.get('USER', '')
            kwargs["env"] = env

        LOGGER.debug("Running command {}".format(args))
        p = Popen(args, stdout=PIPE, stderr=PIPE, text=False, **kwargs)
        out, err = p.communicate()
        if err:
            LOGGER.debug(err)
        err = self.msversion_dev_re.sub('', err.decode())

        # Lock messages are pretty common...
        err = err.replace('Client status messages disabled, retries exceeded.\n', '')

        try:
            return p, out.decode(), err
        except (DecodeError, UnicodeDecodeError):
            return p, out.decode("ISO-8859-1"), err
        except Exception as e:
            return p, str(out), err



