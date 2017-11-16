# -*- coding: utf-8 -*-
"""
Created on Fri May 19 10:35:15 2017

@author: MoBeiHuYang
"""

import itchat, datetime
from itchat.content import *
import threading
import random
import time
import pickle, os
pickle_dir = 'pickle_do_not_delete/'
log_dir = 'log_do_not_delete/'
news_dir = 'news_do_not_delete/'
emotion_dir = 'emotion_do_not_delete/'
mu = threading.RLock()

rdmResponsCore = [\
'我爱你啦！',         '祝你一天好心情!',         '一切顺利啦！',            '你还好吗？',            '朕今天并不开心！',   \
'尝试下其他选项吧!',   '快要下班了嘛?',          '今天吃什么饭呀?',          '周末约起来？',          '你瞅啥！', \
'你们这些凡人！',      '登临绝顶，我便为峰！',   '宝宝不开心！',             '你给我发个红包吧！',     '这个故事真的很难编！',\
'找不到工作怎么办？',  '累了就休息一下吧~',      '向工作在一线的同志们致敬！','明天一起去看日出吧！',   '我的媳妇是石睿~',\
'我已结婚，请自重！',  '嗯',                    '好的',                     '你说的很有道理！',      '谢谢！',\
'拜拜！',             '嗯，请继续',             '别再这里耍流氓啦~',        '我要喊人了',            '你信不信我要喊人了',\
'真的假的？',         '好呀',                   '来个美女看看',             '你后面那位是你领导吗？', '你领导正在看着你', \
'保重啦',             '我要闪人了！',           '明天天气如何？',           '今天工作如何？',         '今天心情挺好呀？',\
'我就欣赏你这样的！', '我就喜欢你这股劲！',       '我只喜欢你一个人！',      '赶紧过来调戏我！',        '睡觉中，勿扰。。。', \
'去路边调戏个姑娘吧!', '喜欢写代码，就是没工作',  '千金易买，工作难求！',     '要珍惜身边美好的事物！',  '没人陪我爬山！']
rdmResponsAdd = ['这是个测试吧？']
dic_resp = dict.fromkeys(rdmResponsAdd, 1)
maxResps = 10000
rdmRespondFile = pickle_dir + '热启动语句库.pickle'
def getRespons(msg, probability ): # probability: 0 - 100, 值越大，文本消息的概率越大
    global mu, rdmResponsCore, rdmResponsAdd, maxResps, dic_resp
    if '动图' in msg:
        reply = getGifFileinDir()
        return reply
    elif '发个图片' in msg:
        reply = getRandomEmotion()
        return reply
    elif '时间' in msg or '几点' in msg:
        reply = '现在时间是： ' + datetime.datetime.now().strftime('%y-%m-%d %H:%M:%S')
        return reply
    
    temp_resp = rdmResponsCore + rdmResponsAdd
    Flag = random.randint(0,100)
    if Flag < int(probability):
        reply = temp_resp[random.randint(0,len(temp_resp) - 1)]
    else:
        reply = getRandomEmotion()
    try:
        with mu:
            if len(msg) > 1: # 如果是有用消息
                if msg not in rdmResponsAdd:
                    if len(rdmResponsAdd) > maxResps: # 如果超过上限值，排序，剔除最不常用的，然后加入
                        # 查找最不常用的，并pop
                        # 排序，移出
                        temp = sorted(dic_resp.items(), key=lambda d:d[1], reverse = True)
                        lastmsg = temp[-1][0]  #取最后一个语句的对话
                        rdmResponsAdd.remove(lastmsg)
                        dic_resp.pop(lastmsg)
                        # 添加
                        rdmResponsAdd.append(msg)
                        dic_resp.setdefault(msg, 1)
                    else:
                        # 添加，并建立字典
                        rdmResponsAdd.append(msg)
                        dic_resp.setdefault(msg, 1)
                else: # 如果语句已经存在, 其使用频率 + 1
                    dic_resp[msg] = min(dic_resp[msg] + 1, 10000) # 使用频率不能超过1W， 避免大整数溢出
                    minValue  = min(dic_resp.values()) # 最小值不能超过5000，超过，整体重置
                    if  minValue > 5000:
                        for item in dic_resp[msg]:
                            dic_resp[msg] = dic_resp[msg] - minValue
    except Exception as e:
        print('# 语句添加出错！')   
    return reply       
