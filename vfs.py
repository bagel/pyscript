#!/usr/bin/python

import sys
import os
import urllib2
import httplib
import re
import threading


uris = sys.argv[1]
cache = sys.argv[2]
ip = uris.split('_')[1]

def get_hosts():
    f = open('squidcheck.conf', 'r')
    hosts = []
    line = f.readline()
    while line:
        if re.match(ip, line):
            hosts.append(line.strip().split(':'))
        line = f.readline()
    return hosts

def request(uri, host, filename):
    url = cache + uri
    try:
        conn = httplib.HTTPConnection(host[0], int(host[1]), timeout=10)
        conn.request("GET", url)
        req = conn.getresponse()
    except:
        return 0
    f = open(filename, 'w')
    f.write(req.read())


def main():
    hosts = get_hosts()
    f = open(uris, 'r')
    line = f.readline()
    threads = []
    while line:
        uri = line.strip()
        filename = uri.strip('/nd/dataent')
        pathname = os.path.dirname(filename)
        if os.path.exists(filename):
            line = f.readline()
            continue
        if not os.path.exists(pathname):
            os.makedirs(pathname)
        for host in hosts:
            threads.append(threading.Thread(target=request, args=(uri, host, filename)))
        if len(threads) > 1000:
            for t in threads:
                t.start()
            for t in threads:
                t.join()
            threads = []

        line = f.readline()


if __name__ == "__main__":
    main()
