#!/usr/bin/env python
#coding: utf-8

import sys
import os
import redis
import urllib2
import json
import time
import smtplib
import re
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.header import Header


class AutoMail:
    def __init__(self):
        self.r = redis.StrictRedis('10.13.32.21', 6380)
        self.r_info = redis.StrictRedis('10.13.32.21', 6379)
        self.dptitle = '【动态平台自动报警】'
        self.montitle = '【动态平台自动监控】'

    def topHits(self, day):
        data = json.loads(urllib2.urlopen('http://admin.dpool.cluster.sina.com.cn/status/sum?time=%s' % day).read()).items()
        data_new = []
        for k, v in data:
            for kn, vn in data_new:
                if int(v) >= int(vn):
                    data_new.insert(data_new.index((kn, vn)), (k, v))
                    break
            if (k, v) not in data_new:
                data_new.append((k, v))
        return data_new[:100]
    
    def topYestoday(self):
        day = time.strftime("%Y%m%d" , time.localtime(time.time() - 86400))
        return topHits(day)
    
    def domainMail(self, domain, fmin, to, cc):
        title = '%s 访问出现5xx错误' % domain
        subject = self.dptitle + title
        keys = self.r.keys('%s_%s_*' % (domain, str(fmin)))
        msg = '动态平台自动报警邮件, 你所负责的项目有报警，请及时修复.<br><br>%s<br><br>在最近5分钟内 ' % title
        code_msg = []
        n = 0
        for key in keys:
            code = key.split('_')[-1]
            count = self.r.get(key)
            self.r.delete(key)
            code_msg.append('%s错共%s次' % (code, count))
        msg += ', '.join(code_msg)
        msg += '<br><br>访问日志'
        lens = len(msg)
        logs = json.loads(urllib2.urlopen(url='http://admin.dpool.cluster.sina.com.cn/mon/accesslog?domain=%s&num=10&user=caoyu2&key=49eff4f43a196f69108504030222fdad' % domain).read())
        for line in logs:
            line = line.encode('utf-8').split(' ')[:-2]
            if int(line[0]) < fmin:
                continue
            msg += '<br>'
            line[0] = time.strftime('%Y/%m/%d %H:%M:%S', time.localtime(int(line[0])))
            msg += ' '.join(line)
        if len(msg) == lens:
            n = 1
            msg += '<br>null'
        msg += '<br><br>'
        msg += '错误日志'
        lens = len(msg)
        logs = json.loads(urllib2.urlopen(url='http://admin.dpool.cluster.sina.com.cn/mon/errorlog?domain=%s&num=10&user=caoyu2&key=49eff4f43a196f69108504030222fdad' % domain).read())
        for line in logs:
            line = line.encode('utf-8').split(' ')[1:]
            if int(line[0]) < fmin:
                continue
            msg += '<br>'
            line[0] = time.strftime('%Y/%m/%d %H:%M:%S', time.localtime(int(line[0])))
            msg += ' '.join(line)
        if len(msg) == lens:
            if n == 1:
                return 0
            msg += '<br>null'
        msg += '<br><br>更多日志及实时监控请访问 <a href="http://admin.dpool.cluster.sina.com.cn/mon?channel=%s">http://admin.dpool.cluster.sina.com.cn/mon?domain=%s</a>' % (domain, domain)
        self.mail(subject, msg, to, cc)

    def codeMail(self):
        t = int(time.time())
        fmin = t - t % 300 - 300
        keys = self.r.keys('*_%s_*' % str(fmin))
        to = ["caoyu2@staff.sina.com.cn"]
        cc = ["caoyu2@staff.sina.com.cn", "zhigang6@staff.sina.com.cn"]
        users = self.r_info.hgetall('info_user')
        domains = set()
        for key in keys:
            if int(self.r.get(key)) < 10:
                self.r.delete(key)
                continue
            domains.add(key.split('_')[0])
        for domain in domains:
            if not users.has_key(domain):
                for key in self.r.keys('_'.join([domain, '*'])):
                    self.r.delete(key)
                continue
            to = eval(users[domain])
            self.domainMail(domain, fmin, to, cc)
    

    def cardLog(self):
        subject = "%s %s日card池访问统计" % (self.montitle, time.strftime("%Y-%m-%d", time.localtime(time.time() - 86400)))
        to = ["lilin6@staff.sina.com.cn", "zehua2@staff.sina.com.cn", "sunqi2@staff.sina.com.cn", "chenhao5@staff.sina.com.cn"]
        #to = ["caoyu2@staff.sina.com.cn"]
        cc = ["caoyu2@staff.sina.com.cn", "jingwei5@staff.sina.com.cn"]
        #cc = []
        msg = ""
        day = time.strftime("%Y%m%d", time.localtime(time.time() - 86400))
        f = open("%s.cnt" % day, "r")
        f_i = open('uri.info', 'r')
        line = f.readline()
        line_i = f_i.readline()
        while line:
            uri, info = line_i.strip().split(' ')
            uri, cnt = line.strip().split(' ')
            msg += '<tr><td style="border-right: 1px solid #ddd; border-bottom: 1px solid #ddd; padding: 10px">%s</td><td style="border-right: 1px solid #ddd; border-bottom: 1px solid #ddd; padding: 10px">%s</td><td style="border-right: 1px solid #ddd; border-bottom: 1px solid #ddd; padding: 10px">%s</td></tr>' % (info, uri, cnt)
            line = f.readline()
            line_i = f_i.readline()

        message = '''card池每天访问hits统计
<br>
<br>
<table style="border-top: 1px solid #ddd; border-left: 1px solid #ddd; border-spacing: 0;">
<thead>
    <tr style="font-size: 16px">
        <th style="border-right: 1px solid #ddd; border-bottom: 1px solid #ddd; padding: 10px">info</th>
        <th style="border-right: 1px solid #ddd; border-bottom: 1px solid #ddd; padding: 10px">uri</th>
        <th style="border-right: 1px solid #ddd; border-bottom: 1px solid #ddd; padding: 10px">hits(day)</th>
    </tr>
</thead>
<tbody>
%s
</tbody>
</table>
''' % msg
        self.mail(subject, message, to, cc)

    def articleLog(self):
        subject = "%s %s日article访问统计" % (self.montitle, time.strftime("%Y-%m-%d", time.localtime(time.time() - 86400)))
        to = ["junjie4@staff.sina.com.cn", "jiantao1@staff.sina.com.cn", "wangchao7@staff.sina.com.cn"]
        #to = ["caoyu2@staff.sina.com.cn"]
        cc = ["caoyu2@staff.sina.com.cn", "jingwei5@staff.sina.com.cn"]
        #cc = []
        day = time.strftime("%Y%m%d", time.localtime(time.time() - 86400))
        f = open("%s.article.cnt" % day, "r")
        line = f.readline()
        t0 = 0
        uri = ''
        msgs = []
        msg = ''
        while line:
            if re.match('/longtext/', line):
                if msg and uri:
                    msgs.append([uri, msg])
                    msg = ''
                    t0 = 0
                uri = line.strip()
                line = f.readline()
            t, cnt = line.strip().split(' ')
            if t != "1000":
                msg_t = "%s<=time<%s" % (t0, t)
            else:
                msg_t = "time>=%s" % t0
            t0 = t
            msg += '<tr><td style="border-right: 1px solid #ddd; border-bottom: 1px solid #ddd; padding: 10px">%s</td><td style="border-right: 1px solid #ddd; border-bottom: 1px solid #ddd; padding: 10px">%s</td></tr>' % (msg_t, cnt)
            line = f.readline()
        if msg and uri:
            msgs.append([uri, msg])

        message = 'article每天访问统计<br><br>'
        for m in msgs:
            message += '''
<table style="border-top: 1px solid #ddd; border-left: 1px solid #ddd; border-spacing: 0;">
<thead>
    <tr style="font-size: 16px">
        <th style="border-right: 1px solid #ddd; border-bottom: 1px solid #ddd; padding: 10px">%s(s)</th>
        <th style="border-right: 1px solid #ddd; border-bottom: 1px solid #ddd; padding: 10px">hits(day)</th>
    </tr>
</thead>
<tbody>
%s
</tbody>
</table>
<br>
<br>
''' % (m[0], m[1])
        self.mail(subject, message, to, cc)
    
    def mail(self, subject, message, to, cc):
        fr = "dpool_auto@staff.sina.com.cn"
        
        msg = MIMEMultipart('alternative')
        msg['Subject'] = Header(subject, 'utf-8')
        msg['From'] = fr
        msg['To'] = ','.join(to)
        msg['CC'] = ','.join(cc)
    
        html = '''
<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
<html xmlns="http://www.w3.org/1999/xhtml">
<head>
    <meta http-equiv="Content-Type" content="text/html; charset=UTF-8" />
    <title>DPool auto alert</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0"/>
</head>

<body>
%s
<br>
<br>
<hr width="100%%", size=1>
请不要直接回复此邮件，如有问题请联系caoyu2 5405.
</body>
</html>
''' % message
    
        msg.attach(MIMEText(html, 'html', 'utf-8'))
    
        s = smtplib.SMTP('localhost')
        s.sendmail(fr, to + cc, msg.as_string())
        s.quit()


if __name__ == "__main__":
    am = AutoMail()
    #am.codeMail()
    am.cardLog()
    am.articleLog()
