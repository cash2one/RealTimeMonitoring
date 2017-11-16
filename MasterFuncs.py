# -*- coding: utf-8 -*-
"""
Created on Sat May 20 17:57:59 2017

@author: MoBeiHuYang
"""
import threading  # 用于多线程工作
import WeChatFuncs as WeChat
import StockMonitoring as sm
import RealTimeScrapper as ns
import pickle

sleeptime_L = 15*60
sleeptime_S = 15*60
mu =  threading.RLock()
logfile = WeChat.log_dir + '监控主程序.log'
label = ' # 监控主程序 # '
f = open(logfile,'a+')
Master = {'Master':{'UserName':'', 'NickName':'FlameMan'}}
Debug = False
#--------------------------------操作用户列表-------------------------------------------#   
def SendAlert2Master( errmsg):
    global logfile, label, Master
    errmsg2 = '程序异常，提醒管理员：\n' + str(errmsg)
    write2Log(str(label) + str(errmsg2))
    WeChat.SendWeChatMsgToUserList(Master, errmsg2, logfile)
    print(str(label) + str(errmsg2))
def write2Log(msg):
    global f,logfile
    try:
        if f.closed:
            f = open(logfile,'a+')
        f.write(msg + '\n')
        f.close()
    except Exception as e:
        raise Exception('# 异常：监控程序：write to log error!' + str(e)) 
def getKeyNameListOfUser(UserList, userName):
    # 发来消息的有以下几种可能
    # 1. 是用户，仅存在于主账号列表中，即main函数的UserList中，最好办
    # 2. 是用户，不是主账号，但是副账号。仅存在于某个主账号列表中，需要分别在Stock和News的附账号中进行查找，这样就需要遍历所有主账号下的副账号，并得到其对应的主账号
    # 3. 是用户，不在主账号中，但在一个或多个子账号中
    # 4. 是用户，在一个主账号中，但也存在于一个或多个子账号中
    # 本函数输入参数UserList为main file中所有的主账号，userName为发来消息的用户账号
    # 本函数返回一个list，里边列出该用户所在的主账号keyName列表，如果list长度为0，表明该用户不在账户列表中
    # 本函数的策略是，遍历所有的主副账号，每次探测到，则向该用户添加对应的主账号信息，但主账号中不能重复
    try:
        keyNameList = []
        with mu:
            for user in UserList: # 先遍历所有主账号用户， user是callname
                if userName == UserList[user]['UserName']:  # 之间查看主账号
                    addElement2List(keyNameList, user)
                if UserList[user]['Stock']: # 如果定义了stock，则在stock用户列表中寻找
                    if UserList[user]['Stock'].isUserInUserList(userName): # 找到
                         addElement2List(keyNameList, user)  # 添加对应主账号的keyName
                if UserList[user]['News']: # 如果定义了news，则在news用户列表中寻找
                    if UserList[user]['News'].isUserInUserList(userName): # 找到
                         addElement2List(keyNameList, user)  # 添加对应主账号的keyName
    except Exception as e: # 一般错误，向上抛出异常
        raise Exception('# 用户所在主账号列表获取异常：' + str(e))
    return keyNameList
def addElement2List(List, element):
    if element not in List:  # 如果element不存在于List，则进行添加
        List.append(element)
def isUserinList( UserList, userName):
    findUser = False
    with mu:
        for user in UserList:
            if userName == UserList[user]['UserName']:
                findUser = True 
    return findUser    
