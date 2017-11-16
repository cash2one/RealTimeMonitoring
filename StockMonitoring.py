# -*- coding: utf-8 -*-
"""
Created on Fri May 19 09:41:33 2017

@author: MoBeiHuYang
"""
import time, datetime
import tushare as ts
import WeChatFuncs as WeChat
import random
import pickle
import threading  # 用于多线程工作

class TStockMonitor:
    #----------------------------- 实例间共享变量定义（一个实例中变化，其它实例也会变化 ----------------------------------#
    __Author__ = 'FlameMan'
    Master = {'Master':{'UserName':'', 'NickName':'FlameMan'}}
    __ALERTMAX__ = 3
    SendWebChat = 1
    sleeptime_onduty = 1
    sleeptime_offduty = 3
    label = ' # 股票实时监控程序 # '
    maxUserNum = 5
    #--------------------------------------------------------------------------#
    # for time control
    kHr = 0
    kMin = 1
    kSec = 2
    kPeriod1 = 0
    kPeriod2 = 1
    starttime = [[9, 30, 0], [13, 0, 0]] # open time
    endtime =   [[11,30, 0], [15, 0, 0]] # close time
    #--------------------------------------------------------------------------#    
    initMsg = '股票实时监控工具 by ' + str(__Author__) + ' 上线！监控时间为：' + \
    str('%02d' % starttime[kPeriod1][kHr]) + ':' + str('%02d' %starttime[kPeriod1][kMin]) + ':' + str('%02d' %starttime[kPeriod1][kSec]) + ' -- ' + \
    str('%02d' %endtime[kPeriod1][kHr]) + ':' + str('%02d' %endtime[kPeriod1][kMin]) + ':' + str('%02d' %endtime[kPeriod1][kSec]) + '， ' + \
    str('%02d' %starttime[kPeriod2][kHr]) + ':' + str('%02d' %starttime[kPeriod2][kMin]) + ':' + str('%02d' %starttime[kPeriod2][kSec]) + ' -- ' +\
    str('%02d' %endtime[kPeriod2][kHr]) + ':' + str('%02d' %endtime[kPeriod2][kMin]) + ':' + str('%02d' %endtime[kPeriod2][kSec]) + '。 '
    extMsg = '股票实时监控工具下线，管理员正在处理。有急事请联系管理员：18910241406！'
# 股票信息
    def __init__(self,callName, nickName, mhotReload):
        """
        Created on Fri May 19 09:45:52 2017
        @author: MoBeiHuYang
        在构造函数中，针对主要变量进行初始化
        1. 打印该舆论监控工具的上线信息
        2. 初始化Master的微信账号
        3. 初始化User的微信账号
        4. 获取股票的初始信息
        5. 如果是热启动，读取上次监控股票列表
        Created on Fri May 19 09:45:52 2017
        @ author: MoBeiHuYang
        """
        #-------------------- 实例间不共享变量，实例间不会相互影响---------------------------#
        self.mainUser  = callName 
        self.prickleFileName = WeChat.pickle_dir + self.mainUser + '_Stock_热启动文件.pickle'    
        self.logfile = WeChat.log_dir + self.mainUser + '_Stock.log'
        self.f = open(self.logfile,'a+')
        # 用于多线程，进程锁    
        self.mu =  threading.RLock()   
        print(self.initMsg + ' 用户：' + str(callName))
        self.write2Log(self.initMsg + ' 用户：' + str(callName))
        self.ResSetFlag = False
        try:
            WeChat.InitWeChatUsers(self.Master, self.logfile) # 初始化管理员账号
        except Exception as e:
            errmsg = '# 股票监测类：管理员账号初始化异常： ' + str(e) 
            self.write2Log(errmsg)
            print(errmsg)
            raise Exception(errmsg)
        hotReload = False
        if mhotReload:
            hotReload, data = self.getDatafromPickle(self.prickleFileName)
        if mhotReload and hotReload:
            self.residDays = data['residDays']
            self.UserList = data['UserList']
            self.StockDic = data['StockDic']
            self.stockListInChina =data['stockListInChina']
            self.countor = data['countor']
        # 用于多线程，进程锁    
            #----------------------------------初始化微信账号----------------------------#
            try:
                WeChat.InitWeChatUsers(self.UserList, self.logfile) #初始化用户账号
 #               WeChat.SendWeChatMsgToUserList(self.UserList, self.initMsg, self.logfile)
            except Exception as e:
                errmsg = '# 股票监测类：用户初始化异常: ' + str(e) + '。已通知管理员处理！'
                self.SendAlert2Master(errmsg)
                raise Exception(errmsg)
                # log file    
        else:
            self.residDays = 365
            self.UserList = {}  #第一个默认为主账号，其余为副账号
            self.StockDic = {'sh':{'code':'sh', 'lowlimit':3000, 'highlimit':3300, 'Alertsent':0}, \
                     'sz':{'code':'sz', 'lowlimit':9000, 'highlimit':11000, 'Alertsent':0}}   
            self.stockListInChina = None
            self.HotStart = True
                # log file    
        #-------------------- 实例间不共享变量定义结束---------------------------#
            self.countor = 0   # 监控次数置为0
            self.UserList.setdefault(callName,{'UserName':'', 'NickName':nickName})  # 将主账户加入UserList
            print(self.printUserList())
    #----------------------------------初始化微信账号----------------------------#
            try:
                WeChat.InitWeChatUsers(self.UserList, self.logfile) #初始化用户账号
