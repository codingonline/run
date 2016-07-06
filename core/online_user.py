from threading import Timer
from datetime import datetime
import time
import MySQLdb

__author__ = 'user'
timer_interval = 24 * 60 * 60


# connect to mysql
def mysql_con():
    try:
       conn = MySQLdb.connect(host='rdsj7nhfyy0syt1fw980.mysql.rds.aliyuncs.com', user='useradmin', passwd='useradmin',
                              db='pop2016', port=3306, charset="utf8")
    except Exception, e:
        return None
    return conn


def online():
    conn = mysql_con()
    cursor = conn.cursor()
    sql = "select * from user where  date_format(last_login,'%Y-%m-%d') = curdate()"
    count = cursor.execute(sql)
    sql = "INSERT INTO online_user(date, user_num) VALUES (curdate(), %d)" % count
    cursor.execute(sql)
    conn.commit()
    cursor.close()
    conn.close()
    Timer(timer_interval, online).start()


curTime = datetime.now()
desTime = curTime.replace(hour=23, minute=59, second=0, microsecond=0)
delta = desTime - curTime
delta = delta.total_seconds()
time.sleep(delta)
online()
