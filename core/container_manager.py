#!/usr/bin/env python
# -*- coding:utf-8 -*

from flask import Flask, request, render_template, Response
from time import localtime, time, strftime
from json import loads, dumps
import commands

__author__ = 'ckcz123'
__email__ = 'ckcz123@126.com'

MANAGER = '-H tcp://0.0.0.0:9950'
TOKEN = 'b8f7a273ad509ae2cab79e58e19aa392'
DOMAINS = ['123.57.2.1', '123.57.145.224', '182.92.236.173']
DOMAIN = '123.57.2.1' # domain of runners
PORT = 9999 # port on the controller
VALID_TYPES = ['php', 'python', 'java', 'javaweb', 'javaweb-debug', 'javaweb-compile', 'javaweb-file', 'cpp'] # valid runner types

app = Flask(__name__)

def json_to_obj(json_str):
    try:
        obj = loads(json_str.replace("'", "\""))
    except Exception, e:
        return None
    else:
        return obj

def obj_to_json(obj):
    return dumps(obj)

def reply(code, msg):
    return obj_to_json({'code': code, 'msg': msg})

# get a valid port that is not used
def get_valid_port(start, end):
    global MANAGER
    for i in range(start, end):
        status, output = commands.getstatusoutput("docker %s ps -a | grep \":%d->\"" % (MANAGER, i))
        if status != 0:
            return i
    return -1
"""
def run(ptype, path, node=None, port=None, memory=None, overload=False):
    global MANAGER
    constraint=''
    if node is not None:
        constraint=" -e constraint:node_name==node%d" % (int(node))
    if port is None:
        port=get_valid_port(1001, 1999)
    else:
        port=int(port)

    sshport=get_valid_port(4001, 6000)
    debugport=get_valid_port(3001, 4000)

    memlimit=''
    if memory is not None:
        memlimit=" -m %dM" % (int(memory))
    if overload:
        commands.getstatusoutput("docker %s rm -f `docker %s ps | grep ':%d->' | awk '{print $1}'`" % (MANAGER, MANAGER, port))
    
    if ptype=='php':
        code, output=commands.getstatusoutput("docker %s run -id%s -p %d:80 -p %d:22 -v /root/data/repo/php%s:/var/www/html/%s pop2016/php" % (MANAGER, memlimit, port, sshport, path, constraint))
    elif ptype=='python':
        code, output=commands.getstatusoutput("docker %s run -id%s -p %d:80 -p %d:22 -v /root/data/repo/python%s:/home/%s pop2016/python" % (MANAGER, memlimit, port, sshport, path, constraint))
#    elif ptype=='javaweb':
 #       code, output=commands.getstatusoutput("docker %s run -id%s -p %d:8080 -p %d:22 -v /root/data/repo/javaweb%s:/usr/local/tomcat/webapps/ROOT/%s pop2016/tomcat" % (MANAGER, memlimit, port, sshport, path, constraint))
    elif ptype=='javaweb':
        code, output=commands.getstatusoutput("docker %s run -id%s -p %d:8080 -p %d:22 -p %d:8888 -v /root/data/repo/javaweb%s:/root/code/ -v /root/data/mvnrepo/repository/:/root/.m2/repository/%s -e COMPILE=1 pop2016/tomcat2" % (MANAGER, memlimit, port, sshport, debugport, path, constraint))
    elif ptype=='javaweb-debug':
        code, output=commands.getstatusoutput("docker %s run -id%s -p %d:8080 -p %d:22 -p %d:9000 -v /root/data/repo/javaweb%s:/usr/local/tomcat/webapps/ROOT/%s pop2016/tomcat-debug" % (MANAGER, memlimit, port, sshport, debugport, path, constraint)) 
    elif ptype=='cpp':
        code, output=commands.getstatusoutput("docker %s run -id%s -p %d:8888 -p %d:22 -v /root/data/repo/cpp%s:/root/code/%s pop2016/cpp" % (MANAGER, memlimit, port, sshport, path, constraint))
    else:
        return reply(2, "Invalid running type: %s" % (ptype))

    if code is 0:
        dockerid = output[0:12]
        code, output = commands.getstatusoutput("docker %s ps | grep %s" % (MANAGER, dockerid))
        for domain in DOMAINS:
            if domain in output:
                response = {'code': '0', 'domain': domain, 'port': "%d" % (port), 'sshport': "%d" % (sshport), 'dockerid': dockerid}
                if ptype=='javaweb-debug':
                    response['debugport']="%d" % (debugport)
                if ptype=='javaweb':
                    response['wsport']="%d" % (debugport)
                if ptype=='cpp':
                    response['wsport']="%d" % (port)
                    del response['port']
                return obj_to_json(response)
        return reply(6, "Unable to find the domain")
    else:
        return reply(5, output)
"""

