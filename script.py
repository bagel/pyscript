#!/usr/bin/env python

import sys
import os
import re
import cStringIO


def find(line, str):
    s_str = str
    e_str = str[1] + '}'
    start = line.find(s_str)
    end = line.find(e_str)
    return (start, end)

def value(line, val):
    start, end = find(line, '{$')
    key = line[start+2:end].strip()
    line_new = line.replace(line[start:end+2], str(val[key]))
    return line_new

def script(f, Tdict):
    fp = cStringIO.StringIO()
    f.seek(0)
    line = f.readline()
    indent = line.find(line.strip()[0])
    while line:
        if re.match('\s+$', line[:indent]):
            line = line[indent:]
        if line.strip().split(' ')[0] == 'echo':
            line = line.replace('echo', 'res +=')
        fp.write(line)
        line = f.readline()
    fp.seek(0)
    res = str()
    exec_str = ''.join(fp.readlines())
    exec(exec_str)
    return res

def response(temp, val):
    fp = open(temp, 'r')
    line = fp.readline()
    response_body = str()
    while line:
        if re.search('{\$.*\$}', line):
            line = value(line, val)
            continue
        if re.match('<script\s+type\s*=\s*"\s*text/python\s*"\s*>', line):
            fb = cStringIO.StringIO()
            line = fp.readline()
            while line:
                if re.match('</script>', line):
                    response_body += script(fb, val)
                    line = fp.readline()
                    break
                fb.write(line)
                line = fp.readline()
            continue
        response_body += line
        line = fp.readline()
    return response_body


if __name__ == '__main__':
    print response('../wsgi/test/template/test.html', {'val': 'hello', 'n': 20})
