from json import dumps
import os
import random
import MySQLdb
from flask import *
from container_manager import *

__author__ = 'Hu Xing'
INDEX = {'javaweb-compiler':0, 'gateone':0}


# connect to mysql
def mysql_con():
    try:
        conn = MySQLdb.connect(host='rdsj7nhfyy0syt1fw980.mysql.rds.aliyuncs.com', user='useradmin', passwd='useradmin',
                               db='pop2016', port=3306)
    except Exception, e:
        return None
    return conn


# format current time as a string
def get_current_time(timestamp=None):
    if timestamp is None:
        timestamp = time()
    return strftime("%Y-%m-%d %H:%M:%S", localtime(timestamp))


app = Flask(__name__)


@app.route("/getinstance", methods=['GET', 'POST'])
def get_instance():
    global INDEX
    if request.method == 'GET':
        params = request.args
    else:
        params = request.form
    service_name = params.get("name")
    conn = mysql_con()
    cursor = conn.cursor()
    if service_name=='gateone'or service_name=='javaweb-compiler':
        sql = "SELECT domain, port FROM service, service_instance WHERE id=service_id AND service_name='%s' AND issuper=1" % service_name
        count = cursor.execute(sql)
        results = cursor.fetchall()
        cursor.close()
        conn.close()
        if count == 0:
            code = 1
            msg = "No available instance!"
            return dumps({'code': code, 'msg': msg})
        else:
            index = int(INDEX[service_name]) % len(results)
            url = results[index][0]+':'+ str(results[index][1])
            INDEX[service_name] += 1
            code = 0
            return dumps({'code':code,'url':url})
    else:
        sql = "SELECT plugin_address FROM service WHERE service_name='%s' AND issuper=1" % service_name
        count = cursor.execute(sql)
        result = cursor.fetchone()
        cursor.close()
        conn.close()
        if count == 0:
            code = 1
            msg = "No available instance!"
            return dumps({'code': code, 'msg': msg})
        else:
            url = result[0]
            code = 0
            return dumps({'code':code,'url':url})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=9996, debug=True)