def run(ptype, path, extra=False, node=None, port=None, memory=None, overload=False):
    global MANAGER
    constraint=''
    if node is not None:
        constraint=" -e constraint:node_name==node%d" % (int(node))
    if port is None:
        port=get_valid_port(1001, 1999)
    else:
        port=int(port)

    sshport=get_valid_port(4501, 6000)
    wsport=get_valid_port(3001, 4500)

    memlimit=''
#    if memory is not None:
#        memlimit=" -m %dM" % (int(memory))
    if overload:
        commands.getstatusoutput("docker %s rm -f `docker %s ps | grep ':%d->' | awk '{print $1}'`" % (MANAGER, MANAGER, port))
    
    if ptype not in VALID_TYPES:
        return reply(2, "Invalid running type: %s" % (ptype))

    constraint="%s -e MYSQL=1 -e TYPE=%s" % (constraint, ptype)
#    if ptype=='javaweb-debug' or ptype=='javaweb-compile':
#        path="javaweb/%s" % (path)
#    else:
#        path="%s/%s" % (ptype, path)
    path = ptype.split("-")[0] + path

    extra0=''
#    if ptype=='javaweb-debug':
#        extra0=' -v /root/data/service/javadebugger/:/usr/local/tomcat/webapps/ROOT/:ro '
#        extra0=' -v /root/data/service/javadebugger/:/tmp/tmp/ '
    if extra is not None:
        extra0 += ' -e EXTRA=%s ' % (extra)

    code, output=commands.getstatusoutput("docker %s run -id%s -p %d:80 -p %d:8888 -p %d:22 -v /root/data/repo/%s:/root/code/ -v /root/data/mvnrepo/repository/:/root/.m2/repository/ %s %s pop2016/runner" % (MANAGER, memlimit, port, wsport, sshport, path, extra0, constraint))

    if code is 0:
        dockerid = output[0:12]
        code, output = commands.getstatusoutput("docker %s ps | grep %s" % (MANAGER, dockerid))
        for domain in DOMAINS:
            if domain in output:
                response = {'code': '0', 'domain': domain, 'port': "%d" % (port), 'sshport': "%d" % (sshport), 'wsport': "%d" % (wsport), 'dockerid': dockerid}
                if ptype=='javaweb-debug':
                    response['debugport']="%d" % (wsport)
                    del response['wsport']
                return obj_to_json(response)
        return reply(6, "Unable to find the domain")
    else:
        return reply(5, output)

def delete(dockerid):
    global MANAGER
    status, output = commands.getstatusoutput("docker %s rm -f %s" % (MANAGER, dockerid.replace(',', ' ')))
    return reply(status, output)
"""
def startservice(ptype, path=None, node=None, port=None, memory=None, overload=False):
    global MANAGER
    if node is None:
        node=1
    constraint=" -e constraint:node_name==node%d" % (int(node))
    if port is None:
        port=get_valid_port(2001, 2999)
    else:
        port=int(port)
    memlimit=''
    if memory is not None:
        memlimit=" -m %dM" % (int(memory))

    sshport=get_valid_port(4001, 6000)

    if overload:
        commands.getstatusoutput("docker %s rm -f `docker %s ps | grep ':%d->' | awk '{print $1}'`" % (MANAGER, MANAGER, port))

    if ptype=='tomcat':
        code, output=commands.getstatusoutput("docker %s run -id%s -p %d:8080 -p %d:22 -v /root/data/repo/:/data/repo/ -v /root/data/template/:/data/template/ -v /root/data/share/:/data/share/ -v /root/data/completion/:/data/completion/ -v /root/data/mvnrepo/repository/:/root/.m2/repository/ -v /root/data/service%s:/usr/local/tomcat/webapps/ROOT/%s pop2016/tomcat-server" % (MANAGER, memlimit, port, sshport, path, constraint))
    elif ptype=='tomcat7':
        code, output=commands.getstatusoutput("docker %s run -id%s -p %d:8080 -p %d:22 -v /root/data/repo/:/data/repo/ -v /root/data/template/:/data/template/ -v /root/data/share/:/data/share/ -v /root/data/completion/:/data/completion/ -v /root/data/service%s:/usr/local/tomcat/webapps/ROOT/%s pop2016/tomcat7" % (MANAGER, memlimit, port, sshport, path, constraint))
    elif ptype=='gateone':
        code, output=commands.getstatusoutput("docker %s run -id%s -p %d:8000 -p %d:22%s pop2016/gateone" % (MANAGER, memlimit, port, sshport, constraint))
    elif ptype=='nginx':
        sshport=0
        code, output=commands.getstatusoutput("docker %s run -id%s -p %d:80 -v /root/data/nginx_conf%s:/etc/nginx/%s nginx" % (MANAGER, memlimit, port, path, constraint))
    else:
        code, output=commands.getstatusoutput("/bin/bash ../scripts/%s.sh" % (ptype))
    
    if code is 0:
        if ptype!='tomcat' and ptype!='gateone' and ptype!='nginx' and ptype!='tomcat7':
            return reply(0, "Success")
        dockerid = output[0:12]
        code, output = commands.getstatusoutput("docker %s ps | grep %s" % (MANAGER, dockerid))
        for domain in DOMAINS:
            if domain in output:
                response = {'code': '0', 'domain': domain, 'port': "%d" % (port), 'sshport': "%d" % (sshport), 'dockerid': dockerid}
                return obj_to_json(response)
        return reply(6, "Unable to find the domain")
    else:
        return reply(5, output)
"""

