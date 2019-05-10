# -*- coding: utf-8 -*-

from flask import Flask
from flask import request, jsonify
import time,threading
from abc_bank import Abc_bank
from mylog import *
from pymongo import MongoClient
from selenium.common.exceptions import ElementNotInteractableException

logger.info("[ abc_bank 服务已启动 ]")

app = Flask(__name__)
cache = {}
cache_list = []

mongoUrl = 'mongodb://bank:FKTup618bd@47.98.10.219:3717/bank?maxPoolSize=10'
mongoDB = 'bank'

@app.route('/bank2/test', methods=['GET'])
def index():
    return 'hello'


def get_value(d, k):
    if d and k and k in d:
        return d[k]


def del_timeout_user():
    global cache_list
    logger.info("[ 监控异常登陆线程 {} start ]".format(threading.current_thread()))
    while True:
        time.sleep(5)
        try:
            if cache_list:
                for data in cache_list:
                    if cache != {}:
                        if cache[data['k']][0] == data['g']:
                            if time.time() - data['t1'] > 300:
                                db = MongoClient(mongoUrl)[mongoDB]
                                db.NodeCol.update_many({'bank': data['bank_name'], 'user': data['user']},
                                                       {'$unset': {'user': 0, 'time': 0}})
                                logger.info("[ 用户: {} 'ip: {}' 长时间未操作，已主动关闭浏览器，清空服务器 user,time 数据]"\
                                            .format(data['user'],data['ip']))
                                with open('del_timeout_user.txt','a',encoding='utf-8')as f:
                                    f.write(datetime.datetime.now().strftime('%Y.%m.%d-%H:%M:%S') + ' '*2 + data['user']\
                                            + ' ' + data['ip'] + '\n')
                                if cache != {}:
                                    data['g'].browser.quit()
                                cache_list.clear()
                        else:
                            data['g'].browser.quit()
                            cache_list.remove(data)
                    else:
                        cache_list.clear()
                        pass
        except Exception as e:
            logger.error("[ error 监控模块异常 {}]".format(e),exc_info=True)
            logger.info("[ cache:{}  cache_list:{} ]".format(cache,cache_list))
            pass
t = threading.Thread(target=del_timeout_user)
t.start()

def finish(bank_name, user):
    global cache_list
    if not bank_name or not user:
        return
    try:
        db = MongoClient(mongoUrl)[mongoDB]
        db.NodeCol.update_many({'bank': bank_name, 'user': user}, {'$unset': {'user': 0, 'time': 0}})
        k = bank_name + '|' + user
        if k in cache and cache[k]:
            cache[k][0].browser.quit()
            del cache[k]
    except :
        logger.error('[ error finish]', exc_info=True)


# def cleanCache():
#     if cache:
#         try:
#             db = MongoClient(mongoUrl)[mongoDB]
#             t2 = time.time()
#             for k in list(cache):
#                 if t2 - cache[k][1] > 320:
#                     k2 = k.split('|')
#                     db.NodeCol.update_many({'bank': k2[0], 'user': k2[1]}, {'$unset': {'user': 0, 'time': 0}})
#                     cache[k][0].browser.quit()
#                     del cache[k]
#         except:
#             logger.error('error cleanCache {}'.format(cache), exc_info=True)

@app.route('/bank2/abc', methods=['POST'])
def abc_bank():
    t1 = time.time()
    try:
        data = request.get_json(force=True)
        bank_name = 'abc'
        logger.info('[ abc %s ]', data)
        user = get_value(data, 'username')
        pwd = get_value(data, 'password')
        mc = get_value(data, 'messagecode')
        mc1 = get_value(data,'messagecode_again')
        sms = get_value(data,'smscode')
        proxy = get_value(data, 'proxy')
        k = bank_name + '|' + user

        if sms:
            if k in cache and cache[k]:
                g = cache[k][0]
                try:
                    rtn = g.sms_login(sms)
                    finish(bank_name, user)
                    t2 = time.time()
                    logger.info('[ %s %s ]', t2 - t1, rtn)
                    return jsonify(rtn)
                except:
                    rtn = {'code': '10004', 'message': u'验证码输入有误'}
                    return jsonify(rtn)
                finally:
                    finish(bank_name,user)

        if mc:
            if k in cache and cache[k]:
                g = cache[k][0]
                try:
                    rtn = g.login(user, pwd, mc)
                    #验证码错了再次重新输入一次
                    if get_value(rtn,'img') and mc1:
                        rtn = g.login_again(mc1 , user)
                        time.sleep(0.2)
                        if rtn['code'] == '1' or rtn['code'] == '4':
                            pass
                        else:
                            finish(bank_name, user)
                        t4 = time.time()
                        logger.info('[ 返回数据用时:%s %s ]', t4 - t1, rtn)
                        return jsonify(rtn)
                    #图片验证码和短信验证码都没错，会直接返回最终结果
                    time.sleep(0.2)
                    if rtn['code'] == '1' or rtn['code'] == '4' or rtn['code'] == '10':
                        pass
                    else:
                        finish(bank_name, user)
                    t2 = time.time()
                    logger.info('[ 返回数据用时:%s %s ]', t2 - t1, rtn)
                    return jsonify(rtn)
                except :
                    logger.error('[ error ]' + user, exc_info=True)
                    rtn = {'code': '99999', 'message': u'请求失败'}
                    finish(bank_name, user)
                    return jsonify(rtn)

        else:
            #记录来访IP,User-Agent
            logger.info(["用户: {}  IP 地址: {}".format(user,request.remote_addr)])
            logger.info(["User-Agent: {}".format(request.headers.get("User-Agent"))])

            # cleanCache()
            g = Abc_bank(proxy)
            cache[k] = (g, time.time())
            cache_list.append({'bank_name': bank_name, 'user': user, 'k': k, 'g': g, 't1': time.time(),'ip':request.remote_addr})
            rtn = g.first()
            t2 = time.time()
            logger.info('[ 返回图片验证码用时:%s ]', t2 - t1)
            return jsonify(rtn)

    except:
        # finish(bank_name,user)
        rtn = {'code': '99998', 'message': u'请求失败'}
        return jsonify(rtn)


if __name__ == '__main__':
    app.run(host='127.0.0.1',port=9000)