#                WeChat.SendWeChatMsgToUserList(self.UserList, self.initMsg, self.logfile)
            except Exception as e:
                errmsg = '# 股票监测类：用户初始化异常: ' + str(e) + '。已通知管理员处理！'
                self.SendAlert2Master(errmsg)
                raise Exception(errmsg)
    #----------------------------------初始化股票列表----------------------------#       
            try:
                df = self.Get_Stock_List()
                self.stockListInChina = list(df.index)
                self.stockListInChina.append('sh')
                self.stockListInChina.append('sz')
            except Exception as e:
                errmsg = '股票监测类：获取股市中股票列表异常：' + str(e)
                self.SendAlert2Master(errmsg)
                raise Exception(errmsg)
    def __del__(self):
       # self.Bye()
        print('Delete' + str(self.label))    
    def getMainUser(self):
        return self.mainUser     
    def Run(self):
        with self.mu:
            print('开始一次 ' + self.label)
            self.countResDays()
            if self.OnDuty():
                self.countor = self.countor + 1
                for code in self.StockDic.keys():
                    self.remind(code,self.countor) 
        #            time.sleep(self.sleeptime_onduty)  # sleep
            else:
                self.countor = 0
                tempstr = time.strftime("%Y-%m-%d %H:%M:%S") + ' I\'m sleeping now!'
                self.write2Log(tempstr)
            #    time.sleep(self.sleeptime_offduty)
            print('结束一次 ' + self.label)
    def Interaction(self, msg):
        self.write2Log('收到来自' + str(msg['User']['NickName'])+'的消息：\n\'' + str(msg['Text']) + '\'')
        cmd_temp = str(msg['Text']).lstrip().rstrip().split(' ')
        cmd = None
        if cmd_temp[0] == '股票':  #壁面用户重复的情况
            cmd = str(msg['Text'][2:len(msg['Text'])]).lstrip().rstrip()
        else:
            cmd = str(msg['Text']).lstrip().rstrip()
        
        sndmsg = str(self.label + '\n')
        if False:  # not self.OnDuty():
            if cmd[0:5] == 'getup':
                cmd = cmd[5:len(cmd)].lstrip()
                sndmsg = sndmsg + '连睡觉时间都不放过，真是个资本家！\n'
                WeChat.SendWeChatTextMsg(sndmsg, msg['FromUserName'], msg['User']['NickName'], self.logfile)
            else:
                sndmsg = sndmsg + 'I\'m sleeping now! You can do it by yourself！'
                WeChat.SendWeChatTextMsg(sndmsg, msg['FromUserName'], msg['User']['NickName'], self.logfile)
                return
        if len(cmd) < 1:
            sndmsg = sndmsg + '我看不懂你在说什么！'
            WeChat.SendWeChatTextMsg(sndmsg, msg['FromUserName'], msg['User']['NickName'], self.logfile)
            return
        sndmsg = str(self.label + '\n')
        cmd = cmd.split(' ')
        '''
    \'股票 h\'： \t获得这款工具的帮助文档。
    \'股票 l ShiRui\'： \t获得用户所在主用户ShiRui下监控股票的信息。
    \'股票 a ShiRui 300332 11.38 12.38\'： \t将300332股票加入用户所在主用户ShiRui下监控列表，后面依次为监控价格下限以及上限。如果列表中已经存在该股票，则用新的监控指标替代旧的数据。参数间用空格分隔。
    \'股票 r ShiRui 300332\'： \t将股票300332从监控列表中移出，如果列表中不存在该股票，则什么都不做。
    \'股票 m ShiRui 300332 11.38 12.38\'： \t修改监控股票300332的监控参数。参数间用空格分隔。
    \'股票 i ShiRui 300332\'： \t 获取股票300332的实时信息。
    \'股票 rs ShiRui 300332\'：\t重置股票300332的报警状态。
    \'股票 lu ShiRui \': \t 列出当前用户信息
    \'股票 收到 ShiRui 300332\'：\t 表明收到股票300332的预警信息，在下次更新预警参数或回归过正常状态之前，不会再发送提醒信息（ 10 ）条预警信息无回复，自动停止发送预警信息）。
        '''
        Option = cmd[0]
        if len(cmd) == 1:
            if Option != 'h':
                sndmsg = sndmsg + '我看不懂你在说什么！'
                WeChat.SendWeChatTextMsg(sndmsg, msg['FromUserName'], msg['User']['NickName'], self.logfile)
                return
        else:
            mainUser = cmd[1] # 获得第二个参数
            if mainUser != self.getMainUser(): # 要输入主用户才可
                if Option != 'h':
                    sndmsg = sndmsg + '我看不懂你在说什么！'
                    WeChat.SendWeChatTextMsg(sndmsg, msg['FromUserName'], msg['User']['NickName'], self.logfile)
                    return
            else: # 删除mainUser的命令，只剩下纯命令
                cmd.remove(mainUser)
        if Option == 'h':
            sndmsg = sndmsg + self.Help()
        elif Option == 'l':
            sndmsg = sndmsg +  self.ListStock()
        elif Option == 'a':
            sndmsg = sndmsg + self.AddStock(cmd)
        elif Option == 'r':
            sndmsg = sndmsg + self.RemoveStock(cmd)
        elif Option == 'm':
            sndmsg = sndmsg + self.ModifyStockList(cmd)
        elif Option == 'i':
            sndmsg = sndmsg + self.getStockInfo(cmd)
        elif Option == 'rs':
            sndmsg = sndmsg + self.ResetStockAlarmInfo(cmd)
        elif Option == 'lu':
                sndmsg = sndmsg + self.printUserList()
        elif Option == '收到':
            sndmsg = sndmsg + self.confirmAlert(cmd)
        else:
            sndmsg = sndmsg + + WeChat.getRespons(msg['Text'], 90)
            if random.randint(0,10) == 2 or random.randint(0,10) == 6:
                sndmsg = sndmsg + '\n 如果你实在不知道要输入什么的话，那就输入\'h\'看看帮助文档吧！'
        WeChat.SendWeChatTextMsg(sndmsg, msg['FromUserName'], msg['User']['NickName'], self.logfile)
       
    def isUserInUserList(self, userAccountName):
        Output = False
        with self.mu:
            for user in self.UserList:
                if str(userAccountName) == self.UserList[user]['UserName']:
                    Output = True
        return Output
    
    def write2Log(self, msg):
        try:
            if self.f.closed:
                self.f = open(self.logfile,'a+')
            self.f.write(msg + '\n')
            self.f.close()
        except Exception as e:
            errmsg = '# 股票监测类写入日志异常：已通知管理员处理!' + str(e)
            print(errmsg)
            self.SendAlert2Master(errmsg)
    def Bye(self, Debug):
        if not Debug:
            self.pickleDump2file(self.prickleFileName)
        print(self.extMsg)