def startservice(ptype, path=None, node=None, port=None, memory=None, overload=False):
    global MANAGER
    constraint=''
    if node is None:
        node=1
    if int(node) != 0:
        constraint=" -e constraint:node_name==node%d" % (int(node))
    if port is None:
        port=get_valid_port(2010, 2999)
    else:
        port=int(port)
    memlimit=''
#    if memory is not None:
#        memlimit=" -m %dM" % (int(memory))

    sshport=get_valid_port(4001, 6000)

    if overload:
        commands.getstatusoutput("docker %s rm -f `docker %s ps | grep ':%d->' | awk '{print $1}'`" % (MANAGER, MANAGER, port))

    if ptype=='tomcat7':
        ptype='tomcat'

    if ptype=='tomcat':
        code, output=commands.getstatusoutput("docker %s run -id%s -p %d:8080 -p %d:22 -v /root/data/repo/:/data/repo/ -v /root/data/template/:/data/template/ -v /root/data/share/:/data/share/ -v /root/data/completion/:/data/completion/ -v /root/data/mvnrepo/repository/:/root/.m2/repository/ -v /root/data/service%s:/usr/local/tomcat/webapps/ROOT/%s pop2016/server" % (MANAGER, memlimit, port, sshport, path, constraint))
#    elif ptype=='tomcat7':
#        code, output=commands.getstatusoutput("docker %s run -id%s -p %d:8080 -p %d:22 -v /root/data/repo/:/data/repo/ -v /root/data/template/:/data/template/ -v /root/data/share/:/data/share/ -v /root/data/completion/:/data/completion/ -v /root/data/service%s:/usr/local/tomcat/webapps/ROOT/%s pop2016/tomcat7" % (MANAGER, memlimit, port, sshport, path, constraint))
#    elif ptype=='gateone':
#        code, output=commands.getstatusoutput("docker %s run -id%s -p %d:8000 -p %d:22%s pop2016/gateone" % (MANAGER, memlimit, port, sshport, constraint))
    elif ptype=='nginx':
        sshport=0
        code, output=commands.getstatusoutput("docker %s run -id%s -p %d:80 -v /root/data/nginx_conf%s:/etc/nginx/%s nginx" % (MANAGER, memlimit, port, path, constraint))
    else:
        code, output=commands.getstatusoutput("/bin/bash ../scripts/%s.sh" % (ptype))
    
    if code is 0:
#        if ptype!='tomcat' and ptype!='gateone' and ptype!='nginx' and ptype!='tomcat7':
        if ptype!='tomcat' and ptype!='nginx':
            return reply(0, "Success")
        dockerid = output[0:12]
        code, output = commands.getstatusoutput("docker %s ps | grep %s" % (MANAGER, dockerid))
        for domain in DOMAINS:
            if domain in output:
                response = {'code': '0', 'domain': domain, 'port': "%d" % (port), 'sshport': "%d" % (sshport), 'dockerid': dockerid}
                return obj_to_json(response)
        return reply(6, "Unable to find the domain")
    else:
        return reply(5, output)

def restart(dockerid=None):
    global MANAGER
    status, output=commands.getstatusoutput("docker %s restart %s" % (MANAGER, dockerid))
    if status==0:
        return reply(0, "ok")
    return reply(1, output)

def stat(dockerid=None):
    global MANAGER
    if dockerid is not None:
        status, output=commands.getstatusoutput("docker %s stats --no-stream %s" % (MANAGER, dockerid))
        if status==0:
            output=output.replace("/"," ").replace("\t"," ").replace("kB","KB").split("\n")
            st=output[1].split()
            return obj_to_json({"code":"0", "dockerid": st[0], "cpu": st[1], "memuse": st[2]+" "+st[3], "memall": st[4]+" "+st[5], "mempercent":st[6], "netin":st[7]+" "+st[8], "netout":st[9]+" "+st[10]})
        else:
            return reply(1, output)

    stats=[]

    status, output = commands.getstatusoutput("docker %s stats --no-stream `docker %s ps -q`" % (MANAGER, MANAGER))
    if status == 0:
        output = output.replace("/"," ").replace("\t"," ").replace("kB","KB")
        sts = output.split("\n")
        for i in range(1, len(sts)):
            st=sts[i].split()
            stat={"dockerid": st[0], "cpu": st[1], "memuse": st[2]+" "+st[3], "memall": st[4]+" "+st[5], "mempercent":st[6], "netin":st[7]+" "+st[8], "netout":st[9]+" "+st[10]}
            stats.append(stat)

    return obj_to_json(stats)

