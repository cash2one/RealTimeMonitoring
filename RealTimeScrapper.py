# -*- coding: utf-8 -*-
"""
Created on Fri May 19 09:45:52 2017

@author: MoBeiHuYang
"""
import WeChatFuncs as WeChat
from response import myResponse
from bs4 import BeautifulSoup
import time, datetime
import math
import re
import threading  # 用于多线程工作
import pickle
import random
import requests
import json
from dateutil import parser as dateParser
from requests.packages.urllib3.exceptions import InsecureRequestWarning
# 禁用安全请求警告
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

class TBaiDuNewsScapper:
    # 这里要注意一个python不同于C++ 的类定义的问题
    # 如果该类不同实例间要共享一个变量. 如果要避免变量共享的情况，则这些变量要定义砸__init__函数中
    # ------------------------- 实例间共享变量定义(一个实例中改变，其它实例中也会改变----------------------------------#
    __Author__ = 'FlameMan'
    Master = {'Master':{'UserName':'', 'NickName':'FlameMan'}}
    initNewsinList = 100
    maxNewsinList = 2000
    maxUserNum = 5
    # NewsList 仅能在初始化或者发送提醒消息后更改，切记！
    extMsg = '百度新闻实时监控下线，管理员正在处理。有急事请联系管理员：18910241406！'
    label = ' # 百度新闻实时监控程序 # '
    newsNumpPage = 20
    maximumNews2Get = 300
    
    souGou_Thresh = 0
    souGou_WeChat = 0
    souGou_RestTime = 180 # min
    def __init__(self,callName, nickName, mhotReload):
        """
        Created on Fri May 19 09:45:52 2017
        @author: MoBeiHuYang
        在构造函数中，针对主要变量进行初始化
        1. 打印该舆论监控工具的上线信息
        2. 初始化Master的微信账号
        3. 初始化User的微信账号
        4. 初始化NewsList的新闻信息
        Created on Fri May 19 09:45:52 2017
        @ author: MoBeiHuYang
        """
        #-----------------实例不共享变量定义----------------------#
        self.mainUser  = callName # store the keyname or call name of the class
        self.pricklefileName = WeChat.pickle_dir + self.mainUser + '_News_热启动文件.pickle'   
        self.logfile = WeChat.log_dir + self.mainUser + '_BaiDuNews.log'
        self.mu =  threading.RLock()
        self.f = open(self.logfile,'a+')
        self.ResSetFlag = False
        # 初始化管理员账号
        try:
            WeChat.InitWeChatUsers(self.Master, self.logfile) # 热启动后用户名会发生改变
        except Exception as e:  # 异常，向上抛出。如果第一次初始化，属于严重异常，创建列表中初始化，属于一般异常
            errmsg = '新闻监控类管理员账号初始化异常: ' + str(e) 
            self.write2Log(errmsg)
            print(errmsg)
            raise Exception(errmsg)
        # 添加用户列表，并进行初始化 
        hotReload = False
        if mhotReload:
            hotReload, data = self.getDatafromPickle(self.pricklefileName)
        if mhotReload and hotReload: # 同时满足才热启动
            self.UserList = data['UserList']
            self.keywordList = data['keywordList']
            if 'subkeywordList' in data:
                self.subkeywordList = data['subkeywordList']
            else:
                for key in self.keywordList:
                    self.subkeywordList.setdefault(key, set())
            if 'serachRangeOpts' in data:
                self.serachRangeOpts = data['serachRangeOpts']
#                for key in self.serachRangeOpts:
#                    if key == '如意集团':
#                        self.serachRangeOpts[key]['百度网页'] = True   
#                    else:
#                        self.serachRangeOpts[key]['搜狗微信'] = False
            else:
                self.serachRangeOpts = {}
                for key in self.keywordList:
                    self.serachRangeOpts[key] = {'百度新闻':True, '百度网页':False,'搜狗新闻':True,'搜狗微信':False,'今日头条':True }
            print(self.serachRangeOpts)
            self.companyInFiled = data['companyInFiled']
#            if self.mainUser == 'XuKailong':
#                self.companyInFiled = ['如意集团']
            self.numOfNewsInEachScan = data['numOfNewsInEachScan']
            self.numOfNewsInFieldComp = data['numOfNewsInFieldComp']
            self.defaultSortMethod = data['defaultSortMethod']
            self.residDays = data['residDays']
            self.NewsList = data['NewsList']
            self.initMsg = '百度新闻实时监控 by ' + str(self.__Author__) + ' 上线，监控关键词为： ' + str(self.keywordList) + '。'
            self.newsFileTail = data['newsFileTail']
            
            if 'souGou_Thresh' in data:
                self.souGou_Thresh = min(data['souGou_Thresh'], datetime.datetime.now().timestamp() + self.souGou_RestTime*60)
            else:
                self.souGou_Thresh = 0  
            if 'souGou_WeChat' in data:
                self.souGou_WeChat = min(data['souGou_WeChat'],datetime.datetime.now().timestamp() + self.souGou_RestTime*60)
            else:
                self.souGou_WeChat = 0       
            if 'souGou_RestTime' in data:
                self.souGou_RestTime = data['souGou_RestTime']  
            else:
                self.souGou_RestTime = 180                     
            # log file   
            try:
                WeChat.InitWeChatUsers(self.UserList, self.logfile) #初始化用户账号
#                WeChat.SendWeChatMsgToUserList(self.UserList, self.initMsg, self.logfile) # 向所有用户通知上线信息
            except Exception as e:   #异常，向上抛出。如果第一次初始化，属于严重异常，创建列表中初始化，属于一般异常
                errmsg = '新闻监控类用户列表初始化异常: ' + str(e) + '。已通知管理员处理！'
                self.write2Log(errmsg)
                self.SendAlert2Master(str(self.label) + str(errmsg))
                print(errmsg)
                raise Exception(errmsg)
        else:
            self.UserList = {}  #第一个默认为主账号，其余为副账号
            self.keywordList = ['一带一路'] # 每次更新keyswords时，需要同步更新residDays
            self.subkeywordList = {self.keywordList[0]:set(['丝绸之路'])} # 副标签的作用是，每个关键词可以依次循环搜索副关键词，并查询其新闻内容；每个新闻中，应该在标题或者摘要中包含至少一个主关键词或者副关键词，否则认为是垃圾信息
            self.serachRangeOpts = {self.keywordList[0]:{'百度新闻':True, '百度网页':False,'搜狗新闻':False,'搜狗微信':False,'今日头条':False }}
            self.companyInFiled = ['魏桥纺织','江苏阳光','九牧王','海澜之家','红豆股份',\
                                   '雅戈尔', '希努尔',  '柏堡龙','朗姿股份', '上海三毛',\
                                   '搜于特', '三房巷', '太平鸟', '报喜鸟', '维格娜丝','杉杉股份','如意集团']
            self.numOfNewsInEachScan = 60
            self.numOfNewsInFieldComp = 60
            self.defaultSortMethod = 'date'
            self.residDays = dict.fromkeys(self.keywordList,365)
            self.NewsList = {} # 是个字典，每个关键词对应一个列表。列表中最多200条新闻。每次更新时，更新列表信息。列表本质是排序的
            self.initMsg = '百度新闻实时监控 by ' + str(self.__Author__) + ' 上线，监控关键词为： ' + str(self.keywordList) + '。'
            self.newsFileTail = '_' + self.mainUser + '_newsList.txt'
            self.ResSetFlag = False
            self.souGou_Thresh = 0  
            self.souGou_WeChat = 0       
            self.souGou_RestTime = 180              
            
            print(self.initMsg + ' 用户：' + str(callName))
            self.write2Log(self.initMsg  + ' 用户：' + str(callName))
        #-------------------变量定义结束------------------------#
            # 添加用户列表，并进行初始化    
            try:
                self.UserList.setdefault(callName,{'UserName':'', 'NickName':nickName})  # 将主账户加入UserList
                WeChat.InitWeChatUsers(self.UserList, self.logfile) #初始化用户账号
