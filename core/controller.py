#!/usr/bin/env python
# encoding: utf-8

import container_manager
import MySQLdb
import re
from flask import Flask, request
from config import *
from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime, timedelta
from math import ceil
from shutil import copyfile
from os import path, makedirs, rename, remove


app = Flask(__name__)
scheduler = BackgroundScheduler()


def do_append_instances(service_id, num):
    service, msg = get_service(service_id)
    if service is None:
        return make_reply(1, msg)
    # create a new instance of this service
    service_name, service_type, owner = service[1], 'tomcat', service[9]
    service_path = make_service_path(service_name, service_type, owner)
    for _ in range(num):
        rslt = container_manager.json_to_obj(container_manager.startservice(service_type, service_path))
        if rslt['code'] != '0':
            return container_manager.obj_to_json(rslt)
        # save this instance
        save_rslt = add_service_instance(service_id, rslt)
        if not save_rslt[0]:
            return make_reply(1, save_rslt[1])
        # get the host and port of this instance
        instance_host, instance_port = rslt['domain'], rslt['port']
        # add new instance to nginx conf file
        add_host_to_nginx_conf(service_path, instance_host, instance_port)
    # restart the router
    router, msg = get_router(service_id)
    if router is None:
        return make_reply(1, msg)
    container_manager.restart(router[0])
    return make_reply(0, 'success')


def do_delete_instances(instances):
    service, msg, service_name, service_path = None, None, None, None
    router = None
    for docker_id in instances:
        container_manager.delete(docker_id)
        instance, msg = get_service_instance(docker_id)
        if instance is None:
            return make_reply(1, msg)
        instance_host, instance_port = instance[1], instance[2]
        if service is None:
            service, msg = get_service(instance[4])
            service_name, service_type, owner = service[1], 'tomcat', service[9]
            service_path = make_service_path(service_name, service_type, owner)
        delete_host_from_nginx_conf(service_path, instance_host, instance_port)
        remove_service_instance(docker_id)
    if service is not None:
        router, msg = get_router(service[0])
        if router is None:
            return make_reply(1, msg)
        container_manager.restart(router[0])
    return make_reply(0, 'success')


class AutoScaler:

    def __init__(self, sid, target_cpu_usage = 0.8):
        self.service_id = sid
        # the list keeping all instances of this service
        self.instances = self.__fetch_instances()
        self.last_accumulate_time = datetime.now()
        self.click_cnt = 0.0
        self.last_scale_time = None
        self.target_cpu_usage = target_cpu_usage

    def __fetch_instances(self):
        instances = []
        all_instances, msg = get_all_instances(self.service_id)
        for instance in all_instances:
            instances.append([instance[0], 0.0])
        return instances

    def scale(self):
        instances = self.__fetch_instances()
        if len(instances) != len(self.instances):
           self.click_cnt = 0.0
           self.instances = instances
        # update the statistics of every instance
        self.click_cnt += 1.0
        for instance in self.instances:
            instance[1] += float(container_manager.json_to_obj(container_manager.stat(instance[0]))['cpu'][:-1])
        now = datetime.now()
        if now - self.last_accumulate_time > timedelta(minutes=MIN_SCALING_INTERVAL):
            print '------------------------------------'
            print now
            print len(self.instances)
            print self.instances
            self.last_accumulate_time = now
	    total_cpu_usage = reduce(lambda x, y: x + y, [item[1] / self.click_cnt for item in self.instances], 0.0)
	    target_num = int(ceil(total_cpu_usage / (self.target_cpu_usage * 100)))
	    print total_cpu_usage, target_num
            if self.last_scale_time is None or now - self.last_scale_time > timedelta(minutes=MIN_STABLE_INTERVAL):
                if target_num != len(self.instances):
                    self.do_scale(len(self.instances), target_num)
                    self.last_scale_time = now
                    self.instances = self.__fetch_instances()
            self.click_cnt = 0.0
            for instance in self.instances:
                instance[1] = 0.0

    def do_scale(self, origin, target):
        # in case target is smaller than 1
        target = 1 if target < 1 else target
        # scale up
        if origin < target:
            return do_append_instances(self.service_id, target - origin)
        # scale down
        elif origin > target:
            self.instances = sorted(self.instances, key=lambda item: item[1])
            return do_delete_instances([item[0] for item in self.instances[:origin - target]])
        return make_reply(0, 'No operation.')