#        WeChat.SendWeChatMsgToUserList(self.UserList, self.extMsg, self.logfile)
    def Help(self):
        Output = ''' 这是这款股票监控工具的说明书：
    股票监控工具旨在无需人为盯盘的情况下，当股票价格满足一定条件时，通过微信的方式向用户发送预警信息。当股票价格超出设置的上下限区间，或者低于五日均价，均会向用户发送预警信息。如果输入参数错误，则智能聊天。
    \'股票 h\'： \t获得这款工具的帮助文档。
    \'股票 l ShiRui\'： \t获得用户所在主用户ShiRui下监控股票的信息。
    \'股票 a ShiRui 300332 11.38 12.38\'： \t将300332股票加入用户所在主用户ShiRui下监控列表，后面依次为监控价格下限以及上限。如果列表中已经存在该股票，则用新的监控指标替代旧的数据。参数间用空格分隔。
    \'股票 r ShiRui 300332\'： \t将股票300332从监控列表中移出，如果列表中不存在该股票，则什么都不做。
    \'股票 m ShiRui 300332 11.38 12.38\'： \t修改监控股票300332的监控参数。参数间用空格分隔。
    \'股票 i ShiRui 300332\'： \t 获取股票300332的实时信息。
    \'股票 rs ShiRui 300332\'：\t重置股票300332的报警状态。
    \'股票 lu ShiRui \': \t 列出当前用户信息
    \'股票 收到 ShiRui 300332\'：\t 表明收到股票300332的预警信息，在下次更新预警参数或回归过正常状态之前，不会再发送提醒信息（ 10 ）条预警信息无回复，自动停止发送预警信息）。
     ## 以下操作仅限于管理员账号 ##
    \'股票 au ShiRui XuKailong FlameMan\'： \t 在ShiRui主账号下，添加子账号,callName为XuKailong，昵称为FlameMan。子账户不能超过上限 5 个   
    \'股票 ru ShiRui XuKailong\'： \t 在ShiRui主账号下，删除callName为XuKailong的子账号，子账号数量最少为1个       
    \'股票 srd ShiRui 365\'： \t 将ShiRui主账号的股票监控有效期设置为365天
    '''
        return Output
    def Get_Stock_List(self):
        try:
            df = ts.get_stock_basics() # get all stock info
        except Exception as e:  # 出现异常，向上抛出
            errmsg = '股票监测类获取股市股票列表异常：' + str(e) + '!'
            raise Exception(errmsg)
        return df
    
    def SendAlert2Master(self, errmsg):
        errmsg2 = '程序异常，提醒管理员：\n' + str(errmsg)
        self.write2Log(str(self.label) + str(errmsg2))
        WeChat.SendWeChatMsgToUserList(self.Master, str(self.label) + str(errmsg2), self.logfile)
        print(str(self.label) + str(errmsg2))
        
    def ListStock(self):
        StockDic = self.StockDic
        Output = ''
        with self.mu: 
            for code in StockDic:
                if code == 'sh':
                    codename = '上证指数'
                elif code =='sz':
                    codename ='深圳指数'
                else:
                    codename = self.getNamefromCode(code)
                Output = Output + '股票 ' + codename + '(' +  str(StockDic[code]['code']) + ')：\n ' + '价格下限： ' + str(StockDic[code]['lowlimit']) + ' 元,   价格上限：  ' \
                        + str(StockDic[code]['highlimit']) + ' 元,   预警状态：  ' + str(StockDic[code]['Alertsent']) + ' （0：无预警；1 - ' \
                             + str(self.__ALERTMAX__) + '：正在发送预警； ' + str(self.__ALERTMAX__+ 1) + '：已停止预警）。\n'
        return Output
    def printUserList(self):
        Output = ''
        if len(self.UserList) < 1:
            Output = Output + self.getMainUser() + ': 用户列表为空！'
        else:
            Output = Output + '用户列表如下:\n' 
            with self.mu:
                for user in self.UserList:
                    # 分别打印昵称，用户名和NickName
                    Output = Output + '标称名 -- ' + str(user) + '， 用户名 -- ' + str(self.UserList[user]['UserName']) + '， 昵称 -- ' + str(self.UserList[user]['NickName']) + '\n'
        return Output
    def printInfo(self):
        # 基本信息
        Output =          '\n标签： ' + str(self.label)+ '      主用户： ' + self.getMainUser() + '       作者: ' + self.__Author__  + ' \n'
        # 用户列表
        Output = Output +  self.printUserList()
        # 监控时间段
        Output = Output + '股票监控有效期为：' + str(self.residDays) + ' 天\n'
        Output = Output + '股票监控时间段为：\n'  
        kHr = self.kHr
        kMin = self.kMin
        kSec = self.kSec
        kPeriod1 = self.kPeriod1
        kPeriod2 = self.kPeriod2
        starttime = self.starttime
        endtime =   self.endtime
        Output = Output + \
    str('%02d' % self.starttime[kPeriod1][kHr]) + ':' + str('%02d' %starttime[kPeriod1][kMin]) + ':' + str('%02d' %starttime[kPeriod1][kSec]) + ' -- ' + \
    str('%02d' %endtime[kPeriod1][kHr]) + ':' + str('%02d' %endtime[kPeriod1][kMin]) + ':' + str('%02d' %endtime[kPeriod1][kSec]) + '， ' + \
    str('%02d' %starttime[kPeriod2][kHr]) + ':' + str('%02d' %starttime[kPeriod2][kMin]) + ':' + str('%02d' %starttime[kPeriod2][kSec]) + ' -- ' +\
    str('%02d' %endtime[kPeriod2][kHr]) + ':' + str('%02d' %endtime[kPeriod2][kMin]) + ':' + str('%02d' %endtime[kPeriod2][kSec]) + '\n'
        Output = Output + '监控股票列表为：\n' 
        Output = Output + self.ListStock()
        Output = Output + '最大预警次数为： ' + str(self.__ALERTMAX__) + '\n'
        Output = Output + '工作日志文件名为：' + str(self.logfile) + '\n'    
        return Output  
    
    def AddStock(self, paras):
        if len(paras)!=4:
            Output = '# 错误: addstock(), 参数错误！' + str(paras)
            print(paras)
        else:
            code = str(paras[1])
            if code not in self.stockListInChina:
                code = self.getCodefromName(code)
                if code == -1:
                    Output = '# 找不到股票：' + str(code) 
                    return Output
            ll = float(paras[2])
            hl = float(paras[3])
            if code in self.StockDic.keys(): # 判断股票是否已经存在
                  #如果存在，用新的参数覆盖旧的参数
                  self.StockDic[code]['lowlimit'] = ll
                  self.StockDic[code]['highlimit'] = hl
                  self.StockDic[code]['Alertsent'] = 0 #重置提醒邮件状态       
                  Output = '该股票已存在于监控列表，进行监控参数更新！'                  
            else:
                #如果不存在，用新的参数创建该股票
                with self.mu:    ##加锁
                    self.StockDic.setdefault(code, {'code':code, 'lowlimit':ll, 'highlimit':hl, 'Alertsent':0})  # 如果code存在，不做任何事情； 如果不存在，创建，并赋值
                Output = '股票' + str(code) + '成功添加在监控列表中！'
        return Output    
    def RemoveStock(self, paras):
        if len(paras)!=2:
            Output = '# 错误: RemoveStock(), 参数错误！'
            print(paras)
        else:
            code = str(paras[1])
            #如果不存在，用新的参数创建该股票
            if code not in self.stockListInChina:
                code = self.getCodefromName(code)
                if code == -1:
                    Output = '# 找不到股票：' + str(code) 
                    return Output
            if code in self.StockDic.keys(): # 判断股票是否已经存在
                with self.mu:    ##加锁
                     self.StockDic.pop(code)
                Output = '成功将股票' + str(code) + '移出监控列表！'
            else:
                Output = '股票' +  str(code) + '不存在于监控列表!'
        return Output    
    def ModifyStockList(self, paras):
        if len(paras)!=4:
            Output = '# 错误: ModifyStockList(), 参数错误！'
            print(paras)
        else:
            code = str(paras[1])
            ll = float(paras[2])
            hl = float(paras[3])
            #如果不存在，用新的参数创建该股票
            if code not in self.stockListInChina:
                code = self.getCodefromName(code)
                if code == -1:
                    Output = '# 找不到股票：' + str(code) 
                    return Output
            if code in self.StockDic.keys(): # 判断股票是否已经存在
                  #如果存在，用新的参数覆盖旧的参数
                  self.StockDic[code]['lowlimit'] = ll
                  self.StockDic[code]['highlimit'] = hl
                  self.StockDic[code]['Alertsent'] = 0 #重置提醒邮件状态       
                  Output = '股票' + str(code) + '监控参数更新成功！'                  
            else:
                #如果不存在，用新的参数创建该股票
                if code not in self.stockListInChina:
                    code = self.getCodefromName(code)
                    if code == -1:
                        Output = '# 找不到股票：' + str(code) 
                        return Output
                with self.mu:    ##加锁
                    self.StockDic.setdefault(code, {'code':code, 'lowlimit':ll, 'highlimit':hl, 'Alertsent':0})  # 如果code存在，不做任何事情； 如果不存在，创建，并赋值
                Output = '股票' + str(code) + '不存在，已将其添加至监控列表中！'    
        return Output     
    def ResetStockAlarmInfo(self, paras):
        if len(paras)!=2:    
            Output = '#Error: ResetStockAlarmInfo(), 参数错误！'
            print(paras)
        else:
            code = str(paras[1])
            #如果不存在，用新的参数创建该股票
            if code not in self.stockListInChina:
                code = self.getCodefromName(code)
                if code == -1:
                    Output = '# 找不到股票：' + str(code) 
                    return Output
                
            if code in self.StockDic.keys(): # 判断股票是否已经存在
                  #如果存在，用新的参数覆盖旧的参数
                  self.StockDic[code]['Alertsent'] = 0 #重置提醒邮件状态       
                  Output = '股票' + str(code) + '报警状态重置成功！'                  
            else:
                #如果不存在，报错
                Output = '股票' + str(code) + '不存在于监控列表中！'    
        return Output
    def getStockInfo(self, paras):
        if len(paras)!=2:    
            Output = '#Error: getStockInfo(), 参数错误！'
            print(paras)
        else:
            try:
                code = str(paras[1])
                if code not in self.stockListInChina:
                    code = self.getCodefromName(code)
                    if code == -1:
                        Output = '# 找不到股票：' + str(code) 
                        return Output
                df=ts.get_realtime_quotes(code)
                localtoday = datetime.datetime.now()
                yestoday = localtoday - datetime.timedelta(days=30) #获取最近30天的数据，上个交易日为排序第二个
                df_yestoday = ts.get_hist_data(code,start=yestoday.strftime('%Y-%m-%d'), end = localtoday.strftime('%Y-%m-%d')).iloc[1]
                vopen = float(df.ix[0,['open']].values[0])
                vhigh = float(df.ix[0,['high']].values[0])
                vnow =  float(df.ix[0,['price']].values[0])
                vclose = float(df_yestoday['close'])
                Output = '股票代码： ' + code+ '， 股票名： %8s' % df.ix[0,['name']].values[0] + '， 现价： ' + df.ix[0,['price']].values[0] + \
        ' 元， 开盘变化量： %4.2f%%' % ((vnow-vopen)*100./vopen) + '，  昨收变化量： %4.2f%%' % ((vnow-vclose)*100./vclose) + '， 开盘价： ' + str(vopen) + ' 元， 最高价： ' + str(vhigh) + ' 元'
            except Exception as e:
                Output = '股票监测类获取股票' + str(code) + '信息异常：' + str(e) + '!\n'
        return Output

    def confirmAlert(self, paras):
        if len(paras)!=2:    
            Output = '#Error: confirmAlert(), 参数错误！'
            print(paras)
        else:
            code = str(paras[1])
            if code in self.StockDic.keys(): # 判断股票是否已经存在
                  #如果存在，用新的参数覆盖旧的参数
                  self.StockDic[code]['Alertsent'] = self.__ALERTMAX__  + 1 # 表明已经收到       
                  Output = '股票' + str(code) + '报警关闭！'                  
            else:
                #如果不存在，报错
                Output = '股票' + str(code) + '不存在于监控列表中！'       
        return Output

    def remind(self, code, countor):
        lowlimit = self.StockDic[code]['lowlimit']
        highlimit = self.StockDic[code]['highlimit']
        Alertsent = self.StockDic[code]['Alertsent']
        if code not in self.stockListInChina:
            errmsg = '#找不到股票：' + str(code) +', 将其从监控列表移出！'
            self.RemoveStock(['r', code])
            print(errmsg)
            self.write2Log(errmsg)
            return 
        try:           
            df=ts.get_realtime_quotes(code)
            localtoday = datetime.datetime.now()
            yestoday = localtoday - datetime.timedelta(days=30)
            df_yestoday = ts.get_hist_data(code,start=yestoday.strftime('%Y-%m-%d'), end = localtoday.strftime('%Y-%m-%d')).iloc[1]
            vopen = float(df.ix[0,['open']].values[0])
            vhigh = float(df.ix[0,['high']].values[0])
            vnow =  float(df.ix[0,['price']].values[0])
            vMa5 = float(df.ix[0,['ma5']].values[0])
            vclose = float(df_yestoday['close'])
        except Exception as e:
            Output = '股票检测类获取股票' + str(code) + '数据异常： ' + str(e) + '!'
            self.write2Log(Output)
            return
        tempstr = '第 <%d> 次监控：' % countor + '股票代码: ' + code+ ', 股票名: %8s' % df.ix[0,['name']].values[0] + ', 现价:' + df.ix[0,['price']].values[0] + \
        ', 开盘变化量： %4.2f%%' % ((vnow-vopen)*100./vopen) + ', 昨收变化量： %4.2f%%' % ((vnow-vclose)*100./vclose) + ', open:' + str(vopen) + ', high： ' + str(vhigh)
        print(tempstr)
        self.write2Log(tempstr)
        if float(df.ix[0,['price']].values[0]) < lowlimit or float(df.ix[0,['price']].values[0]) < vMa5 :
            if float(df.ix[0,['price']].values[0]) < vMa5:
                if df.ix[0,['name']].values[0] == 'sh':
                    warntext = '# 严重警告：上证指数'
                elif df.ix[0,['name']].values[0] == 'sz':
                    warntext = '# 严重警告：深圳指数'
                else:
                    warntext = str('# 警告：股票 ' + df.ix[0,['name']].values[0])
                msgcontent = warntext + str('低于五日均价： '+str(vMa5)+', 现价: '+ df.ix[0,['price']].values[0]) #正文内容
            else:
                msgcontent = str('股票 ' + df.ix[0,['name']].values[0] + '(' + df.ix[0,['code']].values[0] + ')' + ' 价格低于 '+str(lowlimit)+', 现价: '+ df.ix[0,['price']].values[0]) #正文内容
    #        msgsubject = '#警告:来自' + __Author__ + '的监控！'
                msgcontent = msgcontent + '  ## 第 ' + str(Alertsent) + ' 次提醒！'
            if Alertsent < self.__ALERTMAX__:
    #            Send_Mail(msgfrom, pwd, msgcontent, msgto, msgfrom, msgsubject, sender, receiver)
                if self.SendWebChat ==1:
                    WeChat.SendWeChatMsgToUserList(self.UserList, msgcontent, self.logfile)
                    self.StockDic[code]['Alertsent'] = self.StockDic[code]['Alertsent'] + 1                    
            elif Alertsent == self.__ALERTMAX__:
                if self.SendWebChat ==1:
                    WeChat.SendWeChatMsgToUserList(self.UserList, '# ' + str(code) + ' 预警次数达到上限，停止预警！', self.logfile)
                    self.StockDic[code]['Alertsent'] = self.StockDic[code]['Alertsent'] + 1
            else:
                tempstr = 'Alert already sent!'
                print(tempstr)
                self.write2Log(tempstr)
                
        elif float(df.ix[0,['price']].values[0]) < highlimit:
             self.StockDic[code]['Alertsent'] == 0
                     
        if float(df.ix[0,['price']].values[0]) > highlimit:
            msgcontent = str('股票 '+ df.ix[0,['name']].values[0] + '(' + df.ix[0,['code']].values[0] + ')' + ' 价格高于 '+str(highlimit)+', 现价: '+ df.ix[0,['price']].values[0]) #正文内容
    #        msgsubject = '上涨：来自' + __Author__ + '的监控！'
            msgcontent = msgcontent + '  ## 第 ' + str(Alertsent) + ' 次提醒！'
            if Alertsent < self.__ALERTMAX__:
    #            Send_Mail(msgfrom, pwd, msgcontent, msgto, msgfrom, msgsubject, sender, receiver)
                self.StockDic[code]['Alertsent']==1
                if self.SendWebChat ==1:
                    WeChat.SendWeChatMsgToUserList(self.UserList, msgcontent, self.logfile)
                    self.StockDic[code]['Alertsent'] = self.StockDic[code]['Alertsent'] + 1
            elif Alertsent == self.__ALERTMAX__:
                if self.SendWebChat ==1:
                    WeChat.SendWeChatMsgToUserList(self.UserList, '# ' + str(code) + ' 预警次数达到上限，停止预警！', self.logfile)
                    self.StockDic[code]['Alertsent'] = self.StockDic[code]['Alertsent'] + 1
            else:
                tempstr = 'Alert already sent!'
                print(tempstr)
                self.write2Log(tempstr)
    #--------------------------------------------------------------------------#
    def T1LaterThanT2(self, time1,time2): # t1 < t2, false, t1 >= t2, true
        if len(time1) != 3 or len(time2) != 3:
             tempstr = '股票监测类时间格式异常!'
             self.write2Log(tempstr)
             raise Exception(tempstr)
        T1 = time1[self.kHr]*3600 + time1[self.kMin]*60 + time1[self.kSec] # s
        T2 = time2[self.kHr]*3600 + time2[self.kMin]*60 + time2[self.kSec] # s
        if T1 < T2:
            return False
        else:
            return True
    def OnDuty(self):
        localtime = time.localtime()
        weekday = time.strftime("%w",localtime)
        if weekday =='0' or weekday == '6':  # saturday or sunday,let's rest 
            return False
        mytime = datetime.datetime.now()
        currtime = [mytime.hour, mytime.minute, mytime.second]
        if (self.T1LaterThanT2(currtime, self.starttime[self.kPeriod1]) and (not self.T1LaterThanT2(currtime, self.endtime[self.kPeriod1]))) \
           or (self.T1LaterThanT2(currtime, self.starttime[self.kPeriod2]) and (not self.T1LaterThanT2(currtime, self.endtime[self.kPeriod2]))):
            return True
        else:
            return False
    def setResDays(self, paras, user):