def servicestat(dockerid, ptype='tomcat'):
    if ptype=='tomcat':
        status, output=commands.getstatusoutput("docker %s exec -i %s ps aux | grep java -m 1 | awk '{print $8}'" % (MANAGER, dockerid))
        if status==0:
            return obj_to_json({"code":"0", "stat":output})
        else:
            return reply(1, output)

    if ptype=='registry':
        status, output=commands.getstatusoutput("docker %s exec -i registry ps aux | grep java -m 1 | awk '{print $8}'" % (MANAGER))
        if status==0:
            return obj_to_json({"code":"0", "stat":output})
        else:
            return reply(1, output)
    else:
        return reply(1, "unknown service")

def log(dockerid, ptype):
    global MANAGER
#    if ptype=='php':
#        status, output = commands.getstatusoutput("docker %s exec -i %s /bin/cat /var/www/error.log" % (MANAGER, dockerid))
#    elif ptype=='python':
#        status, output = commands.getstatusoutput("docker %s logs -t %s" % (MANAGER, dockerid))
#    elif ptype=='tomcat':
#        date=strftime("%Y-%m-%d", localtime(time()))
#        status, output=commands.getstatusoutput("docker %s exec -i %s /bin/cat /usr/local/tomcat/logs/catalina.%s.log" % (MANAGER, dockerid, date))
#    elif ptype=='cpp':
#        status, output = commands.getstatusoutput("docker %s exec -i %s /bin/cat /root/code/error.log" % (MANAGER, dockerid))
#    else:
#        return reply(1, "Unknown type")
    status, output=commands.getstatusoutput("docker %s exec -i %s /bin/cat /root/code/error.log" % (MANAGER, dockerid))
    if status==0:
        return obj_to_json({"code":0, "log":output})
    else:
        return reply(1, output)

def nodestat():
    global MANAGER
    code, output=commands.getstatusoutput("docker %s info" % (MANAGER))
    return obj_to_json({"code":0, "nodestat":output})

def ps():
    global MANAGER
    code, output=commands.getstatusoutput("docker %s ps -a" % (MANAGER))
    return "<pre>"+output+"</pre>"

def deleteall():
    global MANAGER
    code, output=commands.getstatusoutput("docker %s rm -f `docker %s ps -a -q`" % (MANAGER, MANAGER))
    return ps()

def autodelete():
    global MANAGER
    code, output=commands.getstatusoutput("docker %s rm -f `docker %s ps -a | grep -v '/tcp' | grep -v 'CONTAINER' | awk '{print $1}'`" % (MANAGER, MANAGER))
    code, output=commands.getstatusoutput("docker %s rm -f `docker %s ps -a | grep runner | awk '{print $1}'`" % (MANAGER, MANAGER))
    if code==0:
        return obj_to_json({"code":"0", "dockerid": output.split("\n")})
    return reply(1, output)

@app.route("/", methods=['GET', 'POST'])
def main():
    if request.method == 'GET':
        params = request.args
    else:
        params = request.form
    action=params.get('action', default=None)
    path=params.get('path', default=None)
    ptype=params.get('type', default=None)
    port=params.get('port', default=None)
    node=params.get('node', default=None)
    memory=params.get('memory', default=None)
    dockerid=params.get('dockerid', default=None)
    overload=params.get('overload', default=None)
    extra=params.get('extra', default=None)
    if overload is not None:
        overload=True
    else:
        overload=False

    if action=='run':
        return run(ptype, path, extra, node, port, memory, overload)
    if action=='startservice':
        return startservice(ptype, path, node, port, memory, overload)
    if action=='stat':
        return stat(dockerid)
    if action=='delete':
        return delete(dockerid)
    if action=='restart':
        return restart(dockerid)
    if action=='servicestat':
        if ptype is None:
            ptype='tomcat'
        return servicestat(dockerid, ptype)
    if action=='log':
        return log(dockerid, ptype)
    if action=='nodestat':
        return nodestat()
    if action=='ps':
        return ps()
    if action=='deleteall':
        return deleteall()
    if action=='autodelete':
        return autodelete()

    return reply(0, "unknown request")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=PORT)