def get_params(req):
    return req.args if req.method == 'GET' else req.form


def make_app_path(app_name, app_type, owner):
#    if app_type == 'javaweb':
#        return '/{0}/{1}/target/{1}/'.format(owner, app_name)
    return '/{0}/{1}/'.format(owner, app_name)


def make_service_path(service_name, service_type, owner):
    return '/{0}/{1}/'.format(owner, service_name)


def add_app_instance(app_id, obj):
    try:
        conn = MySQLdb.connect(host=MYSQL_HOST, user=MYSQL_USER, passwd=MYSQL_PASS, db=DATABASE)
    except Exception, e:
        return (False, str(e))
    else:
        cursor = conn.cursor()
        sql = 'insert into app_instance values (%s, %s, %s, %s, %s)'
        params = (obj['dockerid'], obj['domain'], obj['port'] if 'port' in obj else obj['wsport'], obj['sshport'], app_id)
        cursor.execute(sql, params)
        cursor.close()
        conn.commit()
        conn.close()
        return (True, "success")


def remove_app_instance(docker_id):
    try:
        conn = MySQLdb.connect(host=MYSQL_HOST, user=MYSQL_USER, passwd=MYSQL_PASS, db=DATABASE)
    except Exception, e:
        return (False, str(e))
    else:
        cursor = conn.cursor()
        sql = 'delete from app_instance where dockerid=%s'
        params = (docker_id,)
        cursor.execute(sql, params)
        cursor.close()
        conn.commit()
        conn.close()
        return (True, "success")


def make_reply(status, msg):
    return container_manager.obj_to_json({'code': status, 'msg': msg})


def stop_if_exists(app_id):
    if app_id is not None:
        try:
            conn = MySQLdb.connect(host=MYSQL_HOST, user=MYSQL_USER, passwd=MYSQL_PASS, db=DATABASE)
        except Exception, e:
            return (False, str(e))
        else:
            cursor = conn.cursor()
            sql = 'select dockerid from app_instance where appid=%s'
            cnt = cursor.execute(sql, (app_id, ))
            if cnt == 0:
                return (True, "No instance is running for this app.")
            running_docker_id = cursor.fetchone()[0]
            container_manager.delete(running_docker_id)
            sql = 'delete from app_instance where appid=%s'
            cursor.execute(sql, (app_id, ))
            cursor.close()
            conn.commit()
            conn.close()
            return (True, "Existing instance has bee stopped.")
    return (False, "No specific app id.")


def get_app(app_id, user):
    if app_id is not None and user is not None:
        try:
            conn = MySQLdb.connect(host=MYSQL_HOST, user=MYSQL_USER, passwd=MYSQL_PASS, db=DATABASE)
        except Exception, e:
            return (None, str(e))
        else:
            cursor = conn.cursor()
            sql = 'select app_name, app_type, owner_name from app where id=%s and user_name=%s'
            cnt = cursor.execute(sql, (app_id, user))
            rslt = cursor.fetchone()
            cursor.close()
            conn.close()
            if cnt != 1:
                return (None, '{0} row(s) has been found!'.format(cnt))
            return (rslt, "success")
    return (None, "Param Error.")


def check_live_time(start, job_id):
    live_time = (datetime.now() - start).total_seconds()
    if live_time / 60 >= TIME_LIMIT:
        docker_id = job_id
        container_manager.delete(docker_id)
        remove_app_instance(docker_id)
        scheduler.remove_job(job_id)


def get_service(service_id):
    if service_id is not None:
        try:
            conn = MySQLdb.connect(host=MYSQL_HOST, user=MYSQL_USER, passwd=MYSQL_PASS, db=DATABASE)
        except Exception, e:
            return (None, str(e))
        else:
            cursor = conn.cursor()
            sql = 'select * from service where id=%s'
            cnt = cursor.execute(sql, (service_id, ))
            rslt = cursor.fetchone()
            cursor.close()
            conn.close()
            if cnt != 1:
                return (None, '{0} row(s) has been found!'.format(cnt))
            return (rslt, "success")
    return (None, "Param Error.")