#                WeChat.SendWeChatMsgToUserList(self.UserList, self.initMsg, self.logfile) # 向所有用户通知上线信息
            except Exception as e:   #异常，向上抛出。如果第一次初始化，属于严重异常，创建列表中初始化，属于一般异常
                errmsg = '新闻监控类用户列表初始化异常: ' + str(e) + '。已通知管理员处理！'
                self.write2Log(errmsg)
                self.SendAlert2Master(str(self.label) + str(errmsg))
                print(errmsg)
                raise Exception(errmsg)
            # 检查关键词，并设置有效期
            if len(self.keywordList) < 1:
                with self.mu:    ##加锁
                    self.keywordList.append('一带一路')
                    for keyword in self.keywordList:
                         self.residDays[keyword] = 365
            try: 
                print('初始化新闻列表中...\n')
                self.createNewsList()  # 以目前状态初始化新闻列表
            except Exception as e:  #异常，向上抛出。如果第一次初始化，属于严重异常，创建列表中初始化，属于一般异常
                errmsg = '新闻监控类新闻列表创建异常：' + str(e) + '，已通知管理员处理！'
                self.write2Log(errmsg)
                self.SendAlert2Master(str(self.label) + str(errmsg))
                print(errmsg)
                raise Exception(errmsg)
    def Run(self):
        with self.mu:
            # 扫描一次所有关键词，将更新结果返回
            print('开始一次 ' + str(self.label))
            msgcontent = '' 
            self.countResDays()
            # 反爬虫预警
            if datetime.datetime.now().timestamp() < self.souGou_Thresh:
                errMsg = '搜狗新闻平台遭遇反爬虫系统（' + self.mainUser + '），休息中！剩余时间：' +  str(math.floor((self.souGou_Thresh - datetime.datetime.now().timestamp())/60)) + ' 分钟！'  
                self.SendAlert2Master(str(errMsg))
            if datetime.datetime.now().timestamp() < self.souGou_WeChat:
                errMsg = '搜狗-微信公众号平台遭遇反爬虫系统（' + self.mainUser + '），休息中！剩余时间：' +  str(math.floor((self.souGou_WeChat - datetime.datetime.now().timestamp())/60)) + ' 分钟！' 
                self.SendAlert2Master(str(errMsg))   
            print(self.souGou_Thresh)
            print(self.souGou_WeChat)  
            print(self.souGou_RestTime)
            for keyword in self.keywordList:
                print('关键词 【' + keyword + '】')
                try:
                    # 每隔1小时，更新一次时间戳
                    now = int(datetime.datetime.now().timestamp())
                    if now % 3600 < 2:
                        print(self.label + ' 更新关键词时间戳：' + keyword)
                        self.NewsList[keyword] = self.updateDateStamp(self.NewsList[keyword])
                except Exception as e: # 如果更新时间戳出现异常，通知管理员，然后pass
                    errmsg = '# 更新时间戳异常，已通知管理员处理！' + str(e)
                    print(errmsg)
                    self.write2Log(errmsg)
    #                    WeChat.SendWeChatMsgToUserList(self.Master, errmsg, self.logfile)
                    self.SendAlert2Master(str(self.label) + str(errmsg))
                try:
                    # 扫描是否有新消息
                    updateFlag, updateMsg = self.scrapUpdatedNews(keyword)
                    if updateFlag:
                        print(self.label + ' 开始向用户发消息：' + keyword)
                        msgcontent = msgcontent + updateMsg + '\n'
                        WeChat.SendWeChatMsgToUserList(self.UserList, msgcontent, self.logfile)
                except Exception as e: #一般错误
                    errmsg = '新闻监控类运行异常: # 更新监控列表失败: ' + str(e) + '， 已通知管理员处理！\n'
                    print(errmsg)
    #                    WeChat.SendWeChatMsgToUserList(self.Master, errmsg, self.logfile)
                    self.SendAlert2Master(str(self.label) + str(errmsg))
                    self.write2Log(errmsg)
                    # 向上抛出异常
                    raise Exception(errmsg)
            print('结束一次 ' + str(self.label))
    def pickleDump2file(self, filename):
        try:
            data = {}
            data.setdefault('UserList',self.UserList) 
            data.setdefault('keywordList',self.keywordList) 
            data.setdefault('subkeywordList',self.subkeywordList) 
            data.setdefault('serachRangeOpts',self.serachRangeOpts) 
            data.setdefault('souGou_Thresh',self.souGou_Thresh)
            data.setdefault('souGou_WeChat',self.souGou_WeChat)
            data.setdefault('souGou_RestTime',self.souGou_RestTime)
            data.setdefault('companyInFiled',self.companyInFiled) 
            data.setdefault('numOfNewsInEachScan',self.numOfNewsInEachScan) 
            data.setdefault('numOfNewsInFieldComp',self.numOfNewsInFieldComp) 
            data.setdefault('defaultSortMethod',self.defaultSortMethod) 
            data.setdefault('residDays',self.residDays) 
            data.setdefault('NewsList',self.NewsList) 
            data.setdefault('initMsg',self.initMsg) 
            data.setdefault('newsFileTail',self.newsFileTail) 
            # log file    
            with open(filename, 'wb') as f:
                pickle.dump(data, f)
                print('新闻监控类：pickle file写入成功！')
                self.write2Log('新闻监控类：pickle file写入成功！')
        except Exception as e:
            print('新闻监控类：pickle file写入异常！' + str(e))
            self.write2Log('新闻监控类：pickle file写入异常！' + str(e))
    def getDatafromPickle(self,filename):
        Flag = False
        try:
            with open(filename, 'rb') as f:
                data = pickle.load(f)
                Flag = True
                print('新闻监控类：pickle file读取成功！')
                self.write2Log('新闻监控类：pickle file读取成功！')
        except Exception as e:
            Flag = False
            data = '# 新闻监控类热启动失败！开始初始化：' + str(e)
            print(data)
            self.write2Log(data)
        return Flag, data
    def createNewsList(self):
        # 创建列表
        with self.mu:
            for keyword in self.keywordList:
                self.createNewsListofOneKeyword(keyword)
                
    def createNewsListofOneKeyword(self, keyword):
        # 创建列表
        succ, news = self.getNews( keyword, self.initNewsinList, self.defaultSortMethod)
        if succ:
            with self.mu:
                try:
                    self.NewsList.setdefault(keyword, news)
                    self.writeNews2File(self.NewsList[keyword], WeChat.news_dir + keyword + self.newsFileTail, '## 初始化关键词新闻列表 ##：【 ' + keyword + ' 】 最近 ' + str(self.initNewsinList) + ' 条新闻搜索结果如下（时间排序）：\n\n', 'w+') 
                except Exception as e:
                    raise Exception('创建新闻列表异常：获取新闻失败！' + keyword)
    def getMainUser(self):
        return self.mainUser 
    def addNews2List(self, keyword, news):
        # 仅能在发送提醒消息后调用该函数
        # 将news 添加到list中，并排序
        # news类型是List中排序的类型，典型的news结构如下，即是个键值对
        """
 ('news_55',
 {'author': '金融界',
  'date': '2017年04月27日 18:23',
  'link': 'http://stock.jrj.com.cn/share,disc,2017-04-28,002193,0000000000000hz4ce.shtml',
  'source': '金融界\xa0\xa02017年04月27日 18:23',
  'summary': '证券代码:002193 证券简称:山东如意 公告编号:2017-028。 山东济宁如意毛纺织股份有限公司。 股票交易异常波动公告。 本公司及董事会全体成员保证公  百度快照',
  'timeflag': True,
  'title': '山东如意:股票交易异常波动公告'})
        """
        try:
            Output = ''
            if keyword in self.keywordList:
                # 仅在keyword存在时，才能使用此函数
                if len(self.NewsList[keyword]) < self.maxNewsinList:
                    self.NewsList[keyword].insert(0, news)
                else:
                    while len(self.NewsList[keyword]) > self.maxNewsinList:
                        self.NewsList[keyword].pop() # 删除最后一条
                    self.NewsList[keyword].insert(0, news) # 在最开始加入，默认为新来的总是最新发生的时间
                # 如果NewsList中尚未达到上限，直接加入，否则移除最后一条，并添加新的一条
                # 重新排序
 #               temp = sorted(dict(self.NewsList[keyword]).items(),key = lambda d:d[1]['date'], reverse = True)
 #               self.NewsList[keyword] = temp
                Output  = '## 更新关键词 【：' + keyword + ' 】 新闻列表成功！\n'
                self.writeNews2File(self.NewsList[keyword], WeChat.news_dir + keyword + self.newsFileTail, '## 更新关键词 【：' + keyword + ' 】 新闻列表， 最近 ' + str(len(self.NewsList[keyword])) + ' 条新闻搜索结果如下（时间排序）：\n\n','a+')
            else: # 一般错误
                # 否则，报错
                Output = '# 新闻列表添加错误： ' + keyword + '不在关键词列表中！' 
                self.SendAlert2Master(str(self.label) + str(Output))
        except Exception as e:
            errmsg = '添加新闻至列表异常：In addNews2List():' + str(e)
            print(errmsg)
            self.SendAlert2Master(str(self.label) + str(errmsg))
            raise  Exception(errmsg)
        return Output
    def newsInList(self, keyword, news):
        # news 和 old news 是新闻的键值对，见addNews2List中说明
        # 如果找到，返回True，找不到，返回False
        findNews = False # 外部已经加锁
        with self.mu:
            for oldnews in self.NewsList[keyword]:
                if self.sameNews(oldnews[1], news[1]):
                    findNews = True
                    break
        return findNews    
            
    def scrapUpdatedNews(self, keyword):
        # 扫描一个关键词，得到其前10条新闻列表。逐条判断该新闻是否在该关键词列表中
        # 如果在，返回false
        # 如果不在，返回新闻格式，并将其作为新的新闻返回
        update = False
        result = '\n检测到新的新闻 【 ' + keyword + ' 】：\n' 
        try:
            succ, news = self.getNews(keyword, self.numOfNewsInEachScan, self.defaultSortMethod) 
            # news是个键值对
            if not succ:
                self.SendAlert2Master(str(self.label) + str('警告管理员：新闻监控中关键词【' + keyword + ' 】 新闻获得失败！'))
                return False, result # 这里应该发警报
        except Exception as e: # 如果新闻列表获取错误，则直接返回
            update = False
            errmsg = 'scrapUpdatedNews(): 获取新闻列表失败：' + str(e)
            print(errmsg)
            self.SendAlert2Master(str(self.label) + str(errmsg))
            return update, result
        # 此处得到的news是该keyword下，key排序后的列表
        try:  # Run已经锁定
            for newsitem in news:
                # 如果不是今日新闻，跳过
                # news 中已经排序
                body = newsitem[1] # 获得其键值，其下属有'标题',‘date'等
                now = datetime.datetime.now()
                
                recDay = 1
                FindNews =  False # 是否是最近3天新闻
                for i in range(recDay): # i = 0 ~ recDay - 1
                    day = now - datetime.timedelta(days = i)
                    date = '%04d年%02d月%02d日'%(day.year, day.month, day.day)
                    if date in body['date']:
                       FindNews = True
                if not FindNews:
                    continue
                # 逐条扫描
                if not self.newsInList(keyword, newsitem):
                # 如果该条新闻不在列表中，在result中追加该新闻列表   
                    result = result + self.printNews2Format(newsitem) + '\n'
                    update = True
                    # 添加新闻
                    self.addNews2List(keyword, newsitem)
        except Exception as e: #一般错误，如果出错，返回错误
            update = False
            errmsg = '刷新新闻异常：scrapUpdatedNews():' + str(e)
            print(errmsg)
            self.SendAlert2Master(str(self.label) + str(errmsg))
            pass 
        
        return update, result
    def printNews2Format(self, news):
        # new 格式是排序后的，见addNews2List
        Output = ''
        body = news[1]
        Output = Output + ("标题: " + body['title'] + "\n")
        source = body['author'] + '  ' + body['date'] + ''
        if not body['timeflag']:
            source = source + '(大约)'
        Output = Output + "来源: " + source + '（' + body['platform'] + '）\n' + "链接: " + body['link'] + "\n" + "简介: " + body['summary'] + "\n"      
        return Output
    def getFileName(self, keywords):
        return (WeChat.news_dir + keywords + '_newslist' + str(time.strftime('_%Y_%m_%d_%H_%M_%S', time.localtime(time.time()))) + '.txt')
    def Interaction(self, msg):
        self.write2Log('收到来自' + str(msg['User']['NickName'])+'的消息：\n\'' + str(msg['Text']) + '\'')
        cmd_temp = str(msg['Text']).lstrip().rstrip().split(' ')
        cmd = None
        # 进入此位置的，肯定以  '新闻' 开头，且用户在用户列表中
        if cmd_temp[0] != '新闻':  #避免用户重复的情况
            sndmsg = '命令错误，我没有什么要和你说的！'
        else:
            cmd = str(msg['Text'][2:len(msg['Text'])]).lstrip().rstrip() # 去掉命令中的 新闻 两字，获得剩下部分命令，此处cmd还是一个字符串
            sndmsg = str(self.label + '\n')
            if not self.OnDuty():
                if cmd[0:5] == 'getup':
                    cmd = cmd[5:len(cmd)].lstrip()
                    sndmsg = sndmsg + '连睡觉时间都不放过，真是个资本家！\n'
                    WeChat.SendWeChatTextMsg(sndmsg, msg['FromUserName'], msg['User']['NickName'], self.logfile)
                else:
                    sndmsg = sndmsg + '睡觉中，勿扰！'
                    WeChat.SendWeChatTextMsg(sndmsg, msg['FromUserName'], msg['User']['NickName'], self.logfile)
                    return
            if len(cmd) < 1: # 命令为空
                sndmsg = sndmsg + '我看不懂你在说什么！'
                WeChat.SendWeChatTextMsg(sndmsg, msg['FromUserName'], msg['User']['NickName'], self.logfile)
                return
            cmd = cmd.split(' ') # 提取 新闻 后面的命令
            Option = cmd[0]
            if Option == 'h':
                sndmsg = self.Help()
            elif Option == 'lu':
                sndmsg = self.printUserList()
            elif Option == 'lkw':
                sndmsg = self.printKwdList()
            elif Option == 'lfc':
                sndmsg = self.printFiledCompany()
            elif Option == 'gn':
                succ, filename = self.getNewsofKeyword(cmd)
                if succ:
                    sndmsg =  '@fil@' + filename # 发送文件
                else:
                    sndmsg = '新闻列表获取失败！\n'
            elif Option == 'gf':
                succ, filename = self.getFieldNews(cmd)
                if succ:
                    sndmsg =  '@fil@' + filename # 发送文件
                    print(sndmsg)
                else:
                    sndmsg = '同行动态列表获取失败！\n' + str(filename)
            else:
                sndmsg = sndmsg + WeChat.getRespons(msg['Text'], 90)
        WeChat.SendWeChatTextMsg(sndmsg, msg['FromUserName'], msg['User']['NickName'], self.logfile)
    def isUserInUserList(self, userAccountName):
        Output = False;
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
            errmsg = '# 新闻监控类写入日志异常：' + str(e)
            print(errmsg)
            self.SendAlert2Master(str(self.label) + str(errmsg))
    def __del__(self):
        print('删除' + str(self.label))
    def Bye(self, Debug):
        if not Debug:
            self.pickleDump2file(self.pricklefileName)
        print(self.extMsg)
 #       WeChat.SendWeChatMsgToUserList(self.UserList, self.extMsg, self.logfile)
    def OnDuty(self):
        return True #全时工作
    def SendAlert2Master(self, errmsg):
        errmsg2 = '程序异常，提醒管理员：\n' + str(errmsg)
        self.write2Log(str(self.label) + str(errmsg2))
        WeChat.SendWeChatMsgToUserList(self.Master, errmsg2, self.logfile)
        print(str(self.label) + str(errmsg2))
    def scrapNews(self, keywords, newsNum):
        Output_sum = {}
        succ = False
        # 每个Output的格式如下
        # 命名：'平台名_' + str(author) + ('%04d_%02d_%02d_%02d_%02d_%02d'%(temptime.year, temptime.month, temptime.day, temptime.hour, temptime.minute,temptime.second) + str(Countor))
        # title
        # source
        # author
        # date
        # time_flag
        # link
        # summary
        # platform
        # 先搜索其主关键词，如果有福关键词，也一并搜索
        # subkeywordList
        localKeyWord = set([keywords]) # 默认为主关键词
        if keywords in self.subkeywordList:
            localKeyWord = localKeyWord | self.subkeywordList[keywords] # 求并集
        # 循环搜寻主、副关键词新闻
        #self.serachRangeOpts[key]
        tempFlag = False
        if keywords not in self.serachRangeOpts:
            self.serachRangeOpts[keywords] = {'百度新闻':True, '百度网页':False,'搜狗新闻':True,'搜狗微信':False,'今日头条':True }
            tempFlag = True
        for a_keyWord in localKeyWord:
            Flag_BD = Flag_SG = Flag_SGWe = Flag_JRTT = FG_BDWeb = False
            if self.serachRangeOpts[keywords]['百度新闻']:
                Flag_BD, news = self.searchBaiDuNews(a_keyWord, newsNum)  # 百度新闻
                if Flag_BD:
                    Output_sum.update(news)
            if self.serachRangeOpts[keywords]['搜狗新闻']:
                Flag_SG, news = self.searchSouGouNews(a_keyWord, newsNum) # 搜狗新闻
                if Flag_SG:
                    Output_sum.update(news)
            if self.serachRangeOpts[keywords]['搜狗微信']:
                Flag_SGWe, news = self.searchSouGou_WeChatNews(a_keyWord, newsNum) # 搜狗-微信公众号
                if Flag_SGWe:
                    Output_sum.update(news)           
            if self.serachRangeOpts[keywords]['今日头条']:
                Flag_JRTT, news = self.searchJinRiTouTiao(a_keyWord, newsNum) # 今日头条
                if Flag_JRTT:
                    Output_sum.update(news) 
            if self.serachRangeOpts[keywords]['百度网页']:
                FG_BDWeb, news = self.searchBaiDuWeb(a_keyWord, newsNum) # 百度网页
                if FG_BDWeb:
                    Output_sum.update(news)         
            succ = succ or Flag_BD or Flag_SG or Flag_SGWe or Flag_JRTT or FG_BDWeb
        # Output 中去重（主副关键词搜索结果可能接近）
        
        if succ:
            new_output  = {}
            news_assemble = set()
            for news in Output_sum:
                tempvalues = new_output.values()
                if Output_sum[news] not in tempvalues: #去重(仅去除完全相同的新闻)
                    keysen = ['周末消息重磅来袭', '重磅利好', '重大利好消息', '节后重大利好消息', '最新消息利好',  '最新利好消息', '罕见利好消息', '特大利好强势来袭', '特大利好消息']
                    symbol = [' ', '、']
                    Flag = True
                    for key in keysen:
                        if key in Output_sum[news]['title']:
                            Flag = False
                    if '澳门' in Output_sum[news]['title'] and '赌城' in Output_sum[news]['title']:
                        Flag = False
                    if '澳门' in Output_sum[news]['title'] and '娱乐场' in Output_sum[news]['title']:
                        Flag = False    
                    if '华股财经' in Output_sum[news]['author']:
                        Flag = False                           
                    for symb in symbol:
                        if Output_sum[news]['title'].count(symb) >= 3:
                            Flag = False
                    if (Output_sum[news]['title'] + Output_sum[news]['author']) in news_assemble:
                        Flag = False
                    if Flag:
                        news_assemble.update([Output_sum[news]['title'] + Output_sum[news]['author']])
                        new_output.setdefault(news, Output_sum[news])
