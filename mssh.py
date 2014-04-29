#!/usr/bin/env python2.7

import sys
import os
import gevent
import commands
import getopt
import subprocess
from gevent.queue import Queue
import fcntl


tasks = Queue()

def worker(cmd):
    while not tasks.empty():
        host = tasks.get_nowait()
        p = subprocess.Popen('/usr/bin/ssh -p 26387 root@%s -o StrictHostKeyChecking=no -o ConnectTimeout=2 %s' % (host, cmd), shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        gevent.sleep(0)
        p.wait()
        print host
        print >>sys.stdout, p.stdout.read()
        print >>sys.stderr, p.stderr.read()

def master(hosts, cmd, num):
    for host in hosts:
            tasks.put_nowait(host)

def run(hosts, cmd, num):
    gevent.spawn(master, hosts, cmd, num).join()
    gevent.joinall([ gevent.spawn(worker, cmd) for n in xrange(num) ])

def main():
    usage = '''usage: %s -h "10.73.48.26 10.73.48.28 ..."|ip.txt -c 'ls -l' [-n 2]''' % os.path.basename(sys.argv[0])
    if len(sys.argv) == 1:
        print usage
        sys.exit(0)
    try:
        opts, args = getopt.getopt(sys.argv[1:], "h:c:n:", ["host=", "cmd=", "num="])
    except getopt.GetoptError:
        print usage
        sys.exit(1)
    hosts = cmd = ''
    num = 1
    for opt, val in opts:
        if opt == "-h" or opt == "--host":
            hosts = val
        elif opt == "-c" or opt == "--cmd":
            cmd = val
        elif opt == "-n" or opt == "--num":
            num = int(val)

    if hosts:
        if not os.path.isfile(hosts):
            hosts = hosts.strip().split(' ')
        else:
            with open(hosts, "r") as fp:
                hosts = [ host.strip() for host in fp.readlines() if host.strip() ]
    else:
        try:
            hosts = [ host.strip() for host in sys.stdin.xreadlines() if host.strip() ]
        except:
            pass

    run(hosts, cmd, num)


if __name__ == "__main__":
    main()