def add_service_instance(service_id, obj):
    try:
        conn = MySQLdb.connect(host=MYSQL_HOST, user=MYSQL_USER, passwd=MYSQL_PASS, db=DATABASE)
    except Exception, e:
        return (False, str(e))
    else:
        cursor = conn.cursor()
        sql = 'insert into service_instance values (%s, %s, %s, %s, %s)'
        params = (obj['dockerid'], obj['domain'], obj['port'], obj['sshport'], service_id)
        cursor.execute(sql, params)
        cursor.close()
        conn.commit()
        conn.close()
        return (True, "success")


def stop_all_instances(service_id):
    if service_id is not None:
        try:
            conn = MySQLdb.connect(host=MYSQL_HOST, user=MYSQL_USER, passwd=MYSQL_PASS, db=DATABASE)
        except Exception, e:
            return (False, str(e))
        else:
            cursor = conn.cursor()
            sql = 'select dockerid from service_instance where service_id=%s'
            cursor.execute(sql, (service_id, ))
            instances = cursor.fetchall()
            for instance in instances:
                container_manager.delete(instance[0])
            sql = 'delete from service_instance where service_id=%s'
            cursor.execute(sql, (service_id, ))
            cursor.close()
            conn.commit()
            conn.close()
            return (True, "success")
    return (False, "Param Error.")


def get_all_instances(service_id=None):
    try:
        conn = MySQLdb.connect(host=MYSQL_HOST, user=MYSQL_USER, passwd=MYSQL_PASS, db=DATABASE)
    except Exception, e:
        return (None, str(e))
    else:
        cursor = conn.cursor()
        sql = 'select dockerid from service_instance'
        if service_id is None:
            cursor.execute(sql)
            instances = cursor.fetchall()
        else:
            sql += ' where service_id=%s'
            cursor.execute(sql, (service_id,))
            instances = cursor.fetchall()
        cursor.close()
        conn.close()
        return (instances, 'success')


def get_service_instance(docker_id):
    if docker_id is not None:
        try:
            conn = MySQLdb.connect(host=MYSQL_HOST, user=MYSQL_USER, passwd=MYSQL_PASS, db=DATABASE)
        except Exception, e:
            return (None, str(e))
        else:
            cursor = conn.cursor()
            sql = 'select * from service_instance where dockerid=%s'
            cnt = cursor.execute(sql, (docker_id, ))
            rslt = cursor.fetchone()
            cursor.close()
            conn.close()
            if cnt != 1:
                return (None, '{0} row(s) has been found!'.format(cnt))
            return (rslt, "success")
    return (None, "Param Error.")


def remove_service_instance(docker_id):
    try:
        conn = MySQLdb.connect(host=MYSQL_HOST, user=MYSQL_USER, passwd=MYSQL_PASS, db=DATABASE)
    except Exception, e:
        return (False, str(e))
    else:
        cursor = conn.cursor()
        sql = 'delete from service_instance where dockerid=%s'
        params = (docker_id,)
        cursor.execute(sql, params)
        cursor.close()
        conn.commit()
        conn.close()
        return (True, "success")


def stop_router(service_id):
    if service_id is not None:
        try:
            conn = MySQLdb.connect(host=MYSQL_HOST, user=MYSQL_USER, passwd=MYSQL_PASS, db=DATABASE)
        except Exception, e:
            return (False, str(e))
        else:
            cursor = conn.cursor()
            sql = 'select * from service_router where service_id=%s'
            cnt = cursor.execute(sql, (service_id, ))
            if cnt == 1:
                rslt = cursor.fetchone()
                container_manager.delete(rslt[0])
            sql = 'delete from service_router where service_id=%s'
            cursor.execute(sql, (service_id, ))
            sql = 'update service set plugin_address=%s where id=%s'
            params = ('null', service_id)
            cursor.execute(sql, params)
            cursor.close()
            conn.commit()
            conn.close()
            return (True, "success")
    return (False, "Param Error.")


def has_router(service_id):
    if service_id is not None:
        try:
            conn = MySQLdb.connect(host=MYSQL_HOST, user=MYSQL_USER, passwd=MYSQL_PASS, db=DATABASE)
        except Exception, e:
            return (False, str(e))
        else:
            cursor = conn.cursor()
            sql = 'select * from service_router where service_id=%s'
            cnt = cursor.execute(sql, (service_id, ))
            rslt = cursor.fetchone()
            cursor.close()
            conn.close()
            if cnt != 1:
                return (False, '{0} row(s) has been found!'.format(cnt))
            return (True, "success")
    return (False, "Param Error.")


