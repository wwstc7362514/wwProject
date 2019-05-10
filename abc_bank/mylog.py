# -*- coding: utf-8 -*-
import logging.config
import logging
import datetime
import os
from logging.handlers import RotatingFileHandler


file_name = datetime.datetime.now().strftime('%Y-%m-%d')
#本地
file_path = os.getcwd()+'/logs/' + file_name
#线上
# file_path = '/store/logs/bsd-credit-card-py/' + file_name

if not os.path.exists(file_path):
    os.makedirs(file_path)

#本地
LOG_FILENAME = os.getcwd()+'/logs/{}/abc.log'.format(datetime.datetime.now().strftime('%Y-%m-%d'))
#线上
# LOG_FILENAME = '/store/logs/bsd-credit-card-py/{}/credit_card.log'.format(datetime.datetime.now().strftime('%Y-%m-%d'))
logger = logging.getLogger("abc")
logger.setLevel(logging.DEBUG)
#日志按大小分割
handler = RotatingFileHandler(LOG_FILENAME, encoding='UTF-8', maxBytes=1024 * 1024 * 10,backupCount=100)
#日志级别
handler.setLevel(logging.INFO)
# handler.setLevel(logging.DEBUG)

logging_format = logging.Formatter(
    '%(asctime)s - %(levelname)s - %(filename)s - %(funcName)s - %(lineno)s - %(message)s')

handler.setFormatter(logging_format)
logger.addHandler(handler)
#输出到屏幕
console = logging.StreamHandler()
console.setLevel(logging.INFO)
console.setFormatter(logging_format)
logger.addHandler(console)

