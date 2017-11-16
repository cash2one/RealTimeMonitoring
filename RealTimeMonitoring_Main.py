# -*- coding: utf-8 -*-
"""
Created on Fri May 19 09:41:08 2017

@author: MoBeiHuYang
"""
import itchat
from itchat.content import *
import StockMonitoring as sm
import RealTimeScrapper as ns
from WeChatFuncs import *
import MasterFuncs as MasFun
import threading
import random
import time, os
from threading import Timer
timer_t = None
mu =  threading.RLock()
global __Author__
global Master
global WeChatLogged
WeChatLogged = False
__Author__ = 'FlameMan'
Master = {'Master':{'UserName':'', 'NickName':'FlameMan'}}
UserList = {'XuKailong':{'UserName':'', 'NickName':'FlameMan', 'Stock':None, 'News':None},\
            }   #初始用户列表

global f, logfile, initMsg, label
logfile = log_dir + '监控主程序.log'
label = ' # 监控主程序 # '
f = open(logfile,'a+')

initMsg = '监控软件 by ' + str(__Author__) + ' 启动！\n'
pricklefileName = pickle_dir + '监控数据_热启动文件.pickle'
Debug = MasFun.Debug
# 代码中异常处理，分为三种
# 1. 非常严重错误，如微信登陆错误，键盘人为打断，属于严重错误。这种需要停止运行程序，并通知管理员
# 2. 一般严重错误，如写入log失败，这样只需要通知管理员，继续运行赓续
# 3. 普通错误，如新闻列表获取失败，信息没有查到，只需要返回错误给用户，并通知管理员
def SendOnlineMsg(entertime):
    global Master, logfile, timer_t
    try:
        reply = '现在时间是： ' + datetime.datetime.now().strftime('%y-%m-%d %H:%M:%S')
        SendWeChatMsgToUserList(Master, reply + '！\n瓦力在线，继续努力工作中！', logfile)
        timer_t = Timer(3600*4, SendOnlineMsg, ( time.time(), )) # 间隔时间,4 小时发一次
        timer_t.start()  
    except Exception as e:
        raise Exception('# 异常：向管理员发送值班信息异常：' + str(e))   
def write2Log(msg):
    global f,logfile, WeChatLogged, Master
    try:
        if f.closed:
            f = open(logfile,'a+')
        f.write(msg + '\n')
        f.close()
    except Exception as e:
        errmsg = '# 监控程序日志写入异常：write to log error!' + str(e)
        print(errmsg)
        if WeChatLogged:
            SendWeChatTextMsg(errmsg, Master['Master']['UserName'], Master['Master']['NickName'],logfile)
def __Init__():
    """
    Created on Fri May 19 09:41:08 2017
    @author: MoBeiHuYang
    1. 微信登陆
    2. 初始化管理员账号
    3. 用户列表登录信息的初始化
    4. 用户列表监控类的初始化
    """
    global Master, logfile, UserList, WeChatLogged, pricklefileName, Debug
    print(initMsg)
    write2Log(initMsg)
    # 登陆微信
    if not StartWeChat(): # 严重错误，需要向上抛出异常
       raise Exception('# 错误: 微信登陆异常！')
        # 初始化管理员账号
    try:
        InitWeChatUsers(Master, logfile) # 初始化管理员账号
        WeChatLogged = True
    except Exception as e: #严重错误
        errmsg = '# 管理员微信账号初始化异常: ' + str(e) 
        WeChatExit()
        write2Log(errmsg)
        print(errmsg)
        raise Exception(errmsg)
    hotReload = False
    if not Debug:
       hotReload, data = MasFun.getDatafromPickle(pricklefileName)
       try:
           WeChatgetDatafromPickle()
       except Exception:
           pass
    if hotReload:
        UserList = data
    else:
        # 初始化用户微信账号
        try:
            InitWeChatUsers(UserList, logfile) # 初始化用户账号
        except Exception as e:  # 严重错误
            errmsg = '# 主用户列表微信初始化异常: ' + str(e) 
            WeChatExit()
            write2Log(errmsg)
            print(errmsg)
            raise Exception(errmsg) 
    try: # 初始化用户的监控类
        with mu:
            for user in UserList:  
                print(user)
                if (not hotReload) or (hotReload and UserList[user]['Stock']): # 如果冷启动，或者热启动时，原有文件中含有Stock
                    UserList[user]['Stock'] = sm.TStockMonitor(user, UserList[user]['NickName'], hotReload)     # 创建时，微信账号已经初始化完毕
                if (not hotReload) or (hotReload and UserList[user]['News']): # 如果冷启动，或者热启动时，原有文件中含有News
                    UserList[user]['News'] = ns.TBaiDuNewsScapper(user, UserList[user]['NickName'], hotReload)
    except Exception as e:  # 初始化时，属于严重错误，向上抛出异常
        WeChatExit() # 退出微信
        raise Exception(str(e))