def get_router(service_id):
    if service_id is not None:
        try:
            conn = MySQLdb.connect(host=MYSQL_HOST, user=MYSQL_USER, passwd=MYSQL_PASS, db=DATABASE)
        except Exception, e:
            return (False, str(e))
        else:
            cursor = conn.cursor()
            sql = 'select * from service_router where service_id=%s'
            cnt = cursor.execute(sql, (service_id, ))
            rslt = cursor.fetchone()
            cursor.close()
            conn.close()
            if cnt != 1:
                return (None, '{0} row(s) has been found!'.format(cnt))
            return (rslt, "success")
    return (False, "Param Error.")


def add_router(service_id, router):
    if service_id is not None and router is not None:
        try:
            conn = MySQLdb.connect(host=MYSQL_HOST, user=MYSQL_USER, passwd=MYSQL_PASS, db=DATABASE)
        except Exception, e:
            return (False, str(e))
        else:
            cursor = conn.cursor()
            sql = 'insert into service_router values (%s, %s, %s, %s, %s)'
            params = (router['dockerid'], router['domain'], router['port'], router['sshport'], service_id)
            cursor.execute(sql, params)
            sql = 'update service set plugin_address=%s where id=%s'
            params = ('{host}:{port}'.format(host=router['domain'], port=router['port']), service_id)
            cursor.execute(sql, params)
            cursor.close()
            conn.commit()
            conn.close()
            return (True, "success")
    return (False, "Param Error.")


def create_nginx_conf(service_path):
    src, dest, filename = './nginx_conf.tpl', NGINX_CONF_PREFIX + service_path, 'nginx.conf'
    if not path.exists(dest):
        makedirs(dest)
    copyfile(src, path.join(dest, filename))


def add_host_to_nginx_conf(service_path, host, port):
    original = NGINX_CONF_PREFIX + service_path + 'nginx.conf'
    tmp = NGINX_CONF_PREFIX + service_path + 'tmp'
    # pattern = r'\s*ip_hash;\n'
    pattern = r'\s*least_conn;\n'
    new_line = '        server {host}:{port};\n'.format(host=host, port=port)
    with open(original, 'r') as original_file:
        with open(tmp, 'w') as tmp_file:
            for line in original_file:
                tmp_file.write(line)
                if re.match(pattern, line):
                    tmp_file.write(new_line)
    rename(tmp, original)


def delete_host_from_nginx_conf(service_path, host, port):
    original = NGINX_CONF_PREFIX + service_path + 'nginx.conf'
    tmp = NGINX_CONF_PREFIX + service_path + 'tmp'
    pattern = r'\s*server {host}:{port};\n'.format(host=host, port=port)
    with open(original, 'r') as original_file:
        with open(tmp, 'w') as tmp_file:
            for line in original_file:
                if not re.match(pattern, line):
                    tmp_file.write(line)
    rename(tmp, original)


def delete_nginx_conf(service_path):
    target = NGINX_CONF_PREFIX + service_path + 'nginx.conf'
    if path.exists(target):
        remove(target)


@app.route('/run', methods=['GET', 'POST'])
def run():
    # parse params
    params = get_params(request)
    app_id = params.get('appid', default=None)
    user = params.get('user', default=None)
    mode = params.get('mode', default=None)
    extra = params.get('extra', default=None)
    # stop exsting instance
    status, msg = stop_if_exists(app_id)
    if not status:
        return make_reply(1, msg)
    # check privilege and get the info of app
    app, msg = get_app(app_id, user)
    if app is None:
        return make_reply(1, msg)
    app_name, app_type, owner = app
    app_path = make_app_path(app_name, app_type, owner)
    # run container
    if mode is not None:
        app_type = '%s-%s' % (app_type, mode)
#    app_type = '{0}-debug'.format(app_type) if mode == 'debug' else app_type
    rslt = container_manager.json_to_obj(container_manager.run(app_type, app_path, extra))
    if rslt['code'] == '0':
        # save
        save_rslt = add_app_instance(app_id, rslt)
        docker_id = rslt['dockerid']
        if save_rslt[0]:
            # notice: job id is the same as docker id which this job is handling
            scheduler.add_job(check_live_time, 'interval', args=[datetime.now(), docker_id], seconds=30, id=docker_id)
            return container_manager.obj_to_json(rslt)
        container_manager.delete(docker_id)
        return make_reply(1, save_rslt[1])
    return container_manager.obj_to_json(rslt)