#            print(self.label + '抓取关键词 【' + str(keywords) + '】新闻成功！' )
        else:
            print(self.label + '抓取关键词 【' + str(keywords) + '】新闻失败！' )
            new_output  = {}
        if tempFlag:
            self.serachRangeOpts.pop(keywords) # 如果是临时搜索，则从列表中移除该变量
        return succ, new_output ## 字典形式的           
            
    def searchBaiDuNews(self, keywords, newsNum):
        Output = {} 
        newsPerPage = 20
        numOfPage = math.ceil(newsNum/newsPerPage)
        Countor = 0
        succ = False
        print('百度新闻平台搜索关键词：' + keywords)
        for k in range (0, numOfPage):
            url = 'http://news.baidu.com/ns?word=' + keywords + '&pn=%s&cl=2&ct=1&tn=news&rn=20&ie=utf-8&bt=0&et=0'% (k* newsPerPage)
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/52.0.2743.116 Safari/537.36'}
            response = myResponse(url=url,headers=headers, encode = 'utf-8')
            soup = BeautifulSoup(response.text,'lxml')
            div_items = soup.find_all('div', class_ = 'result') # 获得 div标签下， class = 'result'的内容:即提取div； 在每个find函数中，第一个如’div'为标签，在html中总是成对出现的，第二个是标签后面跟的
            if len(div_items) < newsPerPage:
                numOfPage = k + 1
            
            for div in div_items:
                if Countor >= int(newsNum):
                    break
                Countor = Countor + 1
                # 去除title,连接
                try:
                    a_title = div.find('h3', class_='c-title').find('a').get_text() #获得 h3标签下，class为c-title的内容，然后在其中，获得a标签下的所有文本内容
                except Exception as e:
                    a_title = '标题解析错误'
                try:
                    a_href = div.find('h3', class_='c-title').find('a').get('href') # 获得链接
                except Exception as e:
                    a_href = '链接解析错误'
                try:
                    a_summary = div.find('div', class_='c-summary').get_text().replace(u'\xa0',u' ').replace(u'\u2022','·')     # 获得简介
                except Exception as e:
                    a_summary = '简介解析错误'
                try:
                    a_author = div.find('div', class_='c-summary').find('p', class_="c-author").get_text().replace(u'\xa0',u' ')
                    a_summary2 = a_summary[len(a_author): len(a_summary)] # 在summary中去掉 author信息
                except Exception as e:
                    a_author = '作者解析错误 日期解析错误 时间解析错误'
                    a_summary2 = a_summary
                
                # 拆分a_author
                source = str(a_author)
                source = source.split(' ')
                source = filter(lambda x: x != '',source) # 去除空元素
                source = [i for i in source]
                time_flag = False  # True： 准确时间， False，大约时间，需要在后续时间进行更新
                if len(source) == 2:
                    now = int(datetime.datetime.now().timestamp())
                    # 有种情况是作者不存在
                    author = source[0]
                    delta_time_str = source[1]
                    if ('年' in author and '月' in author and '日' in author) or '分钟' in author or '小时' in author:
                        # 这种情况下，一般是author不存在
                        author = '无名氏'
                        author_date  = source[1] + ' ' + source[2]
                        time_flag = True
                        succ = True
                        # 如果作者不存在，则分钟或小时形式的不存在，因为那样的话，len(source) = 1
                    else: # 作者存在
                        delta_time = 0
                        if '分钟' in delta_time_str:
                            delta_time = int(re.findall(r'(\w*[0-9]+)\w*',delta_time_str)[0])*60   # s, 大约估计时间
                        elif '小时' in delta_time_str:
                            delta_time = int(re.findall(r'(\w*[0-9]+)\w*',delta_time_str)[0])*3600 # s，大约估计时间
                        else:
                            print('str is  ' + delta_time_str)
                            delta_time = 0
                            errmsg = 'In searchBaiDuNews(): # Error: in scrapper news, analysis of the news time failed: ' + str(source) # (其他情况，delta_time置为0，即认为是现在发生的)
                        author_time_format = time.localtime(now - delta_time)
                        author_date = '%04d年%02d月%02d日 %02d:%02d'%(author_time_format.tm_year, author_time_format.tm_mon, author_time_format.tm_mday, author_time_format.tm_hour, author_time_format.tm_min)
                        succ = True
                elif len(source) == 3:
                    time_flag = True
                    author = source[0]
                    author_date = source[1] + ' ' + source[2]
                    succ = True
                elif len(source) ==  1:
                     # 作者不存在（时间为小时或者分钟形式）或者时间不存在（仅为作者）
                     if '分钟' in source[0] or '小时' in source[0]:
                         # 无作者
                         author = '无名氏'                       
                         now = int(datetime.datetime.now().timestamp())
                         # 有种情况是作者不存在
                         delta_time_str = source[0]
                         delta_time = 0
                         if '分钟' in delta_time_str:
                             delta_time = int(re.findall(r'(\w*[0-9]+)\w*',delta_time_str)[0])*60   # s, 大约估计时间
                         else:
                             delta_time = int(re.findall(r'(\w*[0-9]+)\w*',delta_time_str)[0])*3600 # s，大约估计时间
                         author_time_format = time.localtime(now - delta_time)
                         author_date = '%04d年%02d月%02d日 %02d:%02d'%(author_time_format.tm_year, author_time_format.tm_mon, author_time_format.tm_mday, author_time_format.tm_hour, author_time_format.tm_min)
                     else: # 时间不存在
                         author = source[0]
                         now = time.localtime() # 将现在置为其准确时间
                         author_date = '%04d年%02d月%02d日 %02d:%02d'%(now.tm_year, now.tm_mon, now.tm_mday, now.tm_hour, now.tm_min)
                         time_flag = True
                     succ = True
                else: 
                    errmsg = '未发现新闻:' +  str(source)
                    print(str(errmsg))
                    continue
                # 新建字典
                temptime = datetime.datetime.now()
                if keywords not in a_title and keywords not in a_summary:
#                    print("这条新闻不属于" + keywords +':\n标题：' + a_title + '\n简介：' + a_summary2 + '\n')
                    continue  
                Output.setdefault('news_' + str(author) + ('%04d_%02d_%02d_%02d_%02d_%02d'%(temptime.year, temptime.month, temptime.day, temptime.hour, temptime.minute,temptime.second) + str(Countor)), \
    {'title':a_title, 'source':a_author, 'author': author, 'date': author_date, 'timeflag':time_flag, 'link':a_href, 'summary':a_summary2,'platform': '百度新闻'}) 
        return succ, Output ## 字典形式的
    def searchBaiDuWeb(self, keywords, newsNum):
        Output = {} 
        newsPerPage = 10
        numOfPage = math.ceil(newsNum/newsPerPage)
        Countor = 0
        succ = False
        print('百度网页平台搜索关键词：' + keywords)
        for k in range (0, numOfPage):
            url = 'https://www.baidu.com/s?wd=' + keywords + '&pn=%s&cl=0&tn=baidurt&ie=utf-8&rtt=1&bsst=1'% (k* newsPerPage)
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/52.0.2743.116 Safari/537.36'}
            response = myResponse(url=url,headers=headers)
            soup = BeautifulSoup(response.text,'html.parser')
            div_items = soup.find_all('td', class_ = 'f') 
            if len(div_items) < newsPerPage:
                numOfPage = k + 1
            
            for div in div_items:
                if Countor >= int(newsNum):
                    break
                Countor = Countor + 1
                # 去除title,连接
                try:
                    a_title = div.find('h3', class_='t').find('a').get_text().replace(u'\xa0',u' ').replace('\t','').replace('\n','') #获得 h3标签下，class为c-title的内容，然后在其中，获得a标签下的所有文本内容
                except Exception as e:
                    a_title = '标题解析错误'
                try:
                    a_href = div.find('h3', class_='t').find('a').get('href') # 获得链接
                except Exception as e:
                    a_href = '链接解析错误'
                try:
                    a_summary = div.find('font', size='-1').get_text().replace(u'\xa0',u' ').replace('\t','').replace('\n','')     # 获得简介
                except Exception as e:
                    a_summary = '简介解析错误'
                try:
                    a_author = div.find('div', class_='realtime').get_text().replace(u'\xa0',u' ').replace('\t','').replace('\n','')
                    a_summary2 = a_summary[len(a_author): len(a_summary)].replace(div.find('font', size='-1').find('font').get_text().replace(u'\xa0',u' ').replace('\t','').replace('\n',''),'')
                except Exception as e:
                    a_author = '作者解析错误 日期解析错误 时间解析错误'
                # 拆分a_author
                source = str(a_author)
                source = source.split(' ')
                source = filter(lambda x: x != '',source) # 去除空元素
                source = [i for i in source]
                
                time_flag = False  # True： 准确时间， False，大约时间，需要在后续时间进行更新
                if len(source) == 3:
                    now = int(datetime.datetime.now().timestamp())
                    author = source[0]
                    delta_time_str = source[2]
                    if '分钟' in delta_time_str:
                        delta_time = int(re.findall(r'(\w*[0-9]+)\w*',delta_time_str)[0])*60   # s, 大约估计时间
                        author_time_format = time.localtime(now - delta_time)
                        author_date = '%04d年%02d月%02d日 %02d:%02d'%(author_time_format.tm_year, author_time_format.tm_mon, author_time_format.tm_mday, author_time_format.tm_hour, author_time_format.tm_min)               
                    elif '小时' in delta_time_str:
                        delta_time = int(re.findall(r'(\w*[0-9]+)\w*',delta_time_str)[0])*3600 # s，大约估计时间
                        author_time_format = time.localtime(now - delta_time)
                        author_date = '%04d年%02d月%02d日 %02d:%02d'%(author_time_format.tm_year, author_time_format.tm_mon, author_time_format.tm_mday, author_time_format.tm_hour, author_time_format.tm_min)                  
                    elif '天' in delta_time_str:
                        delta_time = int(re.findall(r'(\w*[0-9]+)\w*',delta_time_str)[0])*3600*24 # s，大约估计时间   
                        author_time_format = time.localtime(now - delta_time)
                        author_date = '%04d年%02d月%02d日 %02d:%02d'%(author_time_format.tm_year, author_time_format.tm_mon, author_time_format.tm_mday, author_time_format.tm_hour, author_time_format.tm_min)                  
                    else:
                        '2017-09-25'
                        temp_date = delta_time_str.split('-')
                        try:
                            author_date = temp_date[0] + '年' +  temp_date[1] + '月' + temp_date[2] + '日' + ' --:--'
                            time_flag = True
                        except Exception as e:
                            author_date = '日期解析错误'
                    succ = True
                else: 
                    author = '作者解析错误'
                    author_date = '日期解析错误'
                    succ = True
                # 新建字典
                temptime = datetime.datetime.now()
                if keywords not in a_title and keywords not in a_summary:
#                    print("这条新闻不属于" + keywords +':\n标题：' + a_title + '\n简介：' + a_summary2 + '\n')
                    continue  
                Output.setdefault('news_' + str(author) + ('%04d_%02d_%02d_%02d_%02d_%02d'%(temptime.year, temptime.month, temptime.day, temptime.hour, temptime.minute,temptime.second) + str(Countor)), \
        {'title':a_title, 'source':a_author, 'author': author, 'date': author_date, 'timeflag':time_flag, 'link':a_href, 'summary':a_summary2,'platform': '百度网页'}) 
        return succ, Output ## 字典形式的    
## 搜索 搜狗新闻
    
    def searchSouGouNews(self, keywords, newsNum):
        print('搜狗新闻平台搜索关键词：' + keywords)
        if datetime.datetime.now().timestamp() < self.souGou_Thresh:
           print(str(datetime.datetime.now().timestamp()) + '--' + str(self.souGou_Thresh))
           errMsg = '搜狗新闻平台遭遇反爬虫系统，休息中！剩余时间：' +  str(math.floor((self.souGou_Thresh - datetime.datetime.now().timestamp())/60)) + ' 分钟！'  
           print(errMsg)
           return False, {}
        Output = {} 
        newsPerPage = 10
        numOfPage = math.ceil(newsNum/newsPerPage)
        Countor = 0
        succ = False
        for k in range (0, numOfPage):
            time.sleep(1)
            url = 'http://news.sogou.com/news?query='+ keywords + '&page=%s&p=76330300&dp=1'% (k + 1)
            headers = {'User-Agent':'Mozilla/5.0 (Windows NT 6.1; WOW64; rv:23.0) Gecko/20100101 Firefox/56.0'}

            request_Try = 0
            maxTry = 50
            request_Succ = False
            while True:
                try:
                    request_Try += 1
                    proxy = {'http':requests.get(url='http://127.0.0.1:5010/get/').text}
       #             print('#搜狗新闻# 关键词 %s 第 %s 次尝试, 使用代理：%s' % (keywords, request_Try, proxy))
                    response = requests.get(url = url, headers = headers, proxies = proxy, timeout = 4)
                    response.encoding = 'GBK'
                    soup = BeautifulSoup(response.text,'lxml')
                    if '404 Not Found' in soup.text or ('Authentication Required' in soup.text) or ('Authentication required' in soup.text) or "To protect our users, we can't process this request" in soup.text or 'HTTP/1.1 400 Bad Request' in soup.text:
      #                 print('网页抓取失败：%s' % soup.text)
                        pass
                    else:
                        pass
      #                  print('网页抓取成功！')
                        request_Succ = True     
                        break
                    if request_Try > maxTry:
                        break
                except Exception as e:
                    if request_Try > maxTry:
                        break
            
#            response = myResponse(url=url, headers = headers,encode = 'GBK')
#            soup = BeautifulSoup(response.text,'lxml')
            div_items = soup.find_all('div', class_ = 'vrwrap') 
            if len(div_items) == 0:
                if not request_Succ:#'找到相关新闻约0篇' not in response.text and '请检查您输入的关键词是否有错误' not in response.text and '404 Not Found' in response.text:
                    errMsg = '搜狗新闻平台遭遇反爬虫系统！'
                    print(errMsg)
  #                  print(soup.text)
                    self.write2Log(response.text)
                    WeChat.SendWeChatMsgToUserList(self.Master, errMsg, self.logfile)
#                    self.souGou_Thresh = datetime.datetime.now().timestamp() + self.souGou_RestTime*60 # 休息2小时
                else:
                    print('该页没有找到 %s 相关新闻！' % keywords)
 #                   print(soup.text)
            if len(div_items) < newsPerPage:
                numOfPage = k + 1
            for div in div_items:
                if div == div_items[-1]:
                    continue # 搜狗新闻中最后一条无效，跳过
                # 去除title,连接
                if Countor >= int(newsNum):
                    break
                try:
                    a_title = div.find('h3', class_='vrTitle').find('a').get_text() #获得 h3标签下，class为c-title的内容，然后在其中，获得a标签下的所有文本内容
                except Exception as e:
                    a_title = '标题解析错误'
                try:
                    a_href = div.find('h3', class_='vrTitle').find('a').get('href') # 获得链接
                except Exception as e:
                    a_href = '链接解析错误'
                try:
                    a_summary = div.find('div', class_='news-detail').find('p', class_='news-txt').find('span').get_text()      # 获得简介
                except Exception as e:
                    try:
                        a_summary = div.find('div', class_='news-detail').find('p', class_='news-txt').get_text().replace(u'\xa0',u' ').replace(u'\2122',u'TM')
                    except Exception as e:
                        a_summary = '简介解析错误'
                try:
                    a_author = div.find('div', class_='news-detail').find('p', class_="news-from").get_text().replace(u'\xa0',u' ').replace(u'\2122',u'TM')
                except Exception as e:
                    a_author = '作者解析错误 日期解析错误'
                # 拆分a_author
                source = str(a_author)
                source = source.split(' ')
