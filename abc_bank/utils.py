# -*- coding: utf-8 -*-

import string, random, re, time
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
import logging
import os , glob

logger = logging.getLogger()


def format_date(d):
    return d[:4] + '-' + d[4:6] + '-' + d[6:]


def get_value(d, k):
    if d and k and k in d:
        return d[k]


def id_generator(size):
    chars = string.ascii_lowercase
    return ''.join(random.choice(chars) for _ in range(size))


def get_account_type(a):
    if re.match(r'^1\d{10}$', a):
        return '2'
    elif re.match(r'^\d{15}$', a):
        return '1'
    elif re.match(r'^\d{17}[0-9Xx]$', a):
        return '1'
    elif re.match(r'^\d{16}$', a):
        return '0'
    else:
        return '3'


def find_element(browser, by, v, time=3):
    try:
        return WebDriverWait(browser, time).until(EC.visibility_of_element_located((by, v)))
    except TimeoutException:
        logger.info('no element ' + v)


def switch_frame(browser, flag):
    browser.switch_to.default_content()
    time.sleep(1)
    iframes = browser.find_elements_by_tag_name('iframe')
    if iframes:
        for iframe in iframes:
            if flag in iframe.get_attribute('src'):
                browser.switch_to.frame(iframe)
                break


def delfile( img_path):
    fileNames = glob.glob(img_path + r'\*')
    for fileName in fileNames:
        try:
            os.remove(fileName)
        except:
            try:
                os.rmdir(fileName)
            except:
                delfile(fileName)
                os.rmdir(fileName)

