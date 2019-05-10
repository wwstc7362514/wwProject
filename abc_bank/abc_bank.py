# -*- coding: utf-8 -*-

from PIL import Image
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchFrameException, UnexpectedAlertPresentException
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.keys import Keys
import base64, re, utils,datetime
import logging.config, config, logging
from mylog import *
from lxml import etree
import pymongo
import time
import winio

headers = {'X-Requested-With': 'XMLHttpRequest',
           'X-Prototype-Version': '1.6.1',
           'Accept': 'text/javascript, text/html, application/xml, text/xml, */*',
           'Content-type': 'application/x-www-form-urlencoded; charset=UTF-8',
           'Referer': 'https://ebanks.cgbchina.com.cn/perbank/welcome.do',
           'Accept-Language': 'en-US,en;q=0.8,zh-Hans-CN;q=0.5,zh-Hans;q=0.3',
           'Accept-Encoding': 'gzip, deflate',
           'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; WOW64; Trident/7.0; rv:11.0) like Gecko',
           'Cache-Control': 'no-cache'}


class Abc_bank:
    def __init__(self, proxy=None):
        desired_capabilities = webdriver.DesiredCapabilities.INTERNETEXPLORER.copy()
        if proxy:
            desired_capabilities['se:ieOptions'] = {'ie.usePerProcessProxy': True}
            desired_capabilities['proxy'] = {
                "proxyType": "manual",
                "httpProxy": proxy,
                "ftpProxy": proxy,
                "sslProxy": proxy
            }
        self.browser = webdriver.Ie(executable_path=config.iedriver, desired_capabilities=desired_capabilities)
        self.time_start = None
        self.time_end = None
        self.user_dict = {}

    def get_verify_img(self):
        """
        获取验证码
        :return: 验证码b64encode信息
        """
        logger.info('[ 获取验证码截图 ]')
        imgEle = self.browser.find_element_by_id('vCode')
        fn = utils.id_generator(10)
        self.browser.save_screenshot('pic/' + fn + '.png')
        if imgEle:
            location = imgEle.location
            size = imgEle.size
            if size['width'] < 2 or size['height'] < 2:
                logger.info('[ no img ]')
                return {'code':'10001','message':u'获取验证码失败'}
            im = Image.open('pic/' + fn + '.png')
            left = location['x']
            top = location['y']
            right = left + size['width']
            bottom = top + size['height']
            im = im.crop((int(left), int(top), int(right), int(bottom)))
            im.save('pic/' + fn + '2.png')
            with open('pic/' + fn + '2.png', "rb") as image_file:
                encoded_string = base64.b64encode(image_file.read())
                return encoded_string

    def test(self):
        self.browser.get("https://www.baidu.com/s?wd=ip")


    def first(self):
        """
        初次请求
        :return: 登陆状态码，验证码信息
        """
        self.browser.get("https://perbank.abchina.com/EbankSite/startup.do?")
        self.browser.maximize_window()

        #-----------二维码切换到账号密码登陆----------
        if utils.find_element(self.browser,By.ID,'loginChange',3):
            html = etree.HTML(self.browser.page_source)
            if "".join(html.xpath('//a[@id="loginChange"]/@title')) == '切换到用户名或K宝登录':
                self.browser.find_element_by_id("loginChange").click()

        if utils.find_element(self.browser,By.ID,'vCode',2):
            imgcode = self.get_verify_img()
            if imgcode:
                return {'code': '10000', 'img': imgcode.decode("utf-8")}
            else:
                return {'code': '99999', 'message': u'请求失败'}

    def login(self, user, pwd, captcha):
        """
        登陆功能模块
        :param user: 账号
        :param pwd: 密码
        :param captcha: 验证码
        :return: 登陆失败信息，插入数据库的总数据
        """
        logger.info('[ 开始登陆 ]')
        self.user = user
        try:
            if len(captcha) != 4:
                return {'code': '10001', 'message': u'验证码错误'}
            if len(pwd) > 12 or len(pwd) < 4 or len(user) > 30 or len(user) < 4:
                return {'code': '6', 'message': u'账号或者密码错误'}

            user_ele = self.browser.find_element_by_id('username')
            user_ele.clear()
            user_ele.send_keys(user)

            import pyautogui
            pyautogui.FAILSAFE = True
            #1366*768屏幕分辨率
            # X = 1050
            # Y = 375
            #1920*1080屏幕分辨率
            X = 1300
            Y = 370
            pyautogui.click(x=X,y=Y)

            for i in pwd + '  ':
                time.sleep(0.1)
                winio.key_down(0x0E)
                winio.key_up(0x0E)

            #输入密码
            winio.key_input_word(pass_word=pwd)

            if utils.find_element(self.browser,By.ID,'code',2):
                p_tag = self.browser.find_element_by_id('code')
                p_tag.send_keys(captcha)

            #记录账号密码，用于多卡号记录
            self.user_dict = {'user':user,'pwd':pwd}

            utils.find_element(self.browser, By.XPATH, '//span[@id="imgError"]', 3)
            if 'v-code-error wrong' in self.browser.page_source:
                logger.info('[ 图形验证码错误，重新截图 ]')
                imgcode = self.get_verify_img()
                if imgcode:
                    return {'code': '4', 'message': u'图形验证码错误，重新输入', 'img': imgcode.decode("utf-8")}

            elif 'v-code-error right' in self.browser.page_source:
                # p_tag.send_keys(Keys.TAB)
                # p_tag.send_keys(Keys.ENTER)
                js = 'document.getElementsByClassName("m-uersbtn")[0].click()'
                self.browser.execute_script(js)

                #登陆错误在这
                if not utils.find_element(self.browser,By.XPATH,'//form[@id="userNameForm"]/div[5]/@title',3):
                    if '密码错误' in self.browser.page_source:
                        return {'code': '6', 'message': u'密码错误'}
                    elif '[ABCI86]密码已锁定' in self.browser.page_source:
                        return {'code': '15', 'message': u'您的查询密码输错次数已满，密码已被锁定'}
                    elif '[UUP012]手机号不存在' in self.browser.page_source or '[UUP005]该用户名不存在' in self.browser.page_source \
                            or '[ABCI19]帐户未注册渠道服务或已注销' in self.browser.page_source or '[AB3806]该证件在系统中未登记' \
                            in self.browser.page_source or '用户名包含不合法字符' in self.browser.page_source:
                        return {'code': '20', 'message': u'帐户未注册渠道服务或已注销，请到银行官网注册后登陆'}
                    elif '[4301]重复提交表单或页面已过期' in self.browser.page_source:
                        return {'code': '8', 'message': u'您长时间未操作，连接超时，请重新尝试'}
                    elif '密码为空' in self.browser.page_source:
                        logger.info('[ 密码没输进去 ]')
                        return {'code': '9997', 'message': u'密码为空'}

                p = self.browser.window_handles
                self.browser.switch_to.window(p[0])
                time.sleep(2.5)

                # --------逻辑更改短信验证码分两路走-----------
                if u'获取验证码' in self.browser.page_source:
                    self.sms_send()
                    return {'code': '10', 'message': u'短信验证码已发送'}
                else:
                    return self.data_db(user)

        except NoSuchFrameException:
            logger.info('[ 登陆错误 login ]')
            return {'code': '10001', 'message': user}
        except TimeoutException:
            logger.info('[ 登陆超时 login ]')
            return {'code': '10003', 'message': u'获取账单超时'}

    def login_again(self, captcha, user):
        """
        图片验证码再次输入登陆
        :return: 
        """
        logger.info('[ 再次输入图片验证码 ]')
        try:
            if len(captcha) != 4:
                return {'code': '4', 'message': u'图形验证码输入错误'}
            p_tag = self.browser.find_element_by_id('code')
            p_tag.clear()
            p_tag.send_keys(captcha)

            js = 'document.getElementsByClassName("m-uersbtn")[0].click()'
            self.browser.execute_script(js)

            if utils.find_element(self.browser, By.XPATH, '//span[@id="imgError"]', 3):
                if 'v-code-error wrong' in self.browser.page_source:
                    return {'code':'11','message':'操作频繁，请稍后再试'}

            if not utils.find_element(self.browser, By.XPATH, '//form[@id="userNameForm"]/div[5]/@title', 3):
                if '密码错误' in self.browser.page_source:
                    return {'code': '6', 'message': u'密码错误'}
                elif '[ABCI86]密码已锁定' in self.browser.page_source:
                    return {'code': '15', 'message': u'您的查询密码输错次数已满，密码已被锁定'}
                elif '[UUP012]手机号不存在' in self.browser.page_source or '[UUP005]该用户名不存在' in self.browser.page_source \
                        or '[ABCI19]帐户未注册渠道服务或已注销' in self.browser.page_source or '[AB3806]该证件在系统中未登记' \
                        in self.browser.page_source or '用户名包含不合法字符' in self.browser.page_source:
                    return {'code': '20', 'message': u'帐户未注册渠道服务或已注销，请到银行官网注册后登陆'}
                elif '[4301]重复提交表单或页面已过期' in self.browser.page_source:
                    return {'code': '8', 'message': u'您长时间未操作，连接超时，请重新尝试'}
                elif '密码为空' in self.browser.page_source:
                    logger.info('[ 密码没输进去 ]')
                    return {'code': '9997', 'message': u'密码为空'}

            s = self.browser.window_handles
            self.browser.switch_to.window(s[0])

            # --------逻辑更改短信验证码分两路走--3/27---------
            if utils.find_element(self.browser,By.XPATH,'//a[@id="dynamicPswText_sendSms"]/span',3):
                self.sms_send()
                return {'code': '1', 'message': u'需要短信验证码'}
            else:
                return self.data_db(user)
        except Exception as e:
            logger.info(e)
            return {'code': '11', 'message': u'操作频繁，请稍后再试'}

    def data_db(self, user):
        """
        登陆到主页面后，提取数据主要逻辑在这个下面，长链接
        :param user: 登陆名
        :return: 封装好的data数据集合
        """
        logger.info('[ 开始提取数据 ]')
        try:
            h = self.browser.window_handles
            self.browser.switch_to.window(h[0])

            # 短信验证登陆后会有导航提示弹窗，关掉
            if utils.find_element(self.browser, By.XPATH, '//i[@class="intro-close"]', 3):
                intro = self.browser.find_element_by_xpath('//i[@class="intro-close"]')
                intro.click()

            if utils.find_element(self.browser, By.XPATH, '//div[@class="popbox-mine m-mine"]/a', 2):
                my_btn = self.browser.find_element_by_xpath('//div[@class="popbox-mine m-mine"]/a')
                my_btn.click()

            if utils.find_element(self.browser, By.XPATH,'//div[@class="popbox-mine m-mine"]//ul/li[@class="my-info"]/a', 2):
                m_info_btn = self.browser.find_element_by_xpath('//div[@class="popbox-mine m-mine"]//ul/li[@class="my-info"]/a')
                m_info_btn.click()

            utils.switch_frame(self.browser, 'index.do')
            p_html = self.browser.page_source

        except NoSuchFrameException:
            logger.info('[ 登陆错误 data_db ]')
            return {'code': '10001', 'message': user}

        except TimeoutException:
            logger.info('[ 登陆超时 data_db ]')
            return {'code': '10003', 'message': u'获取账单超时 data_db'}
        except Exception:
            return {'code': '99990', 'message': u'请求失败'}

        info = {"bankCode": "ABC",
                "bankName": u"农业银行",
                "login_account": user,
                "bill_date": None,
                "current_bill_remain_amt": None,
                "id_card": None,
                "bill_address": None,
                "crawl_user_phone": None,
                "card_no": None,
                "balance": None,
                "name": None,
                "credit_limit": None,
                "cash_balance":None,
                "payment_due_date": None,
                "complement_card_no": None,
                "login_account_type": utils.get_account_type(user),
                "reckoningSurveyNot": [{"enterBillNot": [],"enterBill": []}],
                "reckoningSurvey": [],
                "enterBill": [],
                "enterBillNot": [],
                }
        if info['login_account_type'] == '0':
            info['complement_card_no'] = user

        info = self.get_person_info(p_html, info)
        # 切回主文档
        self.browser.switch_to.default_content()
        info = self.card_info(info,user)
        data_info = self.get_detail_bill(info)
        data = {
            'code': '10000',
            'creditCardInfo': data_info,
            'submitTime': int(time.time()),
            'updTime': None
        }
        """程序结束前，删除保存的图片验证码"""
        img_path = config.img_path
        utils.delfile(img_path)
        #在爬虫脚本中关闭窗口会与flask冲突报异常，
        # self.browser.quit()

        return data

    def sms_send(self):
        """
        发送验证码
        :return: 发送短信给用户
        """
        # 发送验证码
        self.browser.find_element_by_xpath('//a[@id="dynamicPswText_sendSms"]/span').click()
        self.time_start = time.time()
        logger.info('[ 发送验证码时间：{} ]'.format(self.time_start))
        # 关掉短信验证码已发送弹窗
        try:
            WebDriverWait(self.browser, 15).until(EC.alert_is_present())
            alert = self.browser.switch_to.alert
            txt = alert.text
            alert.accept()
            return {'code': '1', 'message': txt}
        except UnexpectedAlertPresentException:
            return {'code': '10001', 'message': u'发送短信验证码错误'}

    def sms_login(self, sms_captcha):
        """
        从客户端获取验证码
        :param sms_captcha: 
        :return: 
        """
        logger.info('[ 用户已输入短信验证码，正在登陆 ]')
        try:
            if sms_captcha:
                self.time_end = time.time()
                logger.info('[ 填写验证码时间：{} ]'.format(self.time_end))
                if self.time_end - self.time_start > 70:
                    return {'code': '8', 'message': u'您长时间未操作，验证码已失效'}
                else:
                    h = self.browser.window_handles
                    self.browser.switch_to.window(h[0])
                    if len(sms_captcha) != 6:
                        return {'code': '3', 'message': u'短信验证码错误'}

                    if utils.find_element(self.browser,By.ID,'dynamicPswText',2):
                        sms_input = self.browser.find_element_by_id('dynamicPswText')
                        sms_input.send_keys(sms_captcha)

                    if utils.find_element(self.browser,By.ID,'orangeBtn',2):
                        sms_button = self.browser.find_element_by_id('orangeBtn')
                        sms_button.click()

                    if '验证码已失效' in self.browser.page_source:
                        return {'code': '8', 'message': u'您长时间未操作，验证码已失效'}

                    h = self.browser.window_handles
                    self.browser.switch_to.window(h[0])
                    if utils.find_element(self.browser,By.XPATH,'//div[@class="tip-error text-center"]/h3',3):
                        return {'code':'10004','message':u'验证码输入有误'}

                    return self.data_db(self.user)
        except Exception:
            return {'code': '3', 'message': u'短信验证码错误'}

    def get_detail_bill(self, info):
        """
        每个月的详情账单
        :param info: 数据字典
        :return: 数据字典
        """
        logger.info('[ 获取半年月账单信息 ]')
        try:
            #点击查询账单
            s_bill_btn = utils.find_element(self.browser, By.XPATH,
                                            '//ul[@id="m-hover-ul"]/li/div[@class="zhanghu_a"]/a[1]', 5)
            s_bill_btn.click()
            #查询当月未出账单

            if utils.find_element(self.browser,By.CLASS_NAME,'m-nobills',2):
                m_nobills_btn = self.browser.find_element_by_class_name('m-nobills')
                m_nobills_btn.click()

            #未出账单信息
            if utils.find_element(self.browser,By.XPATH,'//div[@id="TB_BIL"]/div/div[1]',2):
                html = etree.HTML(self.browser.page_source)
                enterBillNot_data = {}
                for i in html.xpath('//div[@id="TB_BIL"]/div')[1:]:
                    #交易日期
                    d_str = "".join(i.xpath('./div[1]/text()'))
                    enterBillNot_data['transactionDate'] = utils.format_date(d_str)
                    #入账日期
                    d_str = "".join(i.xpath('./div[1]/text()'))
                    enterBillNot_data['billingDate'] = utils.format_date(d_str)
                    #描述
                    enterBillNot_data['description'] = "".join(i.xpath('./div[4]/text()'))
                    #明细金额
                    enterBillNot_data['rmb_amount'] = "".join(i.xpath('./div[6]/text()')).strip().split('/')[0]
                info['reckoningSurveyNot'][0]['enterBillNot'].append(enterBillNot_data)
            else:
                info['reckoningSurveyNot'][0]['enterBillNot'] = []

            if utils.find_element(self.browser,By.CLASS_NAME,'button-table',2):
                back_btn = self.browser.find_element_by_class_name('button-table')
                back_btn.click()

            # 点击查询账单
            s_bill_btn = utils.find_element(self.browser, By.XPATH,
                                            '//ul[@id="m-hover-ul"]/li/div[@class="zhanghu_a"]/a[1]', 5)
            s_bill_btn.click()

            time.sleep(1)
            select = self.browser.find_element_by_id('m_select1')
            # 取出所有select元素，判断是否有六个月账单
            options_list = select.find_elements_by_tag_name('option')
            s_list = len(options_list)
            page_num = 1
            if s_list >= 6:
                page_num += 6
            else:
                page_num = s_list + 1
            month_list = info['reckoningSurvey']
            p_num = 1
            for i in range(1, page_num):
                s_btn = utils.find_element(self.browser, By.XPATH, '//div[@id="m-billmonthdiv"]//b[@class="button"]', 5)
                s_btn.click()
                time.sleep(0.2)
                index_btn = self.browser.find_element_by_xpath(
                    '//div[@class="selectric-items"]/div/ul/li[{}]'.format(i))
                index_btn.click()

                if utils.find_element(self.browser,By.ID,'TB_COM_DETAIL_TT',1.5):
                    html = etree.HTML(self.browser.page_source)
                    p_num += 1
                    month_data = {}

                    month_data['month'] = "".join(html.xpath('//select/option[{}]/text()'.format(i))).strip().replace(
                        '/', '-')
                    # 账单日
                    m_str = "".join(html.xpath('//select/option[{}]/@value'.format(i))).strip()
                    month_data['month_bill_date'] = utils.format_date(m_str)
                    # 逾期还款日
                    d_str = "".join(html.xpath('// div[ @ id = "m-repaymentdatediv"] / text()')).strip().split('：')[-1]
                    month_data['month_payment_due_date'] = utils.format_date(d_str)
                    # 当月新增还款金额
                    new_str = "".join(html.xpath('//div[@class="m-accountingnumber bor_all"]/div[2]/text()')).strip()
                    month_data['month_new_balance'] = float(new_str)
                    # 当月还款金额
                    k_str = "".join(html.xpath('//div[@class="m-detailedbottom bor_all"]/div[2]/text()')).strip()
                    month_data['month_bill_amt'] = float(k_str)
                    # 当月账单最低还款金额
                    j_str = "".join(html.xpath('//div[@class="m-detailedbottom bor_all"]/div[3]/text()')).strip()
                    month_data['month_min_payment'] = float(j_str)

                    month_data['details'] = []
                    for i in html.xpath('//div[@id="TB_COM_DETAIL"]/div')[1:]:
                        d_data = {}
                        # 记账日期
                        m_str = "".join(i.xpath('./div[2]/text()')).strip()
                        d_data['billingDate'] = utils.format_date(m_str)
                        # 交易日期
                        l_str = "".join(i.xpath('./div[1]/text()')).strip()
                        d_data['transactionDate'] = utils.format_date(l_str)
                        # 明细金额
                        f_str = "".join(i.xpath('./div[5]/text()')).strip()
                        d_data['rmb_amount'] = f_str
                        # 交易描述
                        d_data['description'] = "".join(
                            i.xpath('./div[3]/text()')).strip()

                        month_data['details'].append(d_data)

                    if month_data == {}:
                        pass
                    else:
                        month_list.append(month_data)

            return info
        except NoSuchFrameException:
            logger.info('[ get_detail_bill error ]')
            return {'code': '10001', 'message': u'获取账单失败'}
        except TimeoutException:
            logger.info('[ get_detail_bill 超时 ]')
            return {'code': '10003', 'message': u'获取账单超时'}

    def card_info(self, info,user):
        """
        卡片和当月账单信息
        :param info: info数据字典
        :return: 数据字典
        """
        logger.info('[ 获取当月账单信息 ]')
        try:
            card_btn = self.browser.find_element_by_xpath('//div[@id="menuNav"]/ul/li[7]')
            card_btn.click()
            time.sleep(0.5)
            card_select_btn = self.browser.find_element_by_xpath(
                '//div[@id="menuNav"]/ul/li[7]/ul/li[1]')
            card_select_btn.click()
            # 切进iframe
            utils.switch_frame(self.browser, 'CreditCardQryInitAct.do')
            if utils.find_element(self.browser, By.CLASS_NAME, 'jia', 5):
                jia = utils.find_element(self.browser, By.CLASS_NAME, 'jia', 5)
                jia.click()
                card_html = etree.HTML(self.browser.page_source)
                # --------记录持卡2张以上的用户--------
                if len(card_html.xpath('//ul[@id="m-hover-ul"]/li/a')) > 2:
                    with open('many_card_user.txt', 'a', encoding='utf-8') as f:
                        f.write('user: ' + user + '  ' + 'pwd: ' + self.user_dict[
                            'pwd'] + '  ' + datetime.datetime.now().strftime('%Y.%m.%d-%H:%M:%S') + '\n')
                    self.user_dict.clear()
                    #--------取出所有卡号，以下面格式返回--------
                    # return {"code" : 18,"cards" : ["111122222","232323232"]}

                # 卡号
                card_no = "".join(card_html.xpath('//ul[@id="m-hover-ul"]/li/span[1]/text()'))
                # 逾期还款日
                payment_due_date = "".join(card_html.xpath('//ul[@id="m-hover-ul"]/li/span[last()]/text()')).strip()
                # 当前账单剩余还款金额
                current_bill_remain_amt = "".join(card_html.xpath('//ul[@id="m-hover-ul"]/li/span[3]/text()'))
                # 切进iframe取弹框的值
                utils.switch_frame(self.browser, 'CreditCardQryInitAct.do')
                html = self.browser.page_source
                # 信用额度
                credit_limit = re.findall(r'detail.credAmt">(.*?)</span>', html, re.S)[0]
                # 当前账户余额
                balance = re.findall(r'detail.availAmt">(.*?)</span>', html, re.S)[0]
                #取现额度
                cash_balance = re.findall(r'detail.availCashAmt">(.*?)</span>',html,re.S)[0].strip() if re.findall(r'detail.availCashAmt(.*?)</span>',html,re.S) else None
                #账单日暂时没找到，用逾期还款日返回
                info['bill_date'] = utils.format_date(payment_due_date)
                #账单地址没找到，暂时返回-1
                info['bill_address'] = -1

                info['card_no'] = card_no
                info['complement_card_no'] = card_no
                info['credit_limit'] = float(credit_limit)
                info['payment_due_date'] = utils.format_date(payment_due_date)
                info['balance'] = float(balance)
                info['current_bill_remain_amt'] = float(current_bill_remain_amt)
                info['cash_balance'] = float(cash_balance)

                return info
            else:
                return {'code':'16','message':u'您的名下不存在信用卡'}
        except NoSuchFrameException:
            logger.info('[ card_info error ]')
            return {'code': '10001', 'message': u'获取账单失败'}
        except TimeoutException:
            logger.info('[ card_info 超时 ]')
            return {'code': '10003', 'message': u'获取账单超时'}

    def get_person_info(self, html, info):
        """
        获取个人信息
        :param html:个人信息页面html 
        :param info: 数据字典
        :return: info数据字典
        """
        logger.info('[ 获取个人详情页信息 ]')
        try:
            if html:
                p_html = etree.HTML(html)
                # 姓名
                name = "".join(p_html.xpath('//div[@class="g-container"]//table//tr[1]/td[last()]/text()')).strip()
                # 身份证
                if "".join(p_html.xpath('//div[@class="g-container"]//table//tr[2]/td[2]/text()')).strip() == '居民身份证':
                    id_card = "".join(
                        p_html.xpath('//div[@class="g-container"]//table//tr[2]/td[last()]/text()')).strip()
                else:
                    id_card = None
                # 用户手机
                crawl_user_phone = "".join(p_html.xpath('//div[@class="g-container"]//table//tr[8]/td[2]/text()'))
                if '1' in crawl_user_phone:
                    if '-' in crawl_user_phone:
                        u_phont = crawl_user_phone.split('-')[-1].strip()
                        info['crawl_user_phone'] = u_phont
                    else:
                        info['crawl_user_phone'] = crawl_user_phone
                else:
                    info['crawl_user_phone'] = None
                info['name'] = name
                info['id_card'] = id_card

                return info
        except NoSuchFrameException:
            logger.info('[ get_person_info error ]')
            return {'code': '10001', 'message': u'获取账单失败'}
        except TimeoutException:
            logger.info('[ get_person_info 超时 ]')
            return {'code': '10003', 'message': u'获取账单超时'}

    def script_click(self, xpath):
        """
        js操作xpath进行click
        :param xpath:
        :return:
        """
        self.browser.execute_script('document.evaluate("%s", document).iterateNext().click();' % xpath)


    def insert(self, info):
        """本地测试"""
        client = pymongo.MongoClient('localhost', 27017)
        mydb = client['test']
        mysql = mydb['CreditCardinfoCol']
        mysql.insert(info)
        print('插入成功')

# if __name__ == '__main__':
#
#         proxy = None
#         g = Abc_bank(proxy)
#
#         r1 = g.first()
#         print(r1)
#
#         captcha = input("captcha?")
#         d1 = datetime.now()
#
#         r2 = g.login('17095118656', '10221408', captcha)
#         print(r2)
#
#
#         sms_code = input("sms_captcha?")
#         r3 = g.sms_login(sms_code)
#         print(r3)
#         s = (datetime.now() - d1).seconds
#         print(s)