def Run():
    """
    1. 依次运行用户的两个监控程序
    2. 如果监控程序出错，则处理异常，且向管理员发信息
    
    """
    global Master, logfile, label
    try:
#        runAllNewsWatch(time.time())
#        runAllStockWatch(time.time())
            
        print('\n# 运行一次监测程序 #')
        tempStockObject = None
        for user in UserList:
            print('\n#------------------用户： ' + str(user) + ' ---------------------------#\n')
            if UserList[user]['Stock']:
                UserList[user]['Stock'].Run()
                tempStockObject = UserList[user]['Stock']
                
            if UserList[user]['News']:
                UserList[user]['News'].Run()
        if tempStockObject and tempStockObject.OnDuty():
            time.sleep(MasFun.sleeptime_S)  #暂停一段时间，开市
        else:
            time.sleep(MasFun.sleeptime_L)  #暂停一段时间,休市
    except KeyboardInterrupt: # 正常键盘退出
        errmsg = '监控程序异常，提醒管理员：\n 键盘中断，微信退出!'
        raise KeyboardInterrupt(errmsg)
    except Exception as e: # 一般错误, 继续运行
        errmsg = label + '运行异常： ' + str(e)
        print(errmsg)
        write2Log(errmsg)
 #       if WeChatLogged:
 #           SendWeChatTextMsg(errmsg, Master['Master']['UserName'], Master['Master']['NickName'],logfile)
        return
    
def runAllNewsWatch(entertime):
    global label, timer_news
    try:
        with mu:
            for user in UserList:
                print('\n#------------------用户： ' + str(user) + ' ---------------------------#\n')
                if UserList[user]['News']:
                    UserList[user]['News'].Run()
        timer_news = Timer(MasFun.sleeptime_L, runAllNewsWatch, ( time.time(), )) 
        timer_news.start()            
    except KeyboardInterrupt: # 正常键盘退出
        errmsg = '监控程序异常，提醒管理员：\n 键盘中断，微信退出!'
        raise KeyboardInterrupt(errmsg)
    except Exception as e: # 一般错误, 继续运行
        errmsg = label + '运行异常： ' + str(e)
        print(errmsg)
        write2Log(errmsg)
def runAllStockWatch(entertime):
    global label, timer_stock
    try:
        with mu:
            tempStockObject = None
            for user in UserList:
                print('\n#------------------用户： ' + str(user) + ' ---------------------------#\n')
                if UserList[user]['Stock']:
                    UserList[user]['Stock'].Run()
                    tempStockObject = UserList[user]['Stock']
        if tempStockObject and tempStockObject.OnDuty():
            timer_stock = Timer(MasFun.sleeptime_S, runAllStockWatch, ( time.time(), )) 
            timer_stock.start()             
        else:
            timer_stock = Timer(MasFun.sleeptime_L, runAllStockWatch, ( time.time(), )) 
            timer_stock.start() 
    except KeyboardInterrupt: # 正常键盘退出
        errmsg = '监控程序异常，提醒管理员：\n 键盘中断，微信退出!'
        raise KeyboardInterrupt(errmsg)
    except Exception as e: # 一般错误, 继续运行
        errmsg = label + '运行异常： ' + str(e)
        print(errmsg)
        write2Log(errmsg)   
    
def Bye():
    """
    1. 每个用户两个监控程序的退出
    """
    global mu, UserList, pricklefileName, Debug
    try:
        timer_t.cancel()
