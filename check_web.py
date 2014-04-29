#!/usr/bin/env python

import sys
import os
import urllib2
import commands
import ConfigParser
import re
import time
import httplib
import json

sys.path.append('/etc/dAppCluster')
from dpool_lib2 import *

sys.path.append(os.path.dirname(os.path.realpath(__file__)))
import cgroupctl
import fpmctl


class Check:
    def __init__(self):
        self.role = get_role().lower()
        self.etcdir = '/usr/local/sinasrv2/etc'
        self.webdir = os.path.join(self.etcdir, 'web3')
        self.cgroupdir = os.path.join('/cgroup/dpool/', self.role)
        self.intip = get_intip()

    def poolChildren(self, domain):
        config = ConfigParser.ConfigParser()
        config.read(os.path.join(self.webdir, domain, "conf.d/%s.conf" % domain))
        max = min = 0
        pm = config.get(domain, 'pm')
        if pm == "static":
            max = min = int(config.get(domain, 'pm.max_children'))
        elif pm == "dynamic":
            max = int(config.get(domain, 'pm.max_spare_servers')) + 50
            min = int(config.get(domain, 'pm.min_spare_servers'))
        elif pm == "ondemand":
            max = 5
        return (min, max)

    def poolProcess(self, domain):
        p = commands.getoutput('pidof "php-fpm: pool %s"' % domain)
        if not p:
            return 0
        else:
            return len(p.strip().split(' '))

    def poolProcessCheck(self, domain):
        min, max = self.poolChildren(domain)
        now = self.poolProcess(domain)
        msg = ''
        print domain, min, now, max
        if now > max or now < min - 2:
            msg = '%s warn %d' % (domain, now)
        return msg

    def poolMasterCheck(self, domain):
        m = commands.getoutput('pidof "php-fpm: master process (%s/php-fpm.conf)"' % os.path.join(self.webdir, domain))
        msg = ''
        if not m:
            msg = '%s no master' % domain
        return msg

    def poolRequestCheck(self, domain):
        req = httplib.HTTPConnection('127.0.0.1', 80, timeout=3)
        try:
            req.request(method="GET", url="/system/dpool_check.php", headers={"Host": domain})
            code = req.getresponse().status
        except:
            code = 404
        msg = ''
        if code != 200 and code != 404:
            msg = '%s code %d' % (domain, code)
        return msg

    def poolCpuCheck(self, domain):
        tmpfile = '/tmp/check_web.%s.cpu' % domain
        cpufile = os.path.join(self.cgroupdir, domain, "cpu.stat")
        if not os.path.exists(cpufile):
            return "%s cpu not exsits" % domain
        cpuold = 0
        if os.path.exists(tmpfile):
            with open(tmpfile, 'r') as fp:
                cpuold = int(fp.read())
        with open(cpufile, "r") as fp:
            fp.readline()
            cpunew = int(re.sub(r'nr_throttled (\d+)\n', r'\1', fp.readline()))
        with open(tmpfile, 'w') as fp:
            fp.write(str(cpunew))
        msg = ''
        print cpunew, cpuold
        if cpunew - cpuold > 1000:
            msg = "%s cpu %d" % (domain, cpunew - cpuold)
        return msg

    def poolMemoryCheck(self, domain):
        tmpfile = '/tmp/check_web.%s.memory' % domain
        memfile = os.path.join(self.cgroupdir, domain, "memory.memsw.failcnt")
        if not os.path.exists(memfile):
            return "%s memory not exsits" % domain
        memoryold = 0
        if os.path.exists(tmpfile):
            with open(tmpfile, 'r') as fp:
                memoryold = int(fp.read())
        with open(memfile, 'r') as fp:
            memorynew = int(fp.read().strip())
        with open(tmpfile, 'w') as fp:
            fp.write(str(memorynew))
        msg = ''
        print memorynew, memoryold
        if memorynew - memoryold > 1000:
            msg = '%s memory %d' % (domain, memorynew - memoryold)
        return msg

    def nginxCheck(self):
        n = len([ p for p in commands.getoutput('pidof nginx').strip().split(' ') if p ])
        with open(os.path.join(self.etcdir, "nginx.conf"), "r") as fp:
            line = fp.readline()
            while line:
                if re.match('worker_processes', line):
                    m = int(re.sub(r'worker_processes\s+(\d+);\n', r'\1', line)) + 1
                line = fp.readline()
        msg = ''
        if n < m:
            msg = 'nginx warn %d' % n
        return msg

    def httpdCheck(self):
        pids = commands.getoutput('pidof /usr/local/sinasrv2/sbin/httpd').strip().split(' ')
        pids = [ p for p in pids if p ]
        n = len(pids)
        for pid in pids:
            try:
                os.kill(int(pid), 9)
            except:
                pass
        msg = ''
        if n > 0:
            msg = 'httpd kill %d' % n
        return msg

    def getDomain(self):
        domains = os.listdir(self.webdir)
        domains.remove('img.mix.sina.com.cn')
        return domains

    def sendMail(self, msg):
        msg = '<br>'.join([ m for m in msg.split('<br>') if m ])
        msg = '<br>%s<br>%s<br>%s<br>try to restart<br>' % (time.strftime('%Y/%m/%d %H:%M:%S'), self.intip, msg) 
        cmd = '/etc/dAppCluster/send_alert.pl --sv DPool --service web --object fpm_status --subject "fpm status" --content "%s" --mailto caoyu2,zhigang6 --html 1' % msg
        return os.system(cmd)

    def sendSms(self, msg):
        msg = msg.replace('<br>', '')
        wokfile = '/tmp/check_web.OK'
        wcrfile = '/tmp/check_web.CRIT'
        if msg and not os.path.exists(wcrfile):
            msg = 'CRIT'
            fp = open(wcrfile, 'w')
            fp.close()
            os.remove(wokfile)
        elif not msg and not os.path.exists(wokfile):
            msg = 'OK'
            fp = open(wokfile, 'w')
            fp.close()
            os.remove(wcrfile)
        else:
            return 0
        msg = '%s %s' % (msg, time.strftime('%m/%d %H:%M'))
        cmd = '/etc/dAppCluster/send_alert.pl -sv DPool --service fpm --object %s --subject "%s" --msgto caoyu2,zhigang6' % (self.intip, msg)
        return os.system(cmd)

    def sendTalk(self, msg):
        msg = '\n'.join([ s for s in msg.split('<br>') if s])
        msg = 'cgroup: %s\n%s\n%s\n' % (time.strftime('%Y/%m/%d %H:%M:%S'), self.intip, msg)
        data = {"to": ["freetgm@gmail.com", "liuzgchn@gmail.com"], "msg": msg}
        req = urllib2.Request(url='http://10.210.215.69/pybot/send')
        req.add_data(json.JSONEncoder().encode(data))
        return urllib2.urlopen(req).read()

    def allRestart(self):
        return fpmctl.Control().restartAll()

    def allCheck(self):
        msg = sms = ""
        msg += '<br>' + self.httpdCheck()
        domains = self.getDomain()
        for domain in domains:
            msg += '<br>'.join([self.poolProcessCheck(domain), self.poolMasterCheck(domain), self.poolRequestCheck(domain), self.poolCpuCheck(domain), self.poolMemoryCheck(domain)])
            msg += '<br>'
        msg += '<br>' + self.nginxCheck()
        if os.path.exists('/var/lock/subsys/fpmctl') and msg.replace('<br>', ''):
            self.allRestart()
            sys.exit(0)
        self.sendSms(msg)
        if msg.replace('<br>', ''):
            self.sendMail(msg)
            self.sendTalk(msg)
            self.allRestart()


if __name__ == "__main__":
    Check().allCheck()