def addUser2UserList(UserList, paras):  #每增加一个，需要申请其状态
#    \'amu ShiRui 落雪 0 1\'： \t 添加ShiRui主账号，昵称为落雪，0（1） 表示不监控股票，1（0）表示监控新闻，至少开通一个功能\n 
#    UserList 格式 {'XuKailong':{'UserName':'', 'NickName':'FlameMan', 'Stock':None, 'News':None}}   #初始用户列表
    global label, logfile
    if len(paras)!= 5:
        Output = '# 错误: ' + str(label) + ' modifyUserList(), 参数错误！\n' 
        Output = Output + '主用户添加方法：\n \' amu ShiRui 落雪 0 1 \'\n  amu 表示命令种类，添加主用户；ShiRui表示用户callName， 落雪是用户昵称，0（1） 表示不监控股票，1（0）表示监控新闻'
        print(paras)
    else:
        callName = paras[1]
        nickName = paras[2]
        stock = paras[3]
        news = paras[4]
        if (int(stock) not in range(0,2)) or (int(news) not in range(0,2) or (int(stock) + int(news) not in range (1,3))):
            Output = '# 错误: ' + str(label) + ' modifyUserList(), 参数错误！\n' 
            Output = Output + '主用户添加方法：\n \' amu ShiRui 落雪 0 1 \'\n  amu 表示命令种类，添加主用户；ShiRui表示用户callName， 落雪是用户昵称，0（1） 表示不监控股票，1（0）表示监控新闻'
            return Output
        try: # 首先，获得用户的账号，如果获得成功
            userName  =  WeChat.findWeChatUser(nickName, logfile) # call name
            if not isUserinList(UserList, userName) : # 判断用户是否已经存在, 如果不存在，添加
                  mystock = None
                  mynews = None
                  if int(stock) == 1:
                      mystock = sm.TStockMonitor(callName, nickName, True)     # 创建时，微信账号已经初始化完毕   
                  if int(news) == 1:
                      mynews = ns.TBaiDuNewsScapper(callName, nickName, True)
                  #如果不存在，添加新用户
                  print(listAllUsers(UserList))
                  with mu:  # 添加用户
                      UserList.setdefault(callName, {'UserName':userName, 'NickName':nickName, 'Stock':mystock, 'News':mynews})
                  print(listAllUsers(UserList))
                  # 添加新用户后，
                  Output = '用户 ' + str(callName) + ' 成功添加在主用户列表中！'
            else:
                  Output = '# 添加失败： 主用户 ' + str(callName) + ' 已经存在于主用户列表中'
        except Exception as e:   # 如果账号不成功，什么也不做，并返回消息
            Output = '添加主用户信息异常： ' + str(nickName) + ': ' + str(e) 
            write2Log(Output)
            SendAlert2Master(Output)
            print(Output)
    return Output  
def rmUserFromUserList(UserList, paras):
#    \'rmu ShiRui\'： \t 删除ShiRui主账号\n 
#    UserList 格式 {'XuKailong':{'UserName':'', 'NickName':'FlameMan', 'Stock':None, 'News':None}}   #初始用户列表
    global label, mu,Debug
    if len(paras)!=2:
        Output = '# 错误: ' + str(label) + ' rmUserFromUserList(), 参数错误！\n'
        Output = Output + '主用户移出：\n \' rmu ShiRui\'\n  rmu 表示命令种类，移出主用户；ShiRui表示用户callName'
        print(paras)
    else:
        callName = paras[1]
        try: # 首先，检查用户是否在列表中
            with mu:
                if callName in UserList.keys(): # 如果用户存在，删除
                    if len(UserList) > 1:
                        if UserList[callName]['Stock']:
                            UserList[callName]['Stock'].Bye(Debug)
                            WeChat.SendWeChatMsgToUserList(UserList[callName]['Stock'].UserList, label + ': 主用户< ' + callName + ' >移出监控列表', UserList[callName]['Stock'].logfile) # 向所有用户通知上线信息
                        if UserList[callName]['News']:
                            UserList[callName]['News'].Bye(Debug)
                            WeChat.SendWeChatMsgToUserList(UserList[callName]['News'].UserList, label + ': 主用户< ' + callName + ' >移出监控列表', UserList[callName]['News'].logfile) # 向所有用户通知上线信息
                        UserList.pop(callName)
                        Output = '成功将主用户' + str(callName) + '主移出用户列表！'
                    else:
                        Output = '主用户移出错误：主用户列表不能为空！'
                else:
                    Output = '主用户' +  str(callName) + '不存在于主用户列表!'
        except Exception as e:   # 如果账号不成功，什么也不做，并返回消息
            Output = '# 主用户移出异常: ' + str(e) 
            write2Log(Output)
            print(Output)
            SendAlert2Master(Output)
    return Output       