#        timer_news.cancel()
#        timer_stock.cancel()
        with mu:
            # 写入主账户的用户名和昵称
            if not Debug:
                MasFun.pickleDump2file(UserList, pricklefileName)
                WeChatpickleDump2file()
            # 先将所有用户信息写入文件
            print('\n正在写入用户信息：\n')
            fileName  = news_dir + 'UserInfo' + str(time.strftime('_%Y_%m_%d_%H_%M_%S', time.localtime(time.time()))) + '.txt'
            f = open(fileName,'w+')
            f.write(MasFun.listAllUsers(UserList) + '\n')
            f.close()
            print('\n用户信息写入完成！\n')
            for user in UserList:
                if UserList[user]['Stock']:
                    UserList[user]['Stock'].Bye(Debug)
                    UserList[user]['Stock'] = None
                if UserList[user]['News']:
                    UserList[user]['News'].Bye(Debug)
                    UserList[user]['News'] = None
    except Exception as e:
        errmsg = label + ' 退出异常：' + str(e)
        write2Log(errmsg)
        if WeChatLogged:
            SendWeChatTextMsg(errmsg, Master['Master']['UserName'], Master['Master']['NickName'],logfile)
#------------------------------------------------微信交互内容-------------------------------------------------------# 
@itchat.msg_register([TEXT, MAP, CARD, NOTE, SHARING])  # 这个函数干嘛的
def text_reply(msg):
    global UserList, logfile, Master, mu
    cmd = str(msg['Text']).lstrip().rstrip().split(' ')
    stockUser = False
    newsUser = False
    print('收到来自 ' + str(msg['User']['NickName']) + ' 的消息：\n' + str(msg['Text']))
    write2Log('收到来自 ' + str(msg['User']['NickName']) + ' 的消息：\n' + str(msg['Text']))
    # 是否是管理员，以及是不是管理员命令
    try:
        if msg['FromUserName'] == Master['Master']['UserName']:
            # 判断是否是管理员操作
            masterWork, sndmsg  = MasFun.isMasterWork(UserList, msg) # 主要处理，如下命令lall, lShiRui, amu, rmu, os, cs, on, cn
            if masterWork: # 向管理员汇报，任务成功完成，并返回
                SendWeChatTextMsg(sndmsg, msg['FromUserName'], msg['User']['NickName'], logfile)
                return
    except Exception as e:
        errmsg = '管理员消息处理异常： ' + str(e)
        print(errmsg)
        if WeChatLogged:
            SendWeChatTextMsg(errmsg, Master['Master']['UserName'], Master['Master']['NickName'],logfile)
    try:
    # 如果不是管理员操作，可能是用户操作，也能是管理员操作子类，或者普通聊天（因为各主账号下的类是独立的，且每个用户在所在的各主账号下只能操作一次，所以用户或者管理员不会有重复操作的情况）
        keyNamelist = MasFun.getKeyNameListOfUser(UserList, msg['FromUserName'])  # 获得用户所在主账号列表，是个字符串列表
        if len(keyNamelist) > 0:
        # 如果在用户列表中，进行数据处理
            msgsent = False
            with mu:
                for mainUser in keyNamelist: # 针对该用户所在的每个主账号分别处理
                    # 针对每个主账号分别处理：
                    StockMonitor = UserList[mainUser]['Stock'] # 若存在，则为实际stock class，若不存在，则为None
                    NewsScrapper = UserList[mainUser]['News'] 
                     # 强制限制，交互内容只能看一个，以股票 或者 新闻开头，其余的均去调戏那边
                    if cmd[0] == 'h':
                        SendWeChatTextMsg(MasFun.Help(), msg['FromUserName'], msg['User']['NickName'], logfile)
                        return
                    if StockMonitor:
                        if cmd[0] == '股票':  
                            stockUser= True
                    if NewsScrapper:
                        if cmd[0] == '新闻':
                            newsUser = True
                    if stockUser:
                        StockMonitor.Interaction(msg) # 交互处理信息，并回复信息
                    elif newsUser:
                        NewsScrapper.Interaction(msg) # 交互处理信息，并回复信息   
                    else: # 调戏
                        if not msgsent:
                            sndmsg = getRespons(msg['Text'], 90)
                            SendWeChatTextMsg(sndmsg, msg['FromUserName'], msg['User']['NickName'],logfile)
                            # 如果是用户，但因没有输入关键字，导致无法得到消息，这时可以设置提醒
                            if random.randint(0,20) == 10:
                                sndmsg = '\n 如果你实在不知道要输入什么的话，输入 \'h\' '
                                if StockMonitor:
                                    sndmsg = sndmsg + '或 \'股票 h\' '
                                if NewsScrapper:
                                    sndmsg = sndmsg + '或 \'新闻 h\' '
                                    sndmsg = sndmsg + '看看帮助文档吧！'
                                SendWeChatTextMsg(sndmsg, msg['FromUserName'], msg['User']['NickName'], logfile)
                        msgsent = True
        else:
        # 如果非用户，进行处理
            return
