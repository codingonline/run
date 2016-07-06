# coding:utf-8
import os
import urllib
import urllib2
from flask import *
from werkzeug.utils import secure_filename
from container_manager import *
from json import loads, dumps
import MySQLdb
from time import localtime, time, strftime
from threading import Timer
import smtplib
from email.mime.text import MIMEText
import sys

reload(sys)
sys.setdefaultencoding('utf8')
__author__ = 'Hu Xing'

MONITOR_PORT = 9222
VALID_TYPES = ['php', 'python', 'javaweb']  # valid runner types
TIME_INTERVAL = 3600
SENDER = '胡星<huxing0101@pku.edu.cn>'
RECEIVIER = 'mass@sei.pku.edu.cn'
SMTPSERVER = 'smtp.pku.edu.cn'
USERNAME = 'huxing0101@pku.edu.cn'
PASSWORD = ''
CODE_ADDR = "/root/data/service/admin/"
ALLOWED_EXTENSIONS = set(['war'])
ADMIN_ID = 111


def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1] in ALLOWED_EXTENSIONS


def check_folder(addr):
    if os.path.exists(addr):
        return True
    else:
        return False


# format current time as a string
def get_current_time(timestamp=None):
    if timestamp is None:
        timestamp = time();
    return strftime("%Y-%m-%d %H:%M:%S", localtime(timestamp))


# connect to mysql
def mysql_con():
    try:
        conn = MySQLdb.connect(host='rdsj7nhfyy0syt1fw980.mysql.rds.aliyuncs.com', user='useradmin', passwd='useradmin',
                               db='pop2016', port=3306, charset="utf8")
    except Exception, e:
        return None
    return conn


def obj_to_json(obj):
    return dumps(obj)


def reply(code, msg):
    return obj_to_json({'code': code, 'msg': msg})


def check_homepage():
    url = "http://www.poprogramming.com"
    try:
        response = urllib2.Request(url)
        res = urllib2.urlopen(response, timeout=10)
    except urllib2.URLError as e:
        SUBJECT = 'Homepage failure!'
        str = 'Homapage time out!'
        msg = MIMEText(str, 'plain', 'utf-8')
        msg['Subject'] = SUBJECT
        smtp = smtplib.SMTP()
        smtp.connect(SMTPSERVER)
        smtp.login(USERNAME, PASSWORD)
        smtp.sendmail(SENDER, RECEIVIER, msg.as_string())
        smtp.quit()


app = Flask(__name__)


@app.route("/", methods=['GET', 'POST'])
def index():
    if session.get('username') == 'admin' and session.get('password') == 'admin':
        return redirect(url_for('userinfo'))
    else:
        return render_template("index.html")


