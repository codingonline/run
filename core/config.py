#!/usr/bin/env python
# encoding: utf-8

# configuration for mysql server
MYSQL_HOST='rdsj7nhfyy0syt1fw980.mysql.rds.aliyuncs.com'
MYSQL_USER='useradmin'
MYSQL_PASS='useradmin'
DATABASE='pop2016'

# time limit for one app in minutes
TIME_LIMIT = 10

# target dir for nginx conf files
NGINX_CONF_PREFIX = '/root/data/nginx_conf'

# minimum interval for deciding whether to scale up or down
MIN_SCALING_INTERVAL = 1
# no scaling operations will be allowed within this interval
MIN_STABLE_INTERVAL = 3