#    \'股票 srd ShiRui 365\'： \t 将ShiRui主账号的股票监控有效期设置为365天\n  
        if len(paras)!=3:
            Output = '#Error: ' + str(self.label) + ' setResDays(), 参数错误！\n' + str(paras) + '\n'
            Output = Output + '使用期重设：\n \' 股票 srd ShirRui 365\'\n  srd 表示重设使用期，ShiRui为主用户名，365 为剩余天数'
            print(paras)
        else:
            mainUser = paras[1]
            days = int(paras[2])
            if mainUser != self.getMainUser():
                Output = '# 忽略使用期重设：主账号名不符合！'
                return Output
            try: 
                self.residDays = days
                Output = '成功重设用户 【 ' + str(mainUser) + ' 】 的股票监控天数为：' + str(days) + '天 by ' + user
                WeChat.SendWeChatMsgToUserList(self.UserList, Output, self.logfile) # 向所有用户通知股票有效期变化信息
            except Exception as e:   # 如果不成功，什么也不做，并返回消息
                Output = '# 用户 【 ' + str(mainUser) + ' 】 股票监控天数重设失败: ' + str(e) 
                self.write2Log(Output)
                self.SendAlert2Master(Output)
                print(Output)
        return Output   
    def countResDays(self):
        try:
            with self.mu:
                now = datetime.datetime.now()
                hour = int(now.hour)
                if hour != 0: # 非12点期间，置为False
                    self.ResSetFlag = False
                    return
                if hour == 0 and not self.ResSetFlag:
                    # 判断是否是半夜十二点
                    self.residDays = int(self.residDays) - 1
                    #判断是否小于15天
                    if  int(self.residDays) < 15:
                        WeChat.SendWeChatMsgToUserList(self.UserList, self.label + '您的股票监控还有' + str(self.residDays) + ' 就要过期了，请及时联系管理员延期！\n' + \
                        '微信： MoBeiHuyang；手机：18910241406', self.logfile) # 向所有用户通知keywords变化信息
                    self.ResSetFlag = True
                    print('用户 ' + str(self.getMainUser()) + '有效期：' + str(self.residDays) + '天！')
                else:
                    print('已经设置用户 ' + str(self.getMainUser()) + '有效期：' + str(self.residDays) + '天！')
        except Exception as e:   # 如果不成功，给管理员发消息
            Output = '# 使用时间设置失败: ' + str(e) 
            self.write2Log(Output)
            print(Output)
            self.SendAlert2Master(self, Output)    
            
    def addUser2UserList(self, paras, user):
