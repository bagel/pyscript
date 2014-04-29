#!/usr/bin/env python

import sys
import os
import time
import re
import subprocess
import threading
import commands
import cStringIO
import traceback

sys.path.append('/etc/dAppCluster')
from dpool_lib2 import *

sys.path.append(os.path.dirname(os.path.realpath(__file__)))
import cgroupctl

class Control:
    def __init__(self):
        self.role = get_role().lower()
        self.sinasrvdir = "/usr/local/sinasrv2"
        self.fpmbin = os.path.join(self.sinasrvdir, "sbin/php-fpm")
        self.fpmetcdir = os.path.join(self.sinasrvdir, "etc/web3")
        self.cgroupdir = os.path.join("/cgroup/dpool", self.role)
        self.nginxlock = "/var/lock/subsys/nginx"
        self.lockfile = "/var/lock/subsys/fpmctl"

    def startDomain(self, domain):
        masterProcess = self.masterCheck(domain)
        if masterProcess:
            print "%s (pid %s) already running" % (domain, masterProcess)
            return 1
        cgroupctl.Control().createDomain(domain)
        cgroupctl.Control().updateDomain(domain)
        fork = os.fork()
        if fork == 0:
            os.chdir(self.sinasrvdir)
            with open(os.path.join(self.cgroupdir, domain, "tasks"), 'a+') as fp:
                fp.write("%s\n" % os.getpid())
            os.system("%s -p %s -y %s" % (self.fpmbin, os.path.join(self.fpmetcdir, domain), os.path.join(self.fpmetcdir, domain, "php-fpm.conf")))
            sys.exit(0)
        else:
            os.wait()

    def stopDomain(self, domain):
        #if self.syntaxCheck(domain) != 0:
        #    print "%s syntax error" % domain
        #    sys.exit(2)
        Processes = self.masterCheck(domain).split(' ') + self.workerCheck(domain).split(' ')
        Processes = [ int(p) for p in Processes if p.isdigit() ]
        if not Processes:
            print "%s not start" % domain
            return 0
        for process in Processes:
            try:
                os.kill(process, 9)
            except:
                pass
        #cgroupctl.Control().deleteDomain(domain)

    def killDomain(self, domain):
        Processes = self.masterCheck(domain).split(' ') + self.workerCheck(domain).split(' ')
        Processes = [ int(p) for p in Processes if p.isdigit() ]
        for process in Processes:
            try:
                os.kill(process, 9)
            except:
                pass

    def statusDomain(self, domain):
        masterProcess = self.masterCheck(domain)
        if not masterProcess:
            print "%s not start" % domain
            return 1
        print "%s (pid %s) running" % (domain, masterProcess)

    def restartDomain(self, domain):
        self.stopDomain(domain)
        time.sleep(3)
        self.startDomain(domain)

    def syntaxCheck(self, domain):
        p = subprocess.Popen("%s -p %s -y %s -t" % (self.fpmbin, os.path.join(self.fpmetcdir, domain), os.path.join(self.fpmetcdir, domain, "php-fpm.conf")), shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        code = p.wait()
        if code != 0:
            print p.stderr.read(),
        return code

    def syntaxAll(self):
        domains = self.getDomain()
        code = 0
        for domain in domains:
            code = self.syntaxCheck(domain)
            if code != 0:
                sys.exit(code)

    def masterCheck(self, domain):
        cmd = 'php-fpm: master process (%s/php-fpm.conf)' % os.path.join(self.fpmetcdir, domain)
        return commands.getoutput('pidof "%s"' % cmd)

    def workerCheck(self, domain):
        cmd = 'php-fpm: pool %s' % domain
        return commands.getoutput('pidof "%s"' % cmd)

    def getDomain(self):
        return os.listdir(self.fpmetcdir)

    def startNginx(self):
        if not os.path.exists(self.nginxlock):
            p = subprocess.Popen('/etc/init.d/nginx start', shell=True, stdout=subprocess.PIPE)
            p.wait()

    def stopNginx(self):
        if os.path.exists(self.nginxlock):
            p = subprocess.Popen('/etc/init.d/nginx stop', shell=True, stdout=subprocess.PIPE)
            p.wait()

    def startAll(self):
        cgroupctl.Control().startCgroup()
        time.sleep(0.5)
        cgroupctl.Control().startCgroup()
        domains = self.getDomain()
        for domain in domains:
            self.startDomain(domain)
        self.startNginx()

    def stopAll(self):
        self.stopNginx()
        domains = self.getDomain()
        for domain in domains:
            self.stopDomain(domain)
        cgroupctl.Control().stopCgroup()

    def killAll(self):
        self.stopNginx()
        domains = self.getDomain()
        for domain in domains:
            self.killDomain(domain)
        cgroupctl.Control().stopCgroup()

    def statusAll(self):
        domains = self.getDomain()
        for domain in domains:
            self.statusDomain(domain)

    def restartAll(self):
        self.checkLock()
        self.stopAll()
        time.sleep(3)
        self.startAll()
        self.deleteLock()
        sys.exit(0)

    def checkLock(self):
        if os.path.exists(self.lockfile):
            if time.time() - os.stat(self.lockfile).st_mtime > 10:
                self.deleteLock()
            else:
                sys.exit(0)
        fp = open(self.lockfile, "w")
        fp.close()

    def deleteLock(self):
        os.remove(self.lockfile)


def main():
    usage = "%s start|stop|restart|status|kill|syntax [domain]" % sys.argv[0]
    if len(sys.argv) == 1 or sys.argv[1] == '-h' or sys.argv[1] == '--help':
        print usage
        sys.exit(0)

    if len(sys.argv) == 2:
        if sys.argv[1] == "start":
            Control().startAll()
        elif sys.argv[1] == "stop":
            Control().stopAll()
        elif sys.argv[1] == "status":
            Control().statusAll()
        elif sys.argv[1] == "restart":
            Control().restartAll()
        elif sys.argv[1] == "kill":
            Control().killAll()
        elif sys.argv[1] == "syntax":
            Control().syntaxAll()
    elif len(sys.argv) == 3:
        if sys.argv[1] == "start":
            Control().startDoamin(sys.argv[2])
        elif sys.argv[1] == "stop":
            Control().stopDomain(sys.argv[2])
        elif sys.argv[1] == "status":
            Control().statusDomain(sys.argv[2])
        elif sys.argv[1] == "restart":
            Control().restartDomain(sys.argv[2])
        elif sys.argv[1] == "kill":
            Control().killDomain(sys.argv[2])
        elif sys.argv[1] == "syntax":
            Control().syntaxCheck(sys.argv[2])


if __name__ == "__main__":
    main()
