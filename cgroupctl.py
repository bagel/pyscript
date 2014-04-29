#!/usr/bin/env python

import sys
import os
import ConfigParser
import commands
import re
import subprocess

sys.path.append('/etc/dAppCluster')
from dpool_lib2 import *

class Control:
    def __init__(self):
        self.role = get_role().lower()
        self.controllers = 'cpu,memory,net_cls,cpuacct,freezer'
        self.cghomedir = '/cgroup/dpool'
        self.fpmetcdir = '/usr/local/sinasrv2/etc/web3'

    def createRole(self):
        if os.path.exists(os.path.join(self.cghomedir, self.role, 'tasks')):
            print 'cgroup %s exists' % self.role
            return 1
        os.system('cgcreate -g %s:/%s' % (self.controllers, self.role))

    def deleteRole(self):
        if not os.path.exists(os.path.join(self.cghomedir, self.role, 'tasks')):
            print 'cgroup %s not exists' % self.role
            return 1
        os.system('cgdelete %s:/%s' % (self.controllers, self.role))

    def createDomain(self, domain):
        if os.path.exists(os.path.join(self.cghomedir, self.role, domain, 'tasks')):
            #print 'cgroup %s exists' % domain
            return 1
        os.system('cgcreate -g %s:/%s/%s' % (self.controllers, self.role, domain))

    def deleteDomain(self, domain):
        if not os.path.exists(os.path.join(self.cghomedir, self.role, domain, 'tasks')):
            #print 'cgroup %s not exists' % domain
            return 1
        os.system('cgdelete %s:/%s/%s' % (self.controllers, self.role, domain))

    def updateDomain(self, domain):
        limitsconf = "/etc/dAppCluster/confs/cgroup_limits.conf"
        cgroupdir = os.path.join('/cgroup/dpool', self.role, domain)
        config = ConfigParser.ConfigParser()
        config.read(limitsconf)
        if not config.has_section(domain):
            return 1
        with open(os.path.join(cgroupdir, "memory.limit_in_bytes"), 'w') as fp:
            fp.write(config.get(domain, "memory.limit_in_bytes"))
        for k, v in config.items(domain):
            if k == "memory.limit_in_bytes":
                continue
            with open(os.path.join(cgroupdir, k), 'w') as f:
                f.write(v)

    def getDomain(self):
        return os.listdir(self.fpmetcdir)

    def createAll(self):
        domains = self.getDomain()
        self.createRole()
        for domain in domains:
            self.createDomain(domain)

    def deleteAll(self):
        domains = self.getDomain()
        for domain in domains:
            self.deleteDomain(domain)
        self.deleteRole()

    def updateAll(self):
        domains = self.getDomain()
        for domain in domains:
            self.updateDomain(domain)

    def clearCgroup(self, dir):
        if not re.match('/cgroup', dir):
            return 0
        pids = commands.getoutput('lsof %s | awk "{print \$2}" | grep -v PID' % dir).strip().split('\n')
        if pids and pids[0]:
            for pid in pids:
                try:
                    os.kill(int(pid), 9)
                except:
                    pass

    def stopCgroup(self):
        self.clearCgroup('/cgroup')
        self.clearCgroup('/cgroup/dpool')
        p = subprocess.Popen('/etc/init.d/cgconfig stop', shell=True, stdout=subprocess.PIPE)
        return p.wait()

    def startCgroup(self):
        p = subprocess.Popen('/etc/init.d/cgconfig start', shell=True, stdout=subprocess.PIPE)
        return p.wait()

    def restartCgroup(self):
        self.stopCgroup()
        time.sleep(1)
        self.startCgroup()


def main():
    usage = '%s create|delete|update [domain]' % sys.argv[0]
    if len(sys.argv) == 1 or sys.argv[1] == '-h' or sys.argv[1] == '--help':
        print usage
        sys.exit(0)
    if len(sys.argv) == 2:
        if sys.argv[1] == 'create':
            Control().createAll()
        elif sys.argv[1] == 'delete':
            Control().deleteAll()
        elif sys.argv[1] == 'update':
            Control().updateAll()
        elif sys.argv[1] == 'stop':
            Control().stopCgroup()
        elif sys.argv[1] == 'start':
            Control().startCgroup()
        elif sys.argv[1] == 'restart':
            Control().restartCgroup()
    elif len(sys.argv) == 3:
        if sys.argv[1] == 'create':
            Control().createDomain(sys.argv[2])
        elif sys.argv[1] == 'delete':
            Control().deleteDomain(sys.argv[2])
        elif sys.argv[1] == 'update':
            Control().updateDomain(sys.argv[2])


if __name__ == "__main__":
    main()