#    \'股票 au ShiRui XuKailong FlameMan\'： \t 在ShiRui主账号下，添加子账号,callName为XuKailong，昵称为FlameMan。子账户不能超过上限 5 个\n 
#    paras 中从au开始 
#    user为字符串
        if len(paras)!=4:
            Output = '#错误: ' + str(self.label) + ' addUser2UserList(), 参数错误！\n' + str(paras) + '\n' 
            Output = Output + '用户添加：\n \' au ShiRui XuKailong FlameMan\'\n  au 表示添加用户，ShiRui为主用户名，XuKailong为添加用户的callName, FlameMan为添加用户的昵称'
            print(paras)
        else:
            mainuser = paras[1]
            callName = paras[2]
            nickName = paras[3]
            if mainuser != self.getMainUser():
                Output = '# 忽略添加：主账号名不符合！'
                return Output
            try: # 首先，获得用户的账号，如果获得成功
                userName  =  WeChat.findWeChatUser(nickName, self.logfile)
                if not self.isUserInUserList(userName) : # 判断用户是否已经存在
                      if len(self.UserList) >= self.maxUserNum:
                           Output = '# 添加失败：用户数已经超过限制！'
                      else:
                          with self.mu:
                              #如果不存在，添加新用户
                              self.UserList.setdefault(callName, {'UserName':userName, 'NickName':nickName})
                              Output = '用户 ' + str(callName) + ' 成功添加在用户' + str(mainuser) + '列表中！ by ' + user
    #                      WeChat.SendWeChatMsgToUserList(self.UserList, Output, self.logfile) # 向所有用户通知添加信息
                else:
                      Output = '# 添加失败： 用户 ' + str(callName) + ' 已经存在于用户' + str(mainuser) + '列表中'
            except Exception as e:   # 如果账号不成功，什么也不做，并返回消息
                Output = '添加用户异常：# 微信中找不到用户 ' + str(nickName) + ': ' + str(e) 
                self.write2Log(Output)
                print(Output)
                self.SendAlert2Master(Output)
        return Output  
    def rmUserFromUserList(self, paras, user):