#                print(source)
                source = filter(lambda x: x != '',source) # 去除空元素
                source = [i for i in source]
                time_flag = False  # True： 准确时间， False，大约时间，需要在后续时间进行更新
                # source所有可能类型：慧聪纺织网资讯中心 1小时前，新浪财经 2017-10-21，中国安防展览网 30分钟前，
                if len(source) == 2: 
                    now = int(datetime.datetime.now().timestamp())
                    succ = True
                    if a_author == '作者解析错误 日期解析错误':
                        author = '作者解析错误'
                        author_date = '日期解析错误'
                    else:               
                        author = source[0]
                        delta_time_str = source[1]
                        if '分钟' in author or '小时' in author:
                            # 这种情况下，一般是author不存在
                            author = '作者解析错误'
                            author_date  = source[1] + ' ' + source[2]
                            succ = True
                        else: # 作者存在
                            delta_time = 0
                            if '分钟' in delta_time_str:
                                delta_time = int(re.findall(r'(\w*[0-9]+)\w*',delta_time_str)[0])*60   # s, 大约估计时间
                                author_time_format = time.localtime(now - delta_time)
                                author_date = '%04d年%02d月%02d日 %02d:%02d'%(author_time_format.tm_year, author_time_format.tm_mon, author_time_format.tm_mday, author_time_format.tm_hour, author_time_format.tm_min)
                            elif '小时' in delta_time_str:
                                delta_time = int(re.findall(r'(\w*[0-9]+)\w*',delta_time_str)[0])*3600 # s，大约估计时间
                                author_time_format = time.localtime(now - delta_time)
                                author_date = '%04d年%02d月%02d日 %02d:%02d'%(author_time_format.tm_year, author_time_format.tm_mon, author_time_format.tm_mday, author_time_format.tm_hour, author_time_format.tm_min)
                            else:
                                temp_date = delta_time_str.split('-')
                                try:
                                    author_date = temp_date[0] + '年' +  temp_date[1] + '月' + temp_date[2] + '日' + ' --:--'
                                    time_flag = True
                                except Exception as e:
                                    author_date = '日期解析错误'
                elif len(source) ==  1:
                     # 作者不存在（时间为小时或者分钟形式）或者时间不存在（仅为作者）
                     if '分钟' in source[0] or '小时' in source[0]:
                         # 无作者
                         author = '作者解析错误'                       
                         now = int(datetime.datetime.now().timestamp())
                         # 有种情况是作者不存在
                         delta_time_str = source[0]
                         delta_time = 0
                         if '分钟' in delta_time_str:
                             delta_time = int(re.findall(r'(\w*[0-9]+)\w*',delta_time_str)[0])*60   # s, 大约估计时间
                         else:
                             delta_time = int(re.findall(r'(\w*[0-9]+)\w*',delta_time_str)[0])*3600 # s，大约估计时间
                         author_time_format = time.localtime(now - delta_time)
                         author_date = '%04d年%02d月%02d日 %02d:%02d'%(author_time_format.tm_year, author_time_format.tm_mon, author_time_format.tm_mday, author_time_format.tm_hour, author_time_format.tm_min)
                     else: # 时间不存在
                         author = source[0]
                         author_date = '日期解析错误'
                         time_flag = True
                     succ = True
                else: 
                    author = '作者解析错误'
                    author_date = '日期解析错误'                    
                # 新建字典
                temptime = datetime.datetime.now()
                if keywords not in a_title and keywords not in a_summary:
#                    print("这条新闻不属于" + keywords +':\n标题：' + a_title + '\n简介：' + a_summary + '\n')
                    continue
                Countor = Countor + 1
                Output.setdefault('news_' + str(author) + ('%04d_%02d_%02d_%02d_%02d_%02d'%(temptime.year, temptime.month, temptime.day, temptime.hour, temptime.minute,temptime.second) + str(Countor)), \
    {'title':a_title, 'source':a_author, 'author': author, 'date': author_date, 'timeflag':time_flag, 'link':a_href, 'summary':a_summary,'platform': '搜狗新闻'}) 
 #       print(Output)
        return succ, Output ## 字典形式的
## 搜索 搜狗|微信公众平台
    
    def searchSouGou_WeChatNews(self, keywords, newsNum):
        print('搜狗-微信公众号平台搜索关键词：' + keywords)
        if datetime.datetime.now().timestamp() < self.souGou_WeChat:
           print(str(datetime.datetime.now().timestamp()) + '--' + str(self.souGou_WeChat))
           errMsg = '搜狗-微信公众号平台遭遇反爬虫系统，休息中！剩余时间：' +  str(math.floor((self.souGou_WeChat - datetime.datetime.now().timestamp())/60)) + ' 分钟！' 
           print(errMsg)
           return False, {}
        newsNum = 50 # 微信公众号强制性只搜索 50条新闻
        Output = {} 
        newsPerPage = 10
        numOfPage = math.ceil(newsNum/newsPerPage)
        Countor = 0
        succ = False
        for k in range (0, numOfPage):
            url = 'http://weixin.sogou.com/weixin?usip=&query='+ keywords + '&ft=&tsn=1&et=&interation=&type=2&wxid=&page=%s&ie=utf8'% (k + 1) # tsn = 1表示只搜索当日新闻
            headers = {'User-Agent':'Mozilla/5.0 (Windows NT 6.1; WOW64; rv:23.0) Gecko/20100101 Firefox/23.0'}
            
            request_Try = 0
            maxTry = 20
            request_Succ = False
            while True:
                try:
                    request_Try += 1
                    proxy = {'http':requests.get(url='http://127.0.0.1:5010/get/').text}
                    print('#搜狗微信# 关键词 %s 第 %s 次尝试, 使用代理：%s' % (keywords, request_Try, proxy))
                    response = requests.get(url = url, headers = headers, proxies = proxy, timeout = 4)
                    response.encoding = 'utf-8'
                    soup = BeautifulSoup(response.text,'lxml')
                    if '用户您好，您的访问过于频繁，为确认本次访问为正常用户行为' in soup.text or ('Authentication Required' in soup.text) or ('Authentication required' in soup.text) or "To protect our users, we can't process this request" in soup.text or 'HTTP/1.1 400 Bad Request' in soup.text:
                       print('网页抓取失败：%s' % soup.text)
                    else:
                        print('网页抓取成功！')
                        request_Succ = True     
                        break
                    if request_Try > maxTry:
                        break
                except Exception as e:
                    if request_Try > maxTry:
                        break            
            
#            response = myResponse(url=url,headers=headers, encode = 'utf-8')
        #    print(response.text)
#            soup = BeautifulSoup(response.text,'lxml')
            div_items = soup.find_all('div', class_ = 'txt-box') 
            if len(div_items) == 0:
                if not request_Succ:
#                and '用户您好，您的访问过于频繁，为确认本次访问为正常用户行为' in response.text:
                    errMsg = '搜狗-微信公众号平台遭遇反爬虫系统！'
                    print(errMsg)
  #                  print(soup.text)
                    WeChat.SendWeChatMsgToUserList(self.Master, errMsg, self.logfile) 
                    self.souGou_WeChat = datetime.datetime.now().timestamp() + self.souGou_RestTime*60 # 休息2小时
                    return False, {}
                else:
                    print('搜狗-微信 该页没有找到 %s 相关新闻！' % keywords)
 #                   print(soup.text)
        #    print(div_items)
            for div in div_items:
                if Countor >= int(newsNum):
                    break
                Countor = Countor + 1                    
                # 去除title,连接
                try:
                    a_title = div.find('h3').find('a').get_text() #获得 h3标签下，class为c-title的内容，然后在其中，获得a标签下的所有文本内容
                except Exception as e:
                    a_title = '标题解析错误'
                try:
                    a_href = div.find('h3').find('a').get('href') # 获得链接
                except Exception as e:
                    a_href = '链接解析错误'
                try:
                    a_summary = div.find('p', class_='txt-info').get_text()      # 获得简介
                except Exception as e:
                    a_summary = '简介解析错误'
                try:
                    a_author = div.find('div', class_='s-p').find('a', class_="account").get_text()
                except Exception as e:
                    a_author = '作者解析错误'
                try:
                    a_date = time.localtime(int(re.findall(r'(\w*[0-9]+)\w*',div.find('div', class_='s-p').find('span').get_text())[0]))
                    a_date = '%04d年%02d月%02d日 %02d:%02d'%(a_date.tm_year, a_date.tm_mon, a_date.tm_mday, a_date.tm_hour, a_date.tm_min)
                except Exception as e:
                    a_date = '日期解析错误'            
                time_flag = True  # True： 准确时间， False，大约时间，需要在后续时间进行更新
                succ = True
                # 新建字典
                temptime = datetime.datetime.now()
                if keywords not in a_title and keywords not in a_summary:
#                    print("这条新闻不属于" + keywords +':\n标题：' + a_title + '\n简介：' + a_summary + '\n')
                    continue                
                Output.setdefault('news_' + str(a_author) + ('%04d_%02d_%02d_%02d_%02d_%02d'%(temptime.year, temptime.month, temptime.day, temptime.hour, temptime.minute,temptime.second) + str(Countor)), \
    {'title':a_title, 'source':a_author, 'author': a_author, 'date': a_date, 'timeflag':time_flag, 'link':a_href, 'summary':a_summary,'platform': '搜狗-微信公众号'}) 
#        print(Output)
            if len(div_items) < newsPerPage: # 如果页面结束，则停止搜搜
                numOfPage = k + 1
        return succ, Output ## 字典形式的

## 搜索 今日头条
    def searchJinRiTouTiao(self, keywords, newsNum):
        print('今日头条搜索关键词：' + keywords)
        Output = {} 
        newsPerReq = 10
        Countor = 0
        offset = 0
        succ = False
        time_flag = False        
        while Countor < newsNum:
            url = 'http://www.toutiao.com/search_content/?offset=' + str(offset) + '&format=json&keyword=' + keywords + '&autoload=true&count=' + str(newsPerReq) +  '&cur_tab=1'
        #    time.sleep(random.randint(3, 5))
            wbdata = requests.get(url).text
#            wbdata.encoding = 'utf-8'
            data = json.loads(wbdata)
            news = data['data']
            offset += newsPerReq
            Countor += newsPerReq
            for item in news:
                if 'title' in item.keys() and item['title']:
                    a_title = item['title']
                    Countor += 1
                else:
                    continue
                if 'source' in item.keys() and item['source']:
                    a_author = item['source']
                else:
                    a_author = '来源无法解析'
                    print(item['source'])
                if 'article_url' in item.keys() and item['article_url']:
                    a_href = item['article_url']
                else:
                    if 'url' in item.keys() and item['url']:
                        a_href = item['url']
                    else:
                        a_href = '链接无法解析'   
                        print(item['article_url'])
                if 'abstract' in item.keys() and item['abstract']:
                    a_summary = item['abstract']
                else:
                    a_summary = '简介无法解析' 
                    print(item['abstract'])             
                if 'datetime' in item.keys() and item['datetime']:
                    a_date2 = item['datetime']
                    time_flag = True
                    try:
                        a_date = time.strptime(a_date2, "%Y年%m月%d日 %H:%M:%S")
                        time_flag = True
                    except Exception as e:
                        a_date = a_date2
                else:
                    a_date = '日期无法解析'  
                    print(item['datetime'])  
                temptime = datetime.datetime.now()    
                if keywords not in a_title and keywords not in a_summary:
#                    print("这条新闻不属于" + keywords +':\n标题：' + a_title + '\n简介：' + a_summary + '\n')
                    continue
                Output.setdefault('news_' + str(a_author) + ('%04d_%02d_%02d_%02d_%02d_%02d'%(temptime.year, temptime.month, temptime.day, temptime.hour, temptime.minute,temptime.second) + str(Countor)), \
        {'title':a_title, 'source':a_author, 'author': a_author, 'date': a_date, 'timeflag':time_flag, 'link':a_href, 'summary':a_summary,'platform': '今日头条'})   
 #           print(Output)
            if len(Output) > 0:
                succ = True
            return succ, Output ## 字典形式的
    
    def writeNews2File(self, sortedNewsDic, fileName, header, mode):
        # 只在新闻有变动的时候才更新
        try:
            with open(fileName, mode, encoding='utf-8') as file:
                with self.mu:
                    file.write(header)
                    for news in sortedNewsDic:
                        body = news[1]
                        file.write("标题: " + body['title'] + "\n")
                        source = body['author'] + '  ' + body['date'] + ''
                        if not body['timeflag']:
                            source = source + '(大约)'
                        file.write("来源: " + source + "\n")
                        file.write("链接: " + body['link'] + "\n")
                        file.write("简介: " + body['summary'] + "\n\n")
        except Exception as e: # 一般错误，通知管理员即可
            errmsg = '# 新闻写入文件异常 writeNews2File:' + str(e)
            print(errmsg)
            self.SendAlert2Master(str(errmsg))
            pass
    def sortNewsbyDate(self, newsDic):
        # 将字典按照'date'排序
        return sorted(newsDic.items(),key = lambda d:d[1]['date'], reverse = True)
    def sortNewsbyAuthor(self,newsDic):
        # 将字典按照'date'排序
        return sorted(newsDic.items(),key = lambda d:d[1]['author'], reverse = True)
    def getNews(self, keywords, numOfNews, sortMethod):
        # 返回排序后的新闻列表
        succ, news = self.scrapNews(keywords, int(numOfNews))
        sortednews = []
        if succ:
            if sortMethod == 'date':
                sortednews = self.sortNewsbyDate(news)
            elif sortMethod == 'author':
                sortednews = self.sortNewsbyAuthor(news)
            else:
                # 不排序
                with  self.mu:
                    for item in news:
                        sortednews.append((item, news[item]))
#                print('# 错误: in getNews(): 新闻排序方法未定义，按照默认date排序!\n')
#               sortednews = self.sortNewsbyDate(news)
        return succ, sortednews
    def sameNews(self, news1, news2):
        # new1 和 new2是仅包含'author', 'date', 'link', 'source', 'summary', 'timeflag', 'ttitle'的新闻字典 
        # 如果两条新闻，author 和 title一样，则认为是同一条新闻
        var_Forward = ' 【疑似转载】 '
        if news1['title'] == news2['title']:
            if news1['author'].replace(var_Forward,'') == news2['author'].replace(var_Forward,''):
                return True # 如果标题与作者均相同，则同一条新闻
            else:
                # 标题相同，作者不同，则通过判断发表时间，将后发表的标记为[疑似转载]
                try:
                    date1 = dateParser.parse(news1['date'].replace('--','').replace('年','-').replace('月','-').replace('日','')).timestamp()
                    date2 = dateParser.parse(news2['date'].replace('--','').replace('年','-').replace('月','-').replace('日','')).timestamp()
                    if date1 > date2:
                        news1['author'] = news1['author'].replace(var_Forward,'').replace('[疑似转载]','')
                        news1['author'] +=var_Forward
                    else:
                        news2['author'] = news2['author'].replace(var_Forward,'').replace('[疑似转载]','')
                        news2['author'] +=var_Forward
                    return False
                except Exception as e:
                    print('# 判断是否转载：日期格式解析错误！')
                    return True
        else:
            return False
    def updateDateStamp(self, sortedNewsDic):
        with self.mu:
            temp_sortedNewsDic = sortedNewsDic
            for k in range(len(sortedNewsDic)):  ##已有的库
                body = sortedNewsDic[k][1]
                timeStamp = body['timeflag']
                if not timeStamp:
                     findNews = False
                     updatedtimeStamp = ''
                     timeFlag = False
                     if not findNews:
                         succ, news_temp = self.scrapNews(body['title'], 60)   # 如果找不到，从最近20条中找
                         if succ:
                             for newsItem in news_temp:
                                 if self.sameNews(news_temp[newsItem], body):
                                     updatedtimeStamp = news_temp[newsItem]['date']
                                     timeFlag = news_temp[newsItem]['timeflag']
                                     findNews = True
                                     break
                     if findNews:
                         temp_sortedNewsDic[k][1]['date'] = updatedtimeStamp
                         temp_sortedNewsDic[k][1]['timeflag'] = timeFlag
                         msg = '新闻' + '## ' + temp_sortedNewsDic[k][1]['title'] + ' ## 的时间戳更新:\n 从 ' + sortedNewsDic[k][1]['date'] + ' 更新为：' + updatedtimeStamp
                         if timeFlag:
                             msg = msg + '\n 时间改为准确值！'
                         msg = msg + '\n'
                         self.write2Log(msg)
                         print(msg)
        return   temp_sortedNewsDic
#--------------------------------操作用户列表-------------------------------------------#    
    def printUserList(self):
        Output = ''
        if len(self.UserList) < 1:
            Output = Output + self.getMainUser() + ': 用户列表为空！'
        else:
            Output = Output + self.getMainUser() + '用户列表如下:\n' 
            with self.mu:
                for user in self.UserList: # 子类中用户
                    # 分别打印昵称，用户名和NickName
                    Output = Output + '标称名 -- ' + str(user) + '， 用户名 -- ' + str(self.UserList[user]['UserName']) + '， 昵称 -- ' + str(self.UserList[user]['NickName']) + '\n'
        return Output
    def printInfo(self):
        # 基本信息
        Output = '\n标签： ' + str(self.label) + '      主用户： ' + self.getMainUser() + '       作者: ' + self.__Author__ + ' \n'
        # 用户列表
        Output = Output +  self.printUserList()
        # 关键词里列表及其有效期
        Output = Output + self.printKwdList()
        Output = Output + self.printFiledCompany()
        Output = Output + '工作日志文件名为：' + str(self.logfile) + '\n'    
        return Output    

    def isUserinList(self, userName):
        findUser = False
        with self.mu:
            for user in self.UserList:
                if userName == self.UserList[user]['UserName']:
                    findUser = True 
        return findUser
    def printKwdList(self):
        Output = ''
        if len(self.keywordList) < 1:
            Output = Output + self.getMainUser() + ': 关键词列表为空！'
        else:
            Output = '用户 '+ str(self.getMainUser()) + ' 关键词列表及其剩余有效期如下：\n'
            with self.mu:
                for keyword in self.keywordList:
                    Output = Output + '【 ' + str(keyword) + ' 】'
                    if keyword in self.subkeywordList:
                        Output += '（' + str(self.subkeywordList[keyword]).replace('{','').replace('}','') + '）'
                    Output += ' 监控范围：' + '百度新闻：' + ('开启；' if self.serachRangeOpts[keyword]['百度新闻'] else '关闭；')
                    Output += '百度网页：' + ('开启；' if self.serachRangeOpts[keyword]['百度网页'] else '关闭；')
                    Output += '搜狗新闻：' + ('开启；' if self.serachRangeOpts[keyword]['搜狗新闻'] else '关闭；')
                    Output += '搜狗微信：' + ('开启；' if self.serachRangeOpts[keyword]['搜狗微信'] else '关闭；')
                    Output += '今日头条：' + ('开启；' if self.serachRangeOpts[keyword]['今日头条'] else '关闭；')
                    Output += '剩余有效期：' + str(self.residDays[keyword]) + ' 天\n'
        return Output
    def Help(self):
        Output = ''' 这是这款新闻监控工具的说明书：
    这款工具旨在实现实时关键词监控，并按照时间排序。当监控关键词有新的新闻出现时，向用户发送预警信息。如果输入参数错误，则智能聊天。
    \'新闻 h\'：   \t获得这款工具的帮助文档。
    \'新闻 lu\'：  \t列出当前用户所在主用户下的用户列表。
    \'新闻 lkw\'： \t列出当前用户所在主用户下的监控关键词列表。
    \'新闻 gn ShiRui 一带一路 100 date\'： \t 发送ShiRui主账号下，【一带一路】 关键词最近100条新闻，并按日期（date)或者作者（author）排序排序
    \'新闻 gf ShiRui\'： \t 发送ShiRui主账号下，今日同行动态文件（仅特定人员开放）   
    \'新闻 lfc ShiRui\'： \t 列出ShiRui主账号下，关注的同行公司名（仅特定人员开放）
    '''
        return Output
    
    def addUser2UserList(self, paras, user):