def listRespon():
#  \'lresp\'： \t 返回所有库中语句'    
    global mu, dic_resp
    Output = '目前语句库中语句及其使用频率如下：\n'
    with mu:
        Output = Output + str(dic_resp)
    return Output
def rmRespon(rawmsg):
#    \'rresp 这是个测试！\'： \t 从语句库中查找并删除语句'这是个测试！''  
    global mu
    msg = rawmsg.replace('rresp ','')
    try:
        with mu:
            if msg in rdmResponsAdd:
                rdmResponsAdd.remove(msg)
                dic_resp.pop(msg)
                Output = '语句 ' + str(msg) + ' 从语句库中移除成功！'
            else: # 如果语句已经存在, 其使用频率 + 1
                Output = '语句 ' + str(msg) + ' 不存在于语句库中！'
            # 移出系统信息，如’因内容受保护，表情未能成功发送'
            for msg2 in rdmResponsAdd:
                if '因内容受保护，表情未能成功发送' in msg2:
                    rdmResponsAdd.remove(msg2)
                    dic_resp.pop(msg2)
                    Output = Output + '\n语句 ' + str(msg2) + ' 成功移出语句库！'
    except Exception as e:
        Output = '# 语句移除出错！'
        print(Output)
    return Output  
def write2Log(msg, logfile):
    try:
        f = open(logfile,'a+')
        f.write(msg + '\n')
        f.close()
    except Exception as e:
        print('微信函数处理异常：写入工作日志异常：' + str(e) )
        pass
def StartWeChat():
    """
    Created on Fri May 19 10:35:15 2017
    
    @author: MoBeiHuYang
    登陆微信，并将其置于run状态
    成功，返回 True
    异常，返回 False
    """
    global log_dir
    try:
        itchat.auto_login(True)
        return True
    except Exception as e:
        errormsg = '# w微信登陆异常：' + str(e)
        write2Log(errormsg,log_dir +'微信登陆异常.log')
        print(errormsg)
        itchat.logout()
        return False
def WeChatExit():
    itchat.logout()
def WeChatOnDuty():
    global log_dir
    try:
        itchat.run(blockThread = False)
    except Exception as e:
        errormsg = '# 微信监控异常：' + str(e)
        write2Log(errormsg,log_dir + '微信异常.log')
        print(errormsg)
        itchat.logout()
        raise Exception('# 微信监控异常：' + str(e) + '，微信账号退出！')
        
def InitWeChatUsers(UserList, logfile):
    global mu
    with mu:
        for user in UserList:
             temUser = itchat.search_friends(nickName=UserList[user]['NickName'])
             if len(temUser) < 1:
                 raise Exception('微信用户寻找异常：用户' + str(UserList[user]['NickName']) + ' 未找到!')
             else:
                 UserList[user]['UserName'] = temUser[len(temUser)-1]['UserName']
                 write2Log('微信用户初始化：\n 用户昵称: ' + str(UserList[user]['NickName']) + '，用户账号： ' + str(UserList[user]['UserName']), logfile)
def findWeChatUser(my_nickName, logfile):
         userName = ''
         temUser = itchat.search_friends(nickName=my_nickName)
         if len(temUser) < 1:
             raise Exception('微信用户寻找异常：用户 ' + str(my_nickName) + ' 未找到！')
         else:
             userName = temUser[len(temUser)-1]['UserName']
             write2Log('Found WeChat user: ' + str(my_nickName) + ': ' + str(userName), logfile)
             
         return userName
            
