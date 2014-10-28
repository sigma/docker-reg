from __future__ import division, absolute_import
from __future__ import print_function, unicode_literals

import argparse
import json
import os
import signal
import subprocess
import time

import docker
import etcd

ETCD_HOST = os.environ.get('ETCD_PORT_10000_TCP_ADDR', 'localhost')
ETCD_PORT = os.environ.get('ETCD_PORT_10000_TCP_PORT', '4001')


class Register(object):

    def __init__(self, container, port, service, **rest):
        self._container = container
        self._port = port
        self._service = service
        self._rest = {}
        for k, v in rest.items():
            try:
                v = int(v)
            except:
                pass
            self._rest[k] = v

        self._configureSignal()
        self._etcd = etcd.Client(host=ETCD_HOST, port=int(ETCD_PORT))
        self._docker = docker.Client(base_url='unix://var/run/docker.sock')

    def handler(self, signum, frame):
        key = self._getKey()
        self._etcd.delete(key)

    def _configureSignal(self):
        for sig in [signal.SIGHUP, signal.SIGINT, signal.SIGTERM]:
            signal.signal(sig, self.handler)

    def _getKey(self):
        return "/services/%s/%s" % (self._service, self._container)
            
    def setKey(self):
        try:
            port_props = self._docker.port("ipxe.service", self._port)[0]
            host, port = port_props['HostIp'], port_props['HostPort']
            obj = {'host': host, 'port': int(port)}
            obj.update(self._rest)

            json_obj = json.dumps(obj)
            self._etcd.write(self._getKey(), json_obj, ttl=5)
        except:
            print("Failed to set key %s" % (self._getKey()))


def getParser():
    parser = argparse.ArgumentParser()
    parser.add_argument("container")
    parser.add_argument("port")
    parser.add_argument("service")
    parser.add_argument("rest", nargs='*')
    return parser

    
def main(args):
    rest = {}
    for val in args.rest:
        k, v = val.split('=')
        rest[k] = v

    reg = Register(args.container, args.port, args.service, **rest)
    while True:
        reg.setKey()
        time.sleep(1)

if __name__ == '__main__':
    parser = getParser()
    args = parser.parse_args()
    main(args)