#   \'股票 ru ShiRui XuKailong\'： \t 在ShiRui主账号下，删除callName为XuKailong的子账号，子账号数量最少为1个\n 
        if len(paras)!=3:
            Output = '# 错误: ' + str(self.label) + ' rmUserFromUserList(), 参数错误！\n' + str(paras) + '\n' 
            Output = Output + '用户添加：\n \' ru ShiRui XuKailong\'\n  ru 表示删除用户，ShiRui为主用户名，XuKailong为删除用户的CallName'
            print(paras)
        else:
            mainUser = paras[1]
            callName = paras[2]
            if mainUser != self.getMainUser():
                Output = '# 忽略移出：主账号名不符合！'
                return Output
            try: # 首先，检查用户是否在列表中
                if len(self.UserList) < 2:
                    Output = '#错误: 该账号下用户数只有 1 人，不能删除！'
                    return Output
                if callName in self.UserList.keys(): # 如果用户存在，删除
                    with self.mu:    ##加锁
                         self.UserList.pop(callName)
                    Output = '成功将用户' + str(callName) + '移出用户' + str(mainUser) + '列表！ by ' + user
    #                WeChat.SendWeChatMsgToUserList(self.UserList, Output, self.logfile) # 向所有用户通知移出信息
                else:
                    Output = '用户' +  str(callName) + '不存在于用户' + str(mainUser) + '列表!'
            except Exception as e:   # 如果账号不成功，什么也不做，并返回消息
                Output = '# 用户删除异常：: ' + str(e) 
                self.write2Log(Output)
                print(Output)
                self.SendAlert2Master(Output)
        return Output      
    def pickleDump2file(self, filename):
        try:
            data = {}
            data.setdefault('residDays',self.residDays) 
            data.setdefault('UserList',self.UserList) 
            data.setdefault('StockDic',self.StockDic) 
            data.setdefault('stockListInChina',self.stockListInChina) 
            data.setdefault('countor',self.countor) 
            with open(filename, 'wb') as f:
                pickle.dump(data, f)
                print('股票监控类：pickle file写入成功！')
                self.write2Log('股票监控类：pickle file写入成功！')
        except Exception as e:
            print('股票监控类：pickle file写入异常！'+ str(e))
            self.write2Log('股票监控类：pickle file写入异常！')    
    def getDatafromPickle(self,filename):
        Flag = False
        try:
            with open(filename, 'rb') as f:
                data = pickle.load(f)
                Flag = True
                print('股票监控类：pickle file读取成功！')
                self.write2Log('股票监控类：pickle file读取成功！')
        except Exception as e:
            Flag = False
            data = '# 股票监控类热启动失败，开始初始化：' + str(e)
            print(data)
            self.write2Log(data)
        return Flag, data
    def getCodefromName(self, stock):
        try:
            df = ts.get_stock_basics() # get all stock info
            data = df[df['name'] == stock]
            if len(data) != 1:
                return -1
            else:
                return data.index[0]
        except Exception as e:  # 出现异常，向上抛出
            errmsg = '根据名称获取股票代码异常：' + str(e) + '!'
            raise Exception(errmsg)
        return df
    def getNamefromCode(self, code):
        try:
            df = ts.get_stock_basics() # get all stock info
            return df.loc[code]['name']
        except Exception as e:  # 出现异常，向上抛出
            errmsg = '根据股票代码获取名称异常：' + str(e) + '!'
            raise Exception(errmsg)
        return df    