#            sndmsg = ' 这是本人小号，不常登陆。有事请联系微信：MoBeiHuYang，或者电话：18910241406！'
#            SendWeChatTextMsg(sndmsg, msg['FromUserName'], msg['User']['NickName'],logfile)
#            sndmsg = getRespons(msg['Text'], 90)
#            SendWeChatTextMsg(sndmsg, msg['FromUserName'], msg['User']['NickName'],logfile)
    except Exception as e:
        errmsg = '用户 ' + str(msg['User']['NickName']) + ' 消息处理异常： ' + str(e)
        print(errmsg)
        if WeChatLogged:
            SendWeChatTextMsg(errmsg, Master['Master']['UserName'], Master['Master']['NickName'],logfile)
        pass
@itchat.msg_register([PICTURE, RECORDING, ATTACHMENT, VIDEO])
def download_files(msg):
    msg['Text'](emotion_dir + msg['FileName'])
    sndmsg = getRespons('no', 20) # 20的概率是文本
    SendWeChatTextMsg(sndmsg, msg['FromUserName'], msg['User']['NickName'],'非用户聊天日志.log')
    return
#    return '@%s@%s' % ({'Picture': 'img', 'Video': 'vid'}.get(msg['Type'], 'fil'), msg['FileName'])

@itchat.msg_register(FRIENDS)
def add_friend(msg):
    itchat.add_friend(**msg['Text']) # 该操作会自动将新好友的消息录入，不需要重载通讯录
    SendWeChatTextMsg('Nice to meet you!', msg['RecommendInfo']['UserName'], msg['RecommendInfo']['UserName'])
    sndmsg = ' 这是本人小号，不常登陆。有事请联系微信：MoBeiHuYang，或者电话：18910241406！'
    SendWeChatTextMsg(sndmsg, msg['FromUserName'], msg['User']['NickName'],'非用户聊天日志.log')
    sndmsg = getRespons('no', 90)
    SendWeChatTextMsg(sndmsg, msg['FromUserName'], msg['User']['NickName'],'非用户聊天日志.log')

@itchat.msg_register(TEXT, isGroupChat=True)
def text_reply(msg):
    if msg['isAt']:
        SendWeChatTextMsg(u'@%s\u2017I received: %s' % (msg['ActualNickName'], msg['Content']),  msg['FromUserName'], msg['User']['NickName'])
        sndmsg = ' 这是本人小号，不常登陆。有事请联系微信：MoBeiHuYang，或者电话：18910241406！'
        SendWeChatTextMsg(sndmsg, msg['FromUserName'], msg['User']['NickName'],'非用户聊天日志.log')
        sndmsg = getRespons('no', 90)
        SendWeChatTextMsg(sndmsg, msg['FromUserName'], msg['User']['NickName'],'非用户聊天日志.log')
#------------------------------------------------微信交互内容-------------------------------------------------------#     
if __name__=="__main__":
    try:
        __Init__()
    except Exception as e:  # 处理异常
        errmsg = '# 这个监控程序初始化异常！' + str(e)
        print(errmsg)
        write2Log(errmsg)
        os._exit()
    # 开启微信待机运行状态
    try: # 如果微信退出，则打印异常，并向管理员发消息
        WeChatOnDuty()
    except Exception as e:
        print(e)
        write2Log(e)
        SendWeChatMsgToUserList(Master, str(label) + ': ' + str(e), logfile)
        
    # 待机运行 
    try:
        Timer(0, SendOnlineMsg, ( time.time(), )).start()  
        while True:
            Run()
    except KeyboardInterrupt as e: # 正常键盘退出
        errmsg = str(e)
        print(errmsg)
        write2Log(errmsg)
        Bye()
#        SendWeChatMsgToUserList(Master, str(label) + ': ' + str(errmsg), logfile)
        WeChatExit()