#    \'新闻 au ShiRui XuKailong FlameMan\'： \t 在ShiRui主账号下，添加子账号,callName为XuKailong，昵称为FlameMan。子账户不能超过上限 5 个\n 
#    paras 中从au开始 
#    user为字符串
        if len(paras) !=4:
            Output = '# 错误: ' + str(self.label) + ' addUser2UserList(), 参数错误！\n' + str(paras) + '\n' 
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
                if not self.isUserinList(userName) : # 判断用户是否已经存在
                      if len(self.UserList) >= self.maxUserNum:
                           Output = '# 添加失败：用户数已经超过限制！'
                      else:
                          with self.mu:
                              #如果不存在，添加新用户
                              print('找到用户名为：' + str(userName))
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
#    \'新闻 ru ShiRui XuKailong\'： \t 在ShiRui主账号下，删除callName为XuKailong的子账号，子账号数量最少为1个\n   
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
#--------------------------------操作关键词-------------------------------------------#  
    def addKeyword2List(self, paras, user):
        #    \'新闻 akw ShiRui 一带一路[OneBelt+OneRoad](10111) 365\'： \t 在ShiRui主账号下，添加关键词【一带一路】，副关键词为OneBelt和OneRoad，其有效期设置为365天(关键词部分不能有空格, 10111分别表示百度新闻，百度网页，搜狗新闻，搜狗微信，今日头条是否开启\n
        # akw ShiRui 山东如意[如意集团+SMCP]（10111） 365，即将山东如意(副关键词：如意集团，SMCP)加入到ShiRui主账号名下, 有效期365天，, 10111分别表示百度新闻，百度网页，搜狗新闻，搜狗微信，今日头条是否开启
        
        if len(paras)!=4:
            Output = '# 错误: ' + str(self.label) + ' addKeyword2List(), 参数错误！\n' + str(paras) + '\n' 
            Output = Output + '关键词添加：\n \' akw ShiRui 一带一路[OneBelt+OneRoad](10111) 365\'\n  akw 表示添加关键词，ShiRui为主用户名，一带一路为添加的关键词，后面为副关键词，不能有空格，365为有效期, 10111分别表示百度新闻，百度网页，搜狗新闻，搜狗微信，今日头条是否开启'
            print(paras)
        else:
            mainUser = paras[1]
            temkeyword = paras[2].replace('【','[').replace('】',']').replace('（','(').replace('）',')')
            if '[' in temkeyword and ']' in temkeyword: # 包含副关键词
                keyword = temkeyword.split('[')[0]
                subKeywords = temkeyword.split('[')[1].split(']')[0].split('+')
            else:# 不包含副关键词
                keyword = temkeyword
            if '(' in temkeyword and ')' in temkeyword: # 包含搜索选项信息
                searchOpts = list(temkeyword.split('(')[1].split(')')[0])
            else: # 不包含搜索选项
                searchOpts = ['1','0','1','0','1']
            if len(searchOpts) != 5:
                print('参数格式错误，默认设置为：\n 百度新闻：开启\n 百度网页：关闭\n 搜狗新闻：开启\n 搜狗微信：开启\n 今日头条：开启\n')
                searchOpts = ['1','0','1','0','1']
            # 设置搜索选项
            tranSearchOpts = {}
            tranSearchOpts['百度新闻'] = True if searchOpts[0] == '1' else False 
            tranSearchOpts['百度网页'] = True if searchOpts[1] == '1' else False 
            tranSearchOpts['搜狗新闻'] = True if searchOpts[2] == '1' else False 
            tranSearchOpts['搜狗微信'] = True if searchOpts[3] == '1' else False 
            tranSearchOpts['今日头条'] = True if searchOpts[4] == '1' else False 
            resdays = int(paras[3])
            if mainUser != self.getMainUser():
                Output = '# 忽略添加关键词：主账号名不符合！'
                return Output
            try: 
                if keyword not in self.keywordList : # 判断关键词是否存在
                      #如果不存在，添加
                      with self.mu:
                          self.keywordList.append(keyword)
                          # 添加副关键词
                          self.subkeywordList.setdefault(keyword, set(subKeywords))
                          self.serachRangeOpts.setdefault(keyword, tranSearchOpts)
                          self.residDays.setdefault(keyword, resdays)
                          # 操作NewsList
                          self.createNewsListofOneKeyword(keyword)
                      Output = '关键词 【 ' + str(keyword) + ' 】 成功添加至用户 ' + str(mainUser) + ' 监控列表中！ by ' + user + '。 剩余有效期为： ' + str(resdays) + ' 天！'
                      WeChat.SendWeChatMsgToUserList(self.UserList, Output, self.logfile) # 向所有用户通知keywords变化信息
                else:
                    # 判断副关键词是否存在或一致
                    if keyword not in self.subkeywordList:
                        self.subkeywordList.setdefault(keyword, set(subKeywords))
                    else:
                        self.subkeywordList[keyword] = set(subKeywords) # 与已有结果求并集
                    if keyword not in self.serachRangeOpts:
                        self.serachRangeOpts.setdefault(keyword, tranSearchOpts)
                    else:
                        self.serachRangeOpts[keyword]= tranSearchOpts
                        
#                        {self.keywordList[0]:{'百度新闻':True, '百度网页':False,'搜狗新闻':False,'搜狗微信':False,'今日头条':False }}
                    Output = '关键词 【 ' + str(keyword) + ' 】 信息成功添加至用户 ' + str(mainUser) + ' 监控列表中！ by ' + user + '。 剩余有效期为： ' + str(self.residDays) + ' 天！'
            except Exception as e:   
                Output = '# 关键词 【 ' + str(keyword) + ' 】 添加失败: ' + str(e) 
                self.write2Log(Output)
                self.SendAlert2Master(Output)
                print(Output)
        return Output  
    def rmKeywordfromList(self, paras, user): # 只有主用户权限
#    \'新闻 rkw ShiRui 一带一路\'： \t 在ShiRui主账号下，移出关键词【一带一路】(关键词数量不能少于1）\n
        # rkw ShiRui 山东如意，即ShiRui名下 山东如意关键词删除
        if len(paras)!=3:
            Output = '# 错误: ' + str(self.label) + ' rmKeywordfromList(), 参数错误！\n' + str(paras) + '\n' 
            Output = Output + '关键词删除：\n \' rkw ShiRui 一带一路\'\n  rkw 表示删除关键词，ShiRui为主用户名，一带一路为关键词'
            print(paras)
        else:
            mainUser = paras[1]
            keyword = paras[2]
            if mainUser != self.getMainUser():
                Output = '# 忽略删除关键词：主账号名不符合！'
                return Output
            if len(self.keywordList) < 2:
                Output = '# 忽略删除关键词：主账号关键词少于2！'
                return Output
            try: # 首先，检查用户是否在列表中
                if keyword in self.keywordList: # 如果存在，删除
                    with self.mu:    ##加锁
                         self.keywordList.remove(keyword)
                         # 如果存在副关键词，移出
                         if keyword in self.subkeywordList: 
                             self.subkeywordList.pop(keyword)
                         if keyword in self.serachRangeOpts: 
                             self.serachRangeOpts.pop(keyword)                             
                         self.residDays.pop(keyword)
                         # 操作NewsList
                         self.NewsList.pop(keyword)
                    Output = '成功将关键词 【 ' + str(keyword) + ' 】 移出用户'+  mainUser + '监控列表！ by ' + user
                    WeChat.SendWeChatMsgToUserList(self.UserList, Output, self.logfile) # 向所有用户通知keywords变化信息
                else:
                    Output = '关键词 【 ' +  str(keyword) + ' 】 不存在于监控列表!'
            except Exception as e:   # 如果不成功，什么也不做，并返回消息
                Output = '# 关键词 【 ' + str(keyword) + ' 】 删除失败: ' + str(e) 
                self.write2Log(Output)
                print(Output)
                self.SendAlert2Master(Output)
        return Output  
    
#-----------------------------获得某个关键词最近新闻列表------------------------------------------------#
    def getNewsofKeyword(self, paras): # 默认不带有副关键词
 #  \'新闻 gn ShiRui 一带一路 100 date\'： \t 发送ShiRui主账号下，【一带一路】 关键词最近100条新闻，并按日期（date)或者作者（author）排序排序\n
        Flag = False
        Output = ''
        if len(paras)!=5:
            Output = '#错误: ' + str(self.label) + ' getNewsofKeyword(), 参数错误！\n 您输入的参数为：' + \
            str(paras) + '\n 应该输入格式为：新闻 gn ShiRui 一带一路 100 date , gn后面参数依次为，主账号，关键词，新闻条数，以及排序方式（date 或者 author)' 
            print(paras)
        else:
            mainUser = paras[1]
            keyword = paras[2]
            numOfNews = paras[3]
            if int(numOfNews) > self.maximumNews2Get:
                numOfNews = self.maximumNews2Get
            fileName = self.getFileName('keyword')
            sortMethod = paras[4]
            if mainUser != self.getMainUser() and mainUser != 'XuKailong' and mainUser != 'ShiRui': # 这两个用户或者主账户均有权限
                Output = '# 忽略删除关键词：主账号名不符合！'
                return Flag, Output
            if keyword in self.keywordList or mainUser == 'XuKailong':  # 不在列表的关键词不能查询
                try: # 获取新闻列表
                    succ, news = self.getNews(keyword, int(numOfNews), sortMethod)
                    if not succ:
                        Flag = False
                        Output = ''
                    else:
                        self.writeNews2File(news, fileName, '## 关键词 ##：【 ' + keyword + ' 】 最近 ' + str(numOfNews) + ' 条新闻搜索结果如下（时间排序）：\n\n', 'w+')
                        Output = fileName
                        Flag = True
                except Exception as e:   # 如果不成功，什么也不做，并返回消息
                    Output = '# 关键词 【 ' + str(keyword) + ' 】 新闻列表获取异常： ' + str(e) 
                    self.write2Log(Output)
                    print(Output)
            else:
                Output = '关键词 【 ' +  str(keyword) + ' 】 不存在于监控列表!'
        return Flag, Output
    def getFieldNews(self, paras):
#         \'新闻 gf ShiRui\'： \t 发送ShiRui主账号下，今日同行动态文件（仅特定人员开放）\n
        Flag = False
        fileName = ''
        Output = ''
        if len(paras)!=2:
            Output = '# 错误: ' + str(self.label) + ' getFieldNews(), 参数错误！\n 您输入的参数为：' + \
            str(paras) + '\n 应该输入格式为：新闻 gf ShiRui, gf后面参数为主账号' 
            print(paras)
        else:
            mainUser = paras[1]
            fileName = self.getFileName('fields_' + mainUser)
# 仅对ShiRui或者XuKailong开放
            if self.getMainUser() != 'ShiRui' and self.getMainUser() != 'XuKailong': # 只有这两个个用户可以获取
                print('主用户为：' + self.getMainUser())
                Output = '# 获取同行新闻失败！'
                return Flag, Output
            with self.mu:
                fistTime = True
                mode = 'w+'
                Output = ''
                for keyword in self.companyInFiled:  # 不在列表的关键词不能查询, 每个关键词的结果都写入fileName
                    print('获取同行：' + keyword)
                    if fistTime:
                        mode = 'w+'
                        fistTime = False
                    else:
                        mode = 'a+'
                    try: # 获取新闻列表
                        succ, temp_Output = self.getCompanyNewsToday(keyword, fileName, mode) # 只要某个公司的获得成功 ，就返回消息
                        if succ:
                            Output = fileName
                            Flag = True
                        else:
                            Output = Output + temp_Output
                    except Exception as e:   # 如果不成功，什么也不做，并返回消息
                        Output = '# 获取同行 【 ' + str(keyword) + ' 】 当日新闻列表异常： ' + str(e) 
                        self.write2Log(Output)
                        print(Output)
                        self.SendAlert2Master(Output)
        if Flag:
            Output = fileName
        return Flag, Output    
    def printFiledCompany(self):
    #    \'新闻 lfc\'： \t 列出ShiRui主账号下，同行公司列表
        Output = ''
        if len(self.companyInFiled) < 1:
            Output = Output + self.mainUser + ': 同行公司列表为空！'
        else:
            with self.mu:
                Output = Output + self.mainUser + ' 监控的同行公司有：\n' 
                for company in self.companyInFiled:
                    # 分别打印昵称，用户名和NickName
                    Output = Output + '【 ' + str(company) + ' 】\n'
        return Output
    
    def addComp2FieldList(self, paras, user): # 在外部只有管理员能进入
        # \'新闻 afc ShiRui 红豆股份\'： \t 在ShiRui主账号下，添加同行公司名【红豆股份】
        if len(paras)!=3:
            Output = '# 错误: ' + str(self.label) + ' addComp2FieldList(), 参数错误！\n' + str(paras) + '\n' 
            Output = Output + '同行公司添加：\n \' afc ShiRui 红豆股份\'\n  akw 表示添加同行公司名，ShiRui为主用户名，红豆股份为添加的公司名'
            print(paras)
        else:
            mainUser = paras[1]
            company = paras[2]
            if mainUser != self.getMainUser():
                print('主用户为：' + self.getMainUser())
                Output = '# 添加同行公司失败！'
                return Output
            try: 
                if company not in self.companyInFiled : # 判断关键词是否存在
                      #如果不存在，添加
                      with self.mu:
                          self.companyInFiled.append(company)
                      Output = '同行公司 【 ' + str(company) + ' 】 成功添加至用户' + str(mainUser) + '监控列表中！ by ' + user + '。'
                else:
                      Output = '# 添加失败： 同行公司 【 ' + str(company) + ' 】 已经存在于监控列表中'
            except Exception as e:   
                Output = '# 同行公司 【 ' + str(company) + ' 】 添加失败: ' + str(e) 
                self.write2Log(Output)
                self.SendAlert2Master(Output)
                print(Output)
        return Output  
    def rmCompfromFieldList(self, paras, user): # 在外部只有管理员能进入