@app.route("/login", methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        if request.form['username'] == "admin" and request.form['password'] == "admin":
            session['username'] = request.form['username']
            session['password'] = request.form['password']
            return redirect(url_for('userinfo'))
        else:
            return render_template("login.html")
    else:
        return render_template("login.html")


@app.route('/logout')
def logout():
    session.pop('username', None)
    session.pop('password', None)
    return redirect(url_for('index'))


# interface for editor to get app log
@app.route("/applog", methods=['GET', 'POST'])
def app_log():
    if request.method == 'GET':
        params = request.args
    else:
        params = request.form

    dockerid = params.get('dockerid', default=None)
    ptype = params.get('type', default='invalid')
    result = log(dockerid, ptype)
    return result


    # param = urllib.urlencode({'runnerid': runnerid,'type':ptype})
    # req = urllib2.urlopen(CONTROLLER+"/log", param)
    # response = urllib2.urlopen(req)
    # result = response.read()
    # result = log_filter(result)


# interface for editor to get runner container status
@app.route("/runnerstat")
def runner_stat():
    if request.method == 'GET':
        params = request.args
    else:
        params = request.form
    dockerid = params.get('dockerid', default=None)
    result = stat(dockerid)
    return result


def send_mail(report):
    SUBJECT = 'POP2016 monitor'
    str = '<html><h1>Warning!</h1></html>' + '<table border="1"><tr><th>Docker ID</th><th>CPU</th><th>mempercent</th></tr>'
    for st in report:
        str = str + '<tr><td>' + st['dockerid'] + '</td><td>' + st['cpu'] + '</td><td>' + st[
            'mempercent'] + '</td></tr>'
    str = str + '</table>'
    msg = MIMEText(str, 'html', 'utf-8')
    msg['Subject'] = SUBJECT
    smtp = smtplib.SMTP()
    smtp.connect(SMTPSERVER)
    smtp.login(USERNAME, PASSWORD)
    smtp.sendmail(SENDER, RECEIVIER, msg.as_string())
    smtp.quit()


# get all docker stats every 1 hour

def check_docker_stats():
    global TIME_INTERVAL
    conn = mysql_con()
    cursor = conn.cursor()

    currtime = get_current_time()
    stats = stat()
    stats = loads(stats)
    report = []
    for st in stats:
        cpu = round(float(st['cpu'][0:-1]), 2)
        memuse = st['memuse'].split(' ')
        # memuse unit is 'MB'
        if memuse[1] == 'B':
            memuse = round(float(memuse[0]) / (1024 * 1024), 2)
        elif memuse[1] == 'KB':
            memuse = round(float(memuse[0]) / 1024, 2)
        elif memuse[1] == 'GB':
            memuse = round(float(memuse[0]) * 1024, 2)
        elif memuse[1] == 'MB':
            memuse = round(float(memuse[0]), 2)
        memall = st['memall'].split(' ')
        if memall[1] == 'GB':
            memall = round(float(memall[0]) * 1024, 2)
        elif memall[1] == 'KB':
            memall = round(float(memall[0]) / 1024, 2)
        elif memall[1] == 'B':
            memall = round(float(memall[0]) / (1024 * 1024), 2)
        elif memall[1] == 'MB':
            memall = round(float(memall[0]), 2)
        mempercent = round(float(st['mempercent'][0:-1]), 2)

        # net unit is 'KB
        netin = st['netin'].split(' ')
        if netin[1] == 'B':
            netin = round(float(netin[0]) / 1024, 2)
        elif netin[1] == 'MB':
            netin = round(float(netin[0]) * 1024, 2)
        elif netin[1] == 'KB':
            netin = round(float(netin[0]), 2)
        netout = st['netout'].split(' ')
        if netout[1] == 'B':
            netout = round(float(netout[0]) / 1024, 2)
        elif netout[1] == 'MB':
            netout = round(float(netout[0]) * 1024, 2)
        elif netout[1] == 'KB':
            netout = round(float(netout[0]), 2)
        sql = "insert into dockerstat(dockerid,time,cpu,memuse,memall,mempercent,netin,netout) VALUES ('%s', '%s', %f, %f, %f, %f, %f, %f)" % (
            st['dockerid'], currtime, cpu, memuse, memall, mempercent, netin, netout)
        try:
            cursor.execute(sql)
            conn.commit()
        except Exception, e:
            pass
        if mempercent > 50 or cpu > 50:
            report.append(st)
    cursor.close()
    conn.close()
    check_homepage()
    if len(report) > 0:
        send_mail(report)
    Timer(TIME_INTERVAL, check_docker_stats).start()


def get_info(dockerid):
    conn = mysql_con()
    mems = []
    cpus = []
    netins = []
    netouts = []
    sql = "select time, cpu, memuse , memall, netin, netout FROM dockerstat WHERE dockerid = '%s'" % dockerid
    cursor = conn.cursor()
    count = cursor.execute(sql)
    results = cursor.fetchall()
    for result in results:
        cpu = dict(time=result[0], cpu=result[1])
        memusg = dict(time=result[0], mem=result[2])
        netin = dict(time=result[0], netin=result[4])
        netout = dict(time=result[0], netout=result[5])

        cpus.append(cpu)
        mems.append(memusg)
        netins.append(netin)
        netouts.append(netout)
    cursor.close()
    conn.close()
    infor = dict(cpus=cpus, mems=mems, netins=netins, netouts=netouts)
    return infor


@app.route('/dockerstat', methods=['GET', 'POST'])
def dockerstst():
    if request.method == 'GET':
        params = request.args
    else:
        params = request.form
    dockerid = params.get('dockerid')
    infor = get_info(dockerid)
    cpus = infor['cpus']
    mems = infor['mems']
    netins = infor['netins']
    netouts = infor['netouts']
    return render_template('dockerstat.html', mems=mems, cpus=cpus, netins=netins, netouts=netouts)


@app.route('/userinfo', methods=['GET', 'POST'])
def userinfo():
    if session.get('username') != 'admin' or session.get('password') != 'admin':
        return redirect(url_for('login'))
    if request.method == 'GET':
        param = request.args
    else:
        param = request.form

    conn = mysql_con()
    cursor = conn.cursor()

    # user statistic
    users = []
    sql = "SELECT * FROM user ORDER BY last_login DESC"
    user_count = cursor.execute(sql)
    results = cursor.fetchall()
    for result in results:
        user = dict(id=result[0], username=result[1], email=result[5], last_login=result[3], register_time=result[13])
        users.append(user)

    # online statistic
    onlines = []

    sql = "select * from user where  date_format(last_login,'%Y-%m-%d') = curdate()"
    count = cursor.execute(sql)
    date = strftime('%Y-%m-%d', localtime(time()))
    online = dict(date=date, count=count)
    onlines.append(online)
    sql = "SELECT * FROM online_user ORDER BY date DESC limit 30"
    day_count = cursor.execute(sql) + 1
    results = cursor.fetchall()
    for result in results:
        online = dict(date=result[0], count=result[1])
        onlines.append(online)
    cursor.close()
    conn.close()
    return render_template('userinfo.html', user_count=user_count, users=users, day_count=day_count, onlines=onlines)


# home services are displayed default
@app.route("/monitor")
def monitor():
    if session.get('username') != 'admin' or session.get('password') != 'admin':
        return redirect(url_for('login'))
    if request.method == 'GET':
        params = request.args
    else:
        params = request.form
    home_service = []
    runners = []
    services = []

    stats = stat()  # get all dockers stats
    stats = loads(stats)
    conn = mysql_con()
    cursor = conn.cursor()

    # home services
    sql = "SELECT id, service_name, service_type,plugin_address,update_date FROM service WHERE issuper=1"
    count = cursor.execute(sql)
    results = cursor.fetchall()
    for result in results:
        s = dict(id=result[0], name=result[1], type=result[2], address=result[3], update_time=result[4])
        home_service.append(s)

    # open service
    sql = "SELECT id, service_name,service_type,owner_name,plugin_address,create_date,status FROM service WHERE issuper=0"
    count = cursor.execute(sql)
    results = cursor.fetchall()
    for result in results:
        s = dict(id=result[0], name=result[1], type=result[2], owner=result[3], address=result[4],
                 create_date=result[5], status=result[6])
        services.append(s)

    # runners
    for st in stats:
        dockerid = st['dockerid']
        sql = "SELECT app_name, app_type, user_name, owner_name, app_instance.domain, port,sshport FROM app_instance, app WHERE dockerid='%s' AND app_instance.appid=app.id limit 1" % dockerid
        count = cursor.execute(sql)
        if count == 1:
            result = cursor.fetchone()
            s = dict(name=result[0], type=result[1], user=result[2], owner=result[3], domain=result[4], port=result[5],
                     sshport=result[6])
            s = dict(s.items() + st.items())
            runners.append(s)
            continue
    cursor.close()
    conn.close()
    return render_template('monitor.html', runners=runners, services=services, home_service=home_service)


@app.route('/setstatus', methods=['GET', 'POST'])
def setstatus():
    if session.get('username') != 'admin' or session.get('password') != 'admin':
        return redirect(url_for('login'))
    if request.method == 'GET':
        params = request.args
    else:
        params = request.form
    serviceid = int(params.get('serviceid'))
    value = int(params.get('serviceid'))
    param = urllib.urlencode({'action': 'setstatus', 'value': value, 'serviceid': serviceid})
    req = urllib2.Request("http://123.57.32.46:8080/openServiceAPI", param)
    response = urllib2.urlopen(req)
    response = response.read()
    return dumps({'code':0, 'msg':'success'})


@app.route("/instance")
def instance():
    if request.method == 'GET':
        params = request.args
    else:
        params = request.form
    service_id = params.get("id")
    service_id = int(service_id)
    instances = []
    conn = mysql_con()
    cursor = conn.cursor()

    stats = stat()
    stats = loads(stats)

    sql = "SELECT dockerid,domain, port,sshport FROM service_instance WHERE service_id=%d" % service_id
    count = cursor.execute(sql)
    results = cursor.fetchall()

    sql = "SELECT service_name FROM service WHERE id=%d" % service_id
    cursor.execute(sql)
    service_name = cursor.fetchone()[0]
    if count > 0:
        for result in results:
            for st in stats:
                if result[0] == st['dockerid']:
                    ins = dict(domain=result[1], port=result[2], sshport=result[3])
                    ins = dict(ins.items() + st.items())
                    instances.append(ins)
                    break

    cursor.close()
    conn.close()
    return render_template("instance.html", instances=instances, service_name=service_name)


@app.route("/upload", methods=['GET', 'POST'])
def upload_service():
    if request.method == 'POST':
        param = request.form
        service_type = param.get('type', None)
        port = int(param.get('port', None))
        code_file = request.files.get('code', None)
        service_name = param.get('service-name', None)
        current_time = get_current_time()
        if not os.path.exists(CODE_ADDR):
            os.makedirs(CODE_ADDR)
        if code_file and allowed_file(code_file.filename):
            app.config['UPLOAD_FOLDER'] = CODE_ADDR
            file_name = secure_filename(code_file.filename)
            code_file.save(os.path.join(app.config['UPLOAD_FOLDER'], file_name))
            code, output = commands.getstatusoutput(
                " unzip -o %s/%s -d %s/%s" % (CODE_ADDR, file_name, CODE_ADDR, service_name))
        path = '/admin/' + service_name + '/'
        node = 1
        memory = None
        overload = 1
        conn = mysql_con()
        cursor = conn.cursor()
        sql = "SELECT * FROM service WHERE service_name='%s' AND owner_id=%d" % (service_name, ADMIN_ID)
        cnt = cursor.execute(sql)
        if cnt == 0:
            sql = "INSERT INTO service(service_name, service_type, service_container_type, owner_id, create_date, issuper) VALUES ('%s', '%s', '%s', '%d', '%s', '%d')" % (
                service_name, service_type, service_type, ADMIN_ID, current_time, 1)
            cursor.execute(sql)
            conn.commit()
        res = startservice(service_type, path, node, port, memory, overload)
        res = loads(res)
        if int(res['code']) != 0:
            return res
        else:
            sql = "SELECT id FROM service WHERE service_name = '%s' AND issuper=1" % service_name
            count = cursor.execute(sql)
            result = cursor.fetchone()
            sql = "DELETE FROM service_instance WHERE port =%d" % int(res['port'])
            count = cursor.execute(sql)
            sql = "INSERT INTO service_instance(dockerid,service_id,domain,port,sshport) VALUES ('%s',%d,'%s',%d,%d)" % (
                res['dockerid'], result[0], res['domain'], int(res['port']), int(res['sshport']))
            try:
                cursor.execute(sql)
                conn.commit()
            except Exception, e:
                pass
        cursor.close()
        conn.close()

        return redirect(url_for('instance', id=result[0]))


@app.route("/delete_instance", methods=['GET', 'POST'])
def delete_instance():
    if request.method == 'GET':
        params = request.args
    else:
        params = request.form
    dockerid = params.get('dockerid')
    param = urllib.urlencode({'dockerid': dockerid})
    req = urllib2.Request("http://123.57.2.1:9998/delete_instance", param)
    response = urllib2.urlopen(req)
    result = response.read()
    return result


@app.route("/create_instance", methods=['GET', 'POST'])
def create_instance():
    if request.method == 'GET':
        params = request.args
    else:
        params = request.form
    serviceid = params.get('serviceid')
    conn = mysql_con()
    cursor = conn.cursor()
    sql = "SELECT service_name, service_type FROM service WHERE id=%d AND issuper=1" % int(serviceid)
    count = cursor.execute(sql)
    result = cursor.fetchone()
    if result[0] == 'javaweb-compiler':
        res = startservice(result[1], '/admin/javaweb-compiler/', 1, None, None, False)
        res = loads(res)
        if int(res['code']) == 0:
            sql = "INSERT INTO service_instance(dockerid,service_id,domain,port,sshport) VALUES ('%s',%d,'%s',%d,%d)" % (
                res['dockerid'], serviceid, res['domain'], int(res['port']), int(res['sshport']))
            try:
                cursor.execute(sql)
                conn.commit()
            except Exception, e:
                pass
            cursor.close()
            conn.close()
        return dumps(res)
    elif result[0] == 'gateone':
        res = startservice(result[1], None, 1, None, None, False)
        res = loads(res)
        if int(res['code']) == 0:
            sql = "INSERT INTO service_instance(dockerid,service_id,domain,port,sshport) VALUES ('%s',%d,'%s',%d,%d)" % (
                res['dockerid'], serviceid, res['domain'], int(res['port']), int(res['sshport']))
            try:
                cursor.execute(sql)
                conn.commit()
            except Exception, e:
                pass
            cursor.close()
            conn.close()
        return dumps(res)
    else:
        param = urllib.urlencode({'serviceid': serviceid})
        req = urllib2.Request("http://123.57.2.1:9998/create_instance", param)
        response = urllib2.urlopen(req)
        return response.read()


app.secret_key = 'A0Zr98j/3yX R~XHH!jmN]LWX/,?RT'

if __name__ == "__main__":
    Timer(TIME_INTERVAL, check_docker_stats).start()
    app.run(host="0.0.0.0", port=MONITOR_PORT, debug=True, use_reloader=False)