def Help():
    Output = ''' 这是这款监控工具的说明书：
    这款工具旨在实现信息的实时监控，并通过微信向用户及时发送预警信息。在监控过程中，允许用户进行交互操作，如果用户输入参数错误，则进行智能聊天。\n\n
    目前，这款工具实现了新闻词条监控和股票价格监控，每个用户可以开通部分或者全部监控功能。管理员的操作命令说明如下：\n
    \n#------------------- 新闻监控命令----------------------------#\n
    新闻监控工具旨在实现实时关键词在百度新闻的舆论信息，按照时间排序。当监控关键词有新的新闻出现时，向用户发送预警信息。如果输入参数错误，则智能聊天。\n
    \'新闻 h\'：   \t获得这款工具的帮助文档。\n
    \'新闻 lu\'：  \t列出当前用户所在主用户下的用户列表。\n
    \'新闻 lkw\'： \t列出当前用户所在主用户下的监控关键词列表。\n
    \'新闻 gn ShiRui 一带一路 100 date\'： \t 发送ShiRui主账号下，【一带一路】 关键词最近100条新闻，并按日期（date)或者作者（author）排序排序\n
    \'新闻 gf ShiRui\'： \t 发送ShiRui主账号下，今日同行动态文件（仅特定人员开放）\n
    \'新闻 lfc ShiRui\'： \t 列出ShiRui主账号下，关注的同行列表（仅特定人员开放）\n
    #--------------------股票监控命令----------------------------#\n
    股票监控工具旨在无需人为盯盘的情况下，当股票价格满足一定条件时，通过微信的方式向用户发送预警信息。当股票价格超出设置的上下限区间，或者低于五日均价，均会向用户发送预警信息。如果输入参数错误，则智能聊天。\n
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
    return Output
def HelpMaster():
    Output = ''' 这是这款监控工具的说明书(管理员）：
    这款工具旨在实现信息的实时监控，并通过微信向用户及时发送预警信息。在监控过程中，允许用户进行交互操作，如果用户输入参数错误，则进行智能聊天。\n
    目前，这款工具实现了新闻词条监控和股票价格监控，每个用户可以开通部分或者全部监控功能。管理员的操作命令说明如下：
    #-------------------管理员管理命令--------------------------#
    \'h\'： \t 打印本帮助文档\n 
    \'lall\'： \t 列出所有主用户，及其附属子用户信息（用户名，关键词，使用期）
    \'l ShiRui\'： \t 列出主用户ShiRui及其附属子用户信息（用户名，关键词，使用期） 
    \'amu ShiRui 落雪 0 1\'： \t 添加ShiRui主账号，昵称为落雪，0（1） 表示不监控股票，1（0）表示监控新闻，至少开通一个功能 
    \'rmu ShiRui\'： \t 删除ShiRui主账号
    \'os ShiRui\'： \t 开启ShiRui主账号下股票功能
    \'cs ShiRui\'： \t 关闭ShiRui主账号下股票功能（股票和新闻至少开一个）
    \'on ShiRui\'： \t 开启ShiRui主账号下新闻功能
    \'cn ShiRui\'： \t 关闭ShiRui主账号下股票功能（股票和新闻至少开一个）
    \'setslt 900 60\'： \t 设置休市时休眠时间为900s，开市时休眠间隔为60s    
    \'getslt\'： \t 显示扫描间隔时间    
    \'snotice all 这是管理员通知！\'： \t 向所有主账号下所有用户发送消息'这是管理员通知！'
    \'snotice ShiRui 这是管理员通知！\'： \t 向ShiRui主账号下用户发送消息'这是管理员通知！'   
    \'lresp\'： \t 返回所有库中语句'    
    \'rresp 这是个测试！\'： \t 从语句库中查找并删除语句'这是个测试！''    
    \n#------------------- 新闻监控命令----------------------------#\n
    新闻监控工具旨在实现实时关键词在百度新闻的舆论信息，按照时间排序。当监控关键词有新的新闻出现时，向用户发送预警信息。如果输入参数错误，则智能聊天。
    \'新闻 h\'：   \t获得这款工具的帮助文档。
    \'新闻 lu\'：  \t列出当前用户所在主用户下的用户列表。
    \'新闻 lkw\'： \t列出当前用户所在主用户下的监控关键词列表。
    \'新闻 gn ShiRui 一带一路 100 date\'： \t 发送ShiRui主账号下，【一带一路】 关键词最近100条新闻，并按日期（date)或者作者（author）排序排序
    \'新闻 gf ShiRui\'： \t 发送ShiRui主账号下，今日同行动态文件（仅特定人员开放）
    ## 以下操作仅限于管理员账号 ##
    \'新闻 au ShiRui XuKailong FlameMan\'： \t 在ShiRui主账号下，添加子账号,callName为XuKailong，昵称为FlameMan。子账户不能超过上限 5 个 
    \'新闻 ru ShiRui XuKailong\'： \t 在ShiRui主账号下，删除callName为XuKailong的子账号，子账号数量最少为1个   
    \'新闻 akw ShiRui 一带一路[OneBelt+OneRoad](10111) 365\'： \t 在ShiRui主账号下，添加关键词【一带一路】，副关键词为OneBelt和OneRoad，中间不能有空格，其有效期设置为365天,10111分别表示百度新闻，百度网页，搜狗新闻，搜狗微信，今日头条是否开启
    \'新闻 rkw ShiRui 一带一路\'： \t 在ShiRui主账号下，移出关键词【一带一路】（关键词数量不能少于1）
    \'新闻 afc ShiRui 红豆股份\'： \t 在ShiRui主账号下，添加同行公司名【红豆股份】
    \'新闻 rfc ShiRui 红豆股份\'： \t 在ShiRui主账号下，移出同行公司名【红豆股份】
    \'新闻 lfc\'： \t 列出用户所有主账号下监控的同行公司列表
    \'新闻 srd ShiRui 一带一路 365\'： \t 将ShiRui主账号下，关键词【一带一路】有效期设置为365天
    \'新闻 lup ShiRui\'： \t 列出ShiRui主账号下，对应的几个扫描参数关键词，第一个为该主用户 numOfNewsInEachScan, 第二个为该主用户 getFiledNews中的扫描新闻条数，第三个为监控新闻排序方式
    \'新闻 sup ShiRui 60 60 180 date\'： \t 列出ShiRui主账号下，对应的几个扫描参数关键词，第一个为该主用户 numOfNewsInEachScan, 第二个为该主用户 getFiledNews中的扫描新闻条数，第三个为搜狗新闻平台遇到反爬虫系统时，暂停时间，分钟，第四个为监控新闻排序方式
    #--------------------股票监控命令----------------------------#
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
def listAllUsers(UserList):
#    \'lall\'： \t 列出所有主用户，及其附属子用户信息（用户名，关键词，使用期）\n 
#    UserList 格式 {'XuKailong':{'UserName':'', 'NickName':'FlameMan', 'Stock':None, 'News':None}}   #初始用户列表
    global mu    
    Output = ''
    with mu:
        try: 
            for user in UserList:
                Output  = Output + getUserInfo(UserList, user)    
        except Exception as e:   # 如果账号不成功，什么也不做，并返回消息
            Output = '# 用户信息获取异常: ' + str(e) 
            write2Log(Output)
            print(Output)
            SendAlert2Master(Output)
    return Output  
        
def listUser(UserList, paras):
# \'l ShiRui\'： \t 列出主用户ShiRui及其附属子用户信息（用户名，关键词，使用期）\n 
#    UserList 格式 {'XuKailong':{'UserName':'', 'NickName':'FlameMan', 'Stock':None, 'News':None}}   #初始用户列表
    # 打印用户主列表，（用户名，关键词，使用期）
    if len(paras)!=2:
        Output = '#Error: ' + str(label) + ' listUser(), 参数错误！' + str(paras) + '\n'
        Output = Output + '列出用户信息：\n \' rmu ShiRui\'\n  rmu 表示命令种类，移出主用户；ShiRui表示用户callName'
        print(paras)
    else:
        callName = paras[1]
        try: # 首先，检查用户是否在列表中
            Output =  getUserInfo(UserList, callName)    
        except Exception as e:   # 如果账号不成功，什么也不做，并返回消息
            Output = '# 用户信息获取异常: ' + str(e) 
            write2Log(Output)
            print(Output)
            SendAlert2Master(Output)
    return Output  
def getUserInfo(UserList, callName):
#    UserList 格式 {'XuKailong':{'UserName':'', 'NickName':'FlameMan', 'Stock':None, 'News':None}}   #初始用户列表
    Output  = ''
    if callName in UserList.keys(): # 如果用户存在
        user = UserList[callName] # 是一个字典，而不是名字
        Output = Output + '\n'
        if user['Stock']:
            Output = Output + user['Stock'].printInfo()
        if user['News']:
            Output = Output + user['News'].printInfo()
        Output = Output + '\n'
    else:
        Output = '用户' +  str(callName) + '不存在于用户列表!'
    return Output
def openStockofUser(UserList, paras):
#\'os ShiRui\'： \t 开启ShiRui主账号下股票功能\n 
#    UserList 格式 {'XuKailong':{'UserName':'', 'NickName':'FlameMan', 'Stock':None, 'News':None}}   #初始用户列表
    if len(paras)!=2:
        Output = '#Error: ' + str(label) + ' openStockofUser(), 参数错误！\n' + str(paras) + '\n'
        Output = Output + '操作用户股票监控信息：\n \' os ShiRui\'\n  os 表示命令种类，打开用户股票监控，ShiRui表示用户callName'
        print(paras)
    else:
        callName = paras[1]
        try: # 首先，检查用户是否在列表中
            if callName in UserList.keys():
                if not UserList[callName]['Stock']:
                    UserList[callName]['Stock'] = sm.TStockMonitor(callName, UserList[callName]['NickName'], True)
                    Output = '用户' +  str(callName) + '的股票监控成功开通！'
                else:
                    Output = '开通失败：用户' +  str(callName) + '的股票监控已经开通！'
            else:
                Output = '用户' +  str(callName) + '不存在于用户列表!'
        except Exception as e:   # 如果账号不成功，什么也不做，并返回消息
            Output = '# 用户股票监控开通异常: ' + str(e) 
            write2Log(Output)
            print(Output)
            SendAlert2Master(Output)
    return Output      
def closeStockofUser(UserList, paras):
#\'cs ShiRui\'： \t 关闭ShiRui主账号下股票功能（股票和新闻至少开一个）\n 
#    UserList 格式 {'XuKailong':{'UserName':'', 'NickName':'FlameMan', 'Stock':None, 'News':None}}   #初始用户列表
    global Debug
    if len(paras)!=2:
        Output = '#Error: ' + str(label) + ' closeStockofUser(), 参数错误！\n' + str(paras) + '\n'
        Output = Output + '操作用户股票监控信息：\n \' cs ShiRui\'\n  os 表示命令种类，关闭用户股票监控，ShiRui表示用户callName'
        print(paras)
    else:
        callName = paras[1]
        try: # 首先，检查用户是否在列表中
            if callName in UserList.keys():
                if UserList[callName]['Stock']: # 若存在，关闭
                    # 判断是否存在News
                    if UserList[callName]['News']:
                        UserList[callName]['Stock'].Bye(Debug)
                        del UserList[callName]['Stock']
                        UserList[callName]['Stock'] = None
                        Output = '用户' +  str(callName) + '的股票监控成功关闭！'
                    else:
                        Output = '关闭失败：用户' +  str(callName) + '的账户必须存在一个监控，否则请直接删除该用户！'
                else:
                    Output = '关闭失败：用户' +  str(callName) + '的股票监控不存在！'
            else:
                Output = '用户' +  str(callName) + '不存在于用户列表!'
        except Exception as e:   # 如果账号不成功，什么也不做，并返回消息
            Output = '# 用户股票监控关闭异常: ' + str(e) 
            write2Log(Output)
            print(Output)
            SendAlert2Master(Output)
    return Output    
def openNewsofUser(UserList, paras):
#\'on ShiRui\'： \t 开启ShiRui主账号下新闻功能\n  
#    UserList 格式 {'XuKailong':{'UserName':'', 'NickName':'FlameMan', 'Stock':None, 'News':None}}   #初始用户列表
    global Debug
    if len(paras)!=2:
        Output = '#Error: ' + str(label) + ' openNewsofUser(), 参数错误！\n'  + str(paras) + '\n'
        Output = Output + '操作用户新闻监控信息：\n \' on ShiRui\'\n  on 表示命令种类，打开用户新闻监控，ShiRui表示用户callName'
        print(paras)
    else:
        callName = paras[1]
        try: # 首先，检查用户是否在列表中
            if callName in UserList.keys():
                if not UserList[callName]['News']:
                    UserList[callName]['News'].Bye(Debug)
                    UserList[callName]['News'] = ns.TBaiDuNewsScapper(callName, UserList[callName]['NickName'], True)
                    Output = '用户' +  str(callName) + '的新闻监控成功开通！'
                else:
                    Output = '开通失败：用户' +  str(callName) + '的新闻监控已经开通！'
            else:
                Output = '用户' +  str(callName) + '不存在于用户列表!'
        except Exception as e:   # 如果账号不成功，什么也不做，并返回消息
            Output = '# 用户新闻监控开通异常: ' + str(e) 
            write2Log(Output)
            print(Output)
            SendAlert2Master(Output)
    return Output   
def closeNewsofUser(UserList, paras):
#\'cn ShiRui\'： \t 关闭ShiRui主账号下股票功能（股票和新闻至少开一个）\n 
#    UserList 格式 {'XuKailong':{'UserName':'', 'NickName':'FlameMan', 'Stock':None, 'News':None}}   #初始用户列表
    if len(paras)!=2:
        Output = '# 错误: ' + str(label) + ' closeNewsofUser(), 参数错误！\n' + str(paras) + '\n'
        Output = Output + '操作用户新闻监控信息：\n \' cn ShiRui\'\n  cn 表示命令种类，关闭用户新闻监控，ShiRui表示用户callName'
        print(paras)
    else:
        callName = paras[1]
        try: # 首先，检查用户是否在列表中
            if callName in UserList.keys():
                if UserList[callName]['News']: # 若存在，关闭
                    if UserList[callName]['Stock']:
                        UserList[callName]['News'].Bye(Debug)
                        del UserList[callName]['News']
                        UserList[callName]['News'] = None
                        Output = '用户' +  str(callName) + '的新闻监控成功关闭！'
                    else:
                        Output = '关闭失败：用户' +  str(callName) + '的账户必须存在一个监控，否则请直接删除该用户！'
                else:
                    Output = '关闭失败：用户' +  str(callName) + '的新闻监控不存在！'
            else:
                Output = '用户' +  str(callName) + '不存在于用户列表!'
        except Exception as e:   # 如果账号不成功，什么也不做，并返回消息
            Output = '# 用户新闻监控关闭异常: ' + str(e) 
            write2Log(Output)
            print(Output)
            SendAlert2Master(Output)
    return Output   
def sendNotic2Users(UserList, paras):
#    \'snotice all 这是管理员通知！\'： \t 向所有主账号下所有用户发送消息'这是管理员通知！'
#    \'snotice ShiRui 这是管理员通知！\'： \t 向ShiRui主账号下用户发送消息'这是管理员通知！' 
    global mu 
    if len(paras)!=3:
        Output = '# 错误: ' + str(label) + ' sendNotic2Users(), 参数错误！\n' + str(paras) + '\n'
        Output = Output + '向用户发通知：\n \'snotice all 这是管理员通知！\'\n  snotice 表示命令种类，发送通知，ShiRui表示用户callName，用户为all时，向所有用户发送消息！'
        print(paras)
    else:
        Output = ''
        callName = paras[1]
        notice = paras[2]
        try: # 首先，检查用户是否在列表中
            if callName == 'all':
                with mu:
                    for user in UserList:
                        Output = Output + sendNotice2OneUser(UserList, user, notice)
            else:
               # 向单个用户发送消息
               Output = Output +  sendNotice2OneUser(UserList, callName, notice)
        except Exception as e:   # 如果账号不成功，什么也不做，并返回消息
            Output = '# 用户通知发送异常: ' + str(e) 
            write2Log(Output)
            print(Output)
            SendAlert2Master(Output)
    return Output
def sendNotice2OneUser(UserList, callName, msg):
    Output = ''
    sentmsg = '#### 管理员通知 ####\n' + msg
    try:
        if callName in UserList.keys():
            if UserList[callName]['News']: # 若存在，发送消息
                WeChat.SendWeChatMsgToUserList(UserList[callName]['News'].UserList, sentmsg, UserList[callName]['News'].logfile)
            if UserList[callName]['Stock']:
                WeChat.SendWeChatMsgToUserList(UserList[callName]['Stock'].UserList, sentmsg, UserList[callName]['Stock'].logfile)
            Output = '向主用户 ' +  str(callName) + ' 的成员成功发送通知！\n'
        else:
            Output = '用户' +  str(callName) + '不存在于用户列表!\n'
    except Exception as e:
        Output = '# 用户 ' + callName + ' 通知发送异常: ' + str(e)  + '\n'
        write2Log(Output)
        print(Output)
        SendAlert2Master(Output)
    return Output   
def isMasterWork(UserList, msg):
#    UserList 格式 {'XuKailong':{'UserName':'', 'NickName':'FlameMan', 'Stock':None, 'News':None}}   #初始用户列表
    # 此处UserList为主用户列表，msg为微信中收到的原始消息
    # 本函数中不需要发消息，只需要返回消息 masterWork：是否是管理员操作, sndmsg：消息内容
    global logfile, label
    masterWork = True
    cmd = str(msg['Text']).lstrip().rstrip().split(' ')
    write2Log('收到来自管理员' + str(msg['User']['NickName'])+'的消息：\n\'' + str(msg['Text']) + '\'')
    cmd = str(msg['Text']).lstrip().rstrip().split(' ')
    sndmsg = str(label + '\n')
    if len(cmd) < 1: # 不是管理员命令，返回让上一层处理
        sndmsg = sndmsg + '我看不懂你在说什么！'
        return False, '管理员命令异常：命令参数小于1个:\n'  + str(cmd) + '\n'
    Option = cmd[0]  # 以下函数中均无需向用户发消息，只需要返回消息就好
    if Option == 'h':
        sndmsg = sndmsg + HelpMaster()
    elif Option == 'lall':
        sndmsg = sndmsg + listAllUsers(UserList)
    elif Option == 'l':
        sndmsg = sndmsg + listUser(UserList, cmd)
    elif Option == 'amu':
        sndmsg = sndmsg + addUser2UserList(UserList, cmd)
    elif Option == 'rmu':
        sndmsg = sndmsg + rmUserFromUserList(UserList, cmd)
    elif Option == 'os':
        sndmsg = sndmsg + openStockofUser(UserList, cmd)
    elif Option == 'cs':
        sndmsg = sndmsg + closeStockofUser(UserList, cmd)
    elif Option == 'on':
        sndmsg = sndmsg + openNewsofUser(UserList, cmd)
    elif Option == 'cn':
        sndmsg = sndmsg + closeNewsofUser(UserList, cmd)
    elif Option == 'snotice':
        sndmsg = sndmsg + sendNotic2Users(UserList, cmd)   
    elif Option == 'setslt':
        sndmsg = sndmsg + setSleepTime(cmd)          
    elif Option == 'getslt':
        sndmsg = sndmsg + showSleepTime()    
    elif Option == 'lresp':
        sndmsg = sndmsg + WeChat.listRespon()            
    elif Option == 'rresp':
        sndmsg = sndmsg + WeChat.rmRespon(msg['Text'])            
    elif Option == '新闻' or Option == '股票':
        # 针对子类进行处理，判断指定主用户是否具有相应类
        cmd_temp = cmd[1:len(cmd)] # 过滤其 第一个 新闻 或者 股票 
        print(str(cmd_temp))
        ## 以下操作仅限于管理员账号 ##
        if len(cmd_temp) < 2: # 不是管理员命令，返回让上一层处理
            sndmsg = sndmsg + '我看不懂你在说什么！\n' + HelpMaster()
            return False, '管理员命令异常：命令参数小于1个:\n'  + str(cmd_temp) + '\n' + sndmsg
        callName = cmd_temp[1] # 获得要操作的账户
        if callName not in UserList.keys(): # 指定主用户不存在
            sndmsg = sndmsg + '监控类操作异常：指定主用户不存在！' + callName + '\n'
            return False, sndmsg
        else:
            newOption = cmd_temp[0]
            mainUser = UserList[callName] # {'UserName':'', 'NickName':'FlameMan', 'Stock':None, 'News':None}
            stock = mainUser['Stock']
            news = mainUser['News']
            if Option == '新闻': # 主用户是否有新闻监控
                if news:
                    # 执行正常操作
                    if newOption == 'au':
                        sndmsg = sndmsg + news.addUser2UserList(cmd_temp, 'FlameMan') # cmd_temp以命令开头，如au
                    elif newOption == 'ru':
                        sndmsg = sndmsg + news.rmUserFromUserList(cmd_temp, 'FlameMan') # cmd_temp以命令开头，如au
                    elif newOption == 'akw':
                        sndmsg = sndmsg + news.addKeyword2List(cmd_temp, 'FlameMan') # cmd_temp以命令开头，如au
                    elif newOption == 'rkw':
                        sndmsg = sndmsg + news.rmKeywordfromList(cmd_temp, 'FlameMan') # cmd_temp以命令开头，如au
                    elif newOption == 'afc':
                        sndmsg = sndmsg + news.addComp2FieldList(cmd_temp, 'FlameMan') # cmd_temp以命令开头，如au                        
                    elif newOption == 'rfc':
                        sndmsg = sndmsg + news.rmCompfromFieldList(cmd_temp, 'FlameMan') # cmd_temp以命令开头，如au                        
                    elif newOption == 'srd':
                        sndmsg = sndmsg + news.setResDays(cmd_temp, 'FlameMan') # cmd_temp以命令开头，如au
                    elif newOption == 'lup':
                        sndmsg = sndmsg + news.listUserParas(cmd_temp, 'FlameMan') # cmd_temp以命令开头，如au
                    elif newOption == 'sup':
                        sndmsg = sndmsg + news.setUserParas(cmd_temp, 'FlameMan') # cmd_temp以命令开头，如au
                    else:
                        sndmsg = sndmsg + '新闻监控类操作异常：我看不懂你说什么！\n' +  str(HelpMaster()) + '\n'
                        return False, sndmsg
                else:
                    sndmsg = sndmsg + '新闻监控类操作异常：指定主用户尚未开通新闻监控功能！' + callName + '\n'

            if Option == '股票': # 主用户是否有股票监控
                if stock:
                    # 执行正常操作
                    if newOption == 'au':
                        sndmsg = sndmsg + stock.addUser2UserList(cmd_temp, 'FlameMan') # cmd_temp以命令开头，如au
                    elif newOption == 'ru':
                        sndmsg = sndmsg + stock.rmUserFromUserList(cmd_temp, 'FlameMan') # cmd_temp以命令开头，如au
                    elif newOption == 'srd':
                        sndmsg = sndmsg + stock.setResDays(cmd_temp, 'FlameMan') # cmd_temp以命令开头，如au
                    else:
                         sndmsg = sndmsg + '股票监控类操作异常：我看不懂你说什么！\n' +  str(HelpMaster()) + '\n'
                         return False, sndmsg
                else:
                    sndmsg = sndmsg + '股票监控类操作异常：指定主用户尚未开通股票监控功能！' + callName + '\n'
    else:
        masterWork = False
        sndmsg = ''
    return masterWork, sndmsg
def printUserList(UserList, label):
    Output = ''
    if len(UserList) < 1:
        Output = Output + str(label) + ': 用户列表为空！'
    else:
        with mu:
            Output = Output + label + ' 用户列表如下:\n' 
            for user in UserList:
                # 分别打印昵称，用户名和NickName
                Output = Output + '标称名 -- ' + str(user) + '， 用户名 -- ' + str(UserList[user]['UserName']) + '， 昵称 -- ' + str(UserList[user]['NickName'])
                if UserList[user]['Stock']:
                    Output = Output + ', 股票监控：开启'
                if UserList[user]['News']:
                    Output = Output + ', 新闻监控：开启'
    return Output
def showSleepTime():
#     \'getslt\'： \t 显示扫描间隔时间        
    global sleeptime_L, sleeptime_S
    return '#两次扫面时间间隔# 休市时： '  + str(sleeptime_L) + ' s，开市时：' + str(sleeptime_S) + ' s !'
def setSleepTime(paras):
 #   \'setslt 10\'： \t 设置休眠时间为 10 s   
    global sleeptime_L, sleeptime_S
    if len(paras)!=3:
        Output = '# 错误: ' + str(label) + ' setSleepTime(), 参数错误！\n' + str(paras) + '\n'
        Output = Output + '向用户发通知：\n \'setslt 900 60\'： \t 设置休眠时间为分别为900 s（休市），60 s（开市）   ！'
        print(paras)
    else:
        Output = ''
        time_l = float(paras[1])
        time_s = float(paras[2])
        try: # 首先，检查用户是否在列表中
            if time_s < 0.01 or time_l < 0.01: # 太短休息时间还不如不休息呢，是不是
                Output = '休息时间太短，不干！'
            else:
                sleeptime_L = time_l
                sleeptime_S = time_s
                Output = '休市时扫描间隔设置为 '  + str(time_l) + ' s，开市时扫描间隔设置为：' + str(time_s) + ' s !'
            return Output         
        except Exception as e:   # 如果账号不成功，什么也不做，并返回消息
            Output = '# 两次扫描间隔时间设置异常: ' + str(e) 
            write2Log(Output)
            print(Output)
            SendAlert2Master(Output)
    return Output
def pickleDump2file(UserList, filename):
    try:
        with mu:
            data = {}
            for callName in UserList.keys():
                user = UserList[callName]
                news = False
                stock = False
                if UserList[callName]['Stock']:
                    stock = True
                if UserList[callName]['News']:
                    news = True
                data.setdefault(callName, {'UserName':user['UserName'], 'NickName':user['NickName'], 'Stock':stock, 'News':news}) 
        # 只写入 callName, UserName, NickName
            with open(filename, 'wb') as f:
                pickle.dump(data, f)
                print(label + '消息：pickle file写入成功！')
                write2Log(label + '：pickle file写入成功！')
    except Exception as e:
        print(label + '：pickle file写入异常！'+ str(e))
        write2Log(label + '：pickle file写入异常！')    
def getDatafromPickle(filename):
    Flag = False
    try:
        with open(filename, 'rb') as f:
            data = pickle.load(f)
            Flag = True
            print(label + '：pickle file读取成功！')
            write2Log(label + '：pickle file读取成功！')
    except Exception as e:
        Flag = False
        data = label + '热启动失败！开始初始化  ' + str(e)
        print(data)
        write2Log(data)
    return Flag, data           