#    \'新闻 rfc ShiRui 红豆股份\'： \t 在ShiRui主账号下，移出同行公司名【红豆股份】
        if len(paras)!=3:
            Output = '# 错误: ' + str(self.label) + ' rmCompfromFieldList(), 参数错误！\n' + str(paras) + '\n' 
            Output = Output + '同行公司删除：\n \' 新闻 rfc ShiRui 红豆股份\'\n  rfc  表示删除关键词，ShiRui为主用户名，红豆股份为同行公司名'
            print(paras)
        else:
            mainUser = paras[1]
            company = paras[2]
            if mainUser !=self.getMainUser():
                print('主用户为：' + self.getMainUser())
                Output = '# 删除同行公司失败！'
                return Output
            if len(self.companyInFiled) < 2:
                Output = '# 忽略删除同行公司：主账号同行公司列表少于2！'
                return Output
            try: # 首先，检查用户是否在列表中
                if company in self.companyInFiled: # 如果存在，删除
                    with self.mu:    ##加锁
                         self.companyInFiled.remove(company)
                    Output = '成功将同行公司 【 ' + str(company) + ' 】 移出用户'+  mainUser + '监控列表！ by ' + user
                else:
                    Output = '同行公司 【 ' +  str(company) + ' 】 不存在于监控列表!'
            except Exception as e:   # 如果不成功，什么也不做，并返回消息
                Output = '# 同行公司 【 ' + str(company) + ' 】 删除失败: ' + str(e) 
                self.write2Log(Output)
                print(Output)
                self.SendAlert2Master(Output)
        return Output  
 
    def getCompanyNewsToday(self, keyword, filename, mode):
        Flag = False
        succ, news = self.getNews( keyword, self.numOfNewsInFieldComp, self.defaultSortMethod)
        Output = ''
        if not succ:
            Flag = False
            Output = '新闻获取异常！'
            return Flag, Output
        else: # 如果成功
        # news 中已经排序
            for item in news: # news 本质上是个list，每个元素为键值对
                body = item[1] # 获得其键值，其下属有'标题',‘date'等
                now = datetime.datetime.now()
                today = '%04d年%02d月%02d日'%(now.year, now.month, now.day)
                if today in body['date']: #如果属于今天，写入该新闻
                    self.writeNews2File([item], filename, '## 今日同行新闻列表 ##：【 ' + keyword + ' 】 搜索结果如下：\n\n', mode)
                    print('【 ' + keyword + '】' + '发现新的新闻！')
                    Flag = True
            if not Flag:
                Output = '没有发现 【 ' + str(keyword) + ' 】新闻！\n'
                
        return Flag, Output
    def setResDays(self, paras, user):  # 在外部只有管理员能进入
    #    \'新闻 srd ShiRui 一带一路 365\'： \t 将ShiRui主账号下，关键词【一带一路】有效期设置为365天\n 
        if len(paras)!= 4:
            Output = '# 错误: ' + str(self.label) + ' setResDays(), 参数错误！\n' + str(paras) + '\n'
            Output = Output + '使用期重设：\n \' srd ShiRui 一带一路 365\'\n  srd 表示重设使用期，ShiRui为主用户名，一带一路为关键词，365 为剩余天数'
            print(paras)
        else:
            mainUser = paras[1]
            keyword = paras[2]
            days = int(paras[3])
            if mainUser != self.getMainUser():
                Output = '# 忽略使用期重设：主账号名不符合！'
                return Output
            try: # 首先，检查用户是否在列表中
                if keyword in self.keywordList: # 如果存在，删除
                    with self.mu:    ##加锁
                         self.residDays[keyword] = int(days)
                    Output = '成功重设主用户 ' + str(self.getMainUser()) + ' 关键词 【 ' + str(keyword) + ' 】 的使用天数为：' + str(days) + '天 by ' + user
                    WeChat.SendWeChatMsgToUserList(self.UserList, Output, self.logfile) # 向所有用户通知keywords变化信息
                else:
                    Output = '关键词 【 ' +  str(keyword) + ' 】 不存在于主用户 ' + str(self.getMainUser()) + '监控列表!'
            except Exception as e:   # 如果不成功，什么也不做，并返回消息
                Output = '主用户 ' + str(self.getMainUser()) + '# 关键词 【 ' + str(keyword) + ' 】 使用天数设置失败: ' + str(e) 
                self.write2Log(Output)
                print(Output)
                self.SendAlert2Master(Output)
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
                    print('开始设置用户 ' + str(self.getMainUser()) +' 关键词有效期：\n')
                    for keyword in self.keywordList: 
                        self.residDays[keyword] = int(self.residDays[keyword]) - 1
                        print(' 关键词 【' + keyword + ' 】：' + str(self.residDays[keyword]) + '天！\n')
                        #判断是否小于15天
                        if  int(self.residDays[keyword]) < 15:
                            WeChat.SendWeChatMsgToUserList(self.UserList, self.label + '您的监控关键词 【' + keyword + ' 】 还有' + str(self.residDays[keyword] ) + ' 就要过期了，请及时联系管理员延期！\n' + \
                        '微信： MoBeiHuyang；手机：18910241406', self.logfile) # 向所有用户通知keywords变化信息
                    self.ResSetFlag = True
                else:
                    print('已经设置用户 ' + str(self.getMainUser()) + '新闻监控有效期！')
        except Exception as e:   # 如果不成功，给管理员发消息
            Output = '# 使用时间设置失败: ' + str(e) 
            self.write2Log(Output)
            print(Output)
            self.SendAlert2Master(Output)
    
    def listUserParas(self, paras, user):  # 只有管理员能进入
# \'新闻 lup ShiRui\'： \t 列出ShiRui主账号下，对应的几个扫描参数关键词，第一个为该主用户 numOfNewsInEachScan, 第二个为该主用户 getFiledNews中的扫描新闻条数，第三个为监控新闻排序方式
        if len(paras)!=2:
            Output = '# 错误: ' + str(self.label) + ' listUserParas(), 参数错误！\n' + str(paras) + '\n' 
            Output = Output + '用户参数打印：\n \' lup ShiRui\'\n  lup 表示列出用户参数，ShiRui为主用户名'
            print(paras)
        else:
            mainUser = paras[1]
            if mainUser != self.getMainUser(): 
                print('主用户为：' + self.getMainUser())
                Output = '# 打印用户 ' + mainUser + ' 参数失败！'
                return Output
            try: 
                Output = '用户 ' + mainUser + '系统参数如下：\n'
                Output = Output + ' numOfNewsInEachScan : ' + str(self.numOfNewsInEachScan) + ' 条\n'
                Output = Output + ' numOfNewsInFieldComp : ' + str(self.numOfNewsInFieldComp) + ' 条\n'
                Output = Output + ' souGou_RestTime : ' + str(self.souGou_RestTime) + ' 分钟\n'
                Output = Output + ' defaultSortMethod : ' + str(self.defaultSortMethod) + ' \n'
            except Exception as e:   
                Output = '# 打印用户 ' + mainUser + ' 参数失败！' + str(e) 
                self.write2Log(Output)
                self.SendAlert2Master(Output)
                print(Output)
        return Output  
    def setUserParas(self, paras, user): # 只有管理员能进入
#   \'新闻 sup ShiRui 60 60 180 date\'： \t 列出ShiRui主账号下，对应的几个扫描参数关键词，第一个为该主用户 numOfNewsInEachScan, 第二个为该主用户 getFiledNews中的扫描新闻条数，,第三个为搜狗新闻平台遇到爬虫时休息时间，分钟，第四个为监控新闻排序方式
        if len(paras)!=6:
            Output = '# 错误: ' + str(self.label) + ' setUserParas(), 参数错误！\n' + str(paras) + '\n' 
            Output = Output + '用户参数设置：\n \' sup ShiRui 60 60 180 date\'\n  sup 表示设置用户参数，ShiRui为主用户名，第一个60表示numOfNewsInEachScan,第二个为该主用户 getFiledNews中的扫描新闻条数，,第三个为搜狗新闻平台遇到爬虫时休息时间，分钟，第四个为监控新闻排序方式'
            print(paras)
        else:
            
            mainUser = paras[1]
            nOfNewsInEachScan = paras[2]
            nOfNewsInFieldComp = paras[3]
            setSouGouRestTime = paras[4]
            SortMethod = paras[5]
            if mainUser != self.getMainUser():
                print('主用户为：' + self.getMainUser())
                Output = '# 用户 ' + str(mainUser) + ' 系统参数设置失败！'
                return Output
            try: 
                self.numOfNewsInEachScan = int(nOfNewsInEachScan)
                self.numOfNewsInFieldComp = int(nOfNewsInFieldComp)
                if self.souGou_RestTime == int(setSouGouRestTime):
                    print('\n\n### 重置搜狗搜索平台阈值（%s）！### \n\n' % self.mainUser)
                    self.souGou_Thresh = 0
                    self.souGou_WeChat = 0
                else:
                    self.souGou_RestTime = int(setSouGouRestTime)
                if SortMethod == 'date' or SortMethod == 'author' or SortMethod == 'other':
                    self.defaultSortMethod = SortMethod
                    Output = '# 用户 ' + str(mainUser) + ' 系统参数设置成功！'
                else:
                    self.defaultSortMethod = 'date'
                    Output = '# 用户 ' + str(mainUser) + ' 新闻参数排序方法设置错误，默认设置为 date !'
            except Exception as e:   
                Output = '# 用户 【 ' + str(mainUser) + ' 】 系统参数设置异常: ' + str(e) 
                self.write2Log(Output)
                self.SendAlert2Master(Output)
                print(Output)
        return Output 
   
  