def SendWeChatTextMsg(Message, useraccount, username, logfile):
    try:  # 如果发送文件，文件名不能为中文，否则发不出去
        msg = str(Message).replace('\xa0',' ')
        if (not '@fil@' in Message) and (not '@img@' in Message) and (not '@vid@' in Message):
            msg = 'To ' + str(username) + ': \n'  + msg 
        if not itchat.send(msg, useraccount):
            # 如果发送失败
            itchat.logout()
            time.sleep(5*60)  
            print("微信文本信息发送失败，尝试重新登录！")
            itchat.auto_login(True)
            itchat.run(blockThread = False)
            time.sleep(10*60)  
            itchat.send(msg, useraccount)
            time.sleep(5*60)  
        write2Log('向' + str(username) + '发送文本消息：\n\' ' + str(msg) + '\' ', logfile)
    except Exception as e:
        errmsg = '#微信文本消息发送异常：' + str(e)
        write2Log(errmsg, logfile)
        print(errmsg)    
        
def SendWeChatImgMsg(filename, useraccount, username, logfile):
    try:
        if not itchat.send_image(filename, useraccount):
            # 如果发送失败
            itchat.logout()
            time.sleep(5*60) 
            print("微信图像信息发送失败，尝试重新登录！")
            itchat.auto_login(True)
            itchat.run(blockThread = False)   
            time.sleep(5*60)     
            itchat.send_image(filename, useraccount)
            time.sleep(5*60)  
        write2Log('向' + str(username) + '发送图片消息：\n\' ' + str(filename) + '\' ', logfile)
    except Exception as e:
        errmsg = '# 微信图片消息发送异常：' + str(e)
        write2Log(errmsg, logfile)
        print(errmsg)   
        
def SendWeChatMsgToUserList(UserList, msgcontent, logfile):   
    global mu
    with mu:     
        for user in UserList:
            SendWeChatTextMsg(str(msgcontent), UserList[user]['UserName'], UserList[user]['NickName'], logfile)
def WeChatpickleDump2file():
    global rdmResponsAdd, dic_resp, rdmRespondFile
    try:
        data = {}
        data.setdefault('rdmResponsAdd',rdmResponsAdd) 
        data.setdefault('dic_resp',dic_resp) 
        with open(rdmRespondFile, 'wb') as f:
            pickle.dump(data, f)
            print('语句库：pickle file写入成功！')
            write2Log('语句库：pickle file写入成功！',log_dir+'非用户聊天日志.log')
    except Exception as e:
        print('语句库：pickle file写入异常！'+ str(e))
        write2Log('语句库：pickle file写入异常！',log_dir+'非用户聊天日志.log')    
def WeChatgetDatafromPickle():
    global rdmResponsAdd, dic_resp, rdmRespondFile
    Flag = False
    try:
        with open(rdmRespondFile, 'rb') as f:
            data = pickle.load(f)
            rdmResponsAdd = data['rdmResponsAdd']
            dic_resp = data['dic_resp']
            Flag = True
            print('语句库：pickle file读取成功！')
            write2Log('语句库：pickle file读取成功！',log_dir+'非用户聊天日志.log')
    except Exception as e:
        Flag = False
        data = '# 语句库热启动失败，开始初始化：' + str(e)
        print(data)
        write2Log(data,log_dir+'非用户聊天日志.log')
    return Flag, data 
def getRandomEmotion():
    global emotion_dir
    fileList = getFileinDir(emotion_dir)
    fileName = '@img@' + fileList[random.randint(0,len(fileList) - 1)]
    return fileName

def getFileinDir(dirName):
    try:
        result = []
        for root,dirs,files in os.walk(dirName):
            for file in files:
                result.append(root + file)
    except Exception as e:
        pass
    return result  

def getGifFileinDir():
    global emotion_dir
    try:
        result = []
        for root,dirs,files in os.walk(emotion_dir):
            for file in files:
                if file.endswith('.gif'):
                    result.append(root + file)
        fileName = '@img@' + result[random.randint(0,len(result) - 1)]            
    except Exception as e:
        pass
    return fileName        