@app.route('/stop', methods=['GET', 'POST'])
def stop():
    # parse params
    params = get_params(request)
    docker_id = params.get('dockerid', default=None)
    if docker_id is None:
        return make_reply(1, 'Param Error.')
    container_manager.delete(docker_id)
    remove_rslt = remove_app_instance(docker_id)
    if remove_rslt[0]:
        make_reply(0, 'success')
    return make_reply(1, remove_rslt[1])


@app.route('/deploy', methods=['GET', 'POST'])
def deploy():
    # get parameters
    params = get_params(request)
    service_id = params.get('serviceid', default=None)
    if service_id is None:
        return make_reply(1, 'Param Error.')
    service, msg = get_service(service_id)
    if service is None:
        return make_reply(1, msg)
    # create a new instance of this service
    # stop all instances if there is any
    stop_all_instances(service_id)
    # create a totally new instance
    service_name, service_type, owner = service[1], 'tomcat', service[9]
    service_path = make_service_path(service_name, service_type, owner)
    rslt = container_manager.json_to_obj(container_manager.startservice(service_type, service_path))
    if rslt['code'] != '0':
        return container_manager.obj_to_json(rslt)
    # save this instance
    save_rslt = add_service_instance(service_id, rslt)
    if not save_rslt[0]:
        return make_reply(1, save_rslt[1])
    # get the host and port of this instance
    instance_host, instance_port = rslt['domain'], rslt['port']
    # create a router node for this service
    # check whether it already has router.
    # if so get the existing router, else create a new router
    stop_router(service_id)
    # set up conf file of nginx and start it
    create_nginx_conf(service_path)
    add_host_to_nginx_conf(service_path, instance_host, instance_port)
    service_type = 'nginx'
    router = container_manager.json_to_obj(container_manager.startservice(service_type, service_path))
    if router['code'] != '0':
        return container_manager.obj_to_json(router)
    save_rslt = add_router(service_id, router)
    if not save_rslt[0]:
        return make_reply(1, save_rslt[1])
    # store service info into table service_instance
    return container_manager.obj_to_json(router)


@app.route('/undeploy', methods=['GET', 'POST'])
def undeploy():
    # get parameters:
    params = get_params(request)
    service_id = params.get('serviceid', default=None)
    if service_id is None:
        return make_reply(1, 'Param Error.')
    service, msg = get_service(service_id)
    if service is None:
        return make_reply(1, msg)
    service_name, service_type, owner = service[1], 'tomcat', service[9]
    service_path = make_service_path(service_name, service_type, owner)
    # delete all related node including router
    stop_all_instances(service_id)
    stop_router(service_id)
    delete_nginx_conf(service_path)
    return make_reply(0, 'Success')


def do_create_instance(service_id):
    return do_append_instances(service_id, 1)

@app.route('/create_instance', methods=['GET', 'POST'])
def create_instance():
    # get parameters
    params = get_params(request)
    service_id = params.get('serviceid', default=None)
    if service_id is None:
        return make_reply(1, 'Param Error.')
    return do_create_instance(service_id)


def do_delete_instance(docker_id):
    container_manager.delete(docker_id)
    instance, msg = get_service_instance(docker_id)
    if instance is None:
        return make_reply(1, msg)
    instance_host, instance_port = instance[1], instance[2]
    service, msg = get_service(instance[4])
    service_name, service_type, owner = service[1], 'tomcat', service[9]
    service_path = make_service_path(service_name, service_type, owner)
    delete_host_from_nginx_conf(service_path, instance_host, instance_port)
    remove_service_instance(docker_id)
    return make_reply(0, 'success')


@app.route('/delete_instance', methods=['GET', 'POST'])
def delete_instance():
    # get parameters:
    # docker_id
    params = get_params(request)
    docker_id = params.get('dockerid', default=None)
    if docker_id is None:
        return make_reply(1, 'Param Error.')
    # delete the instance
    return do_delete_instance(docker_id)


if __name__ == "__main__":
    scheduler.start()
    app.run(host='0.0.0.0', port=9998, debug=True)
    scheduler.remove_all_jobs()
    scheduler.shutdown()
