import b3
import b3.events
import b3.plugin
import time
import threading
import json
import urllib2
import os
import requests
from datetime import datetime
from MySQLdb import _mysql
import MySQLdb
from b3.clients import Group

pluginInstance = None

class chatLogger:
    def __init__(self,url):
        self.url = url
    def log(self,author,msg):
        data = json.dumps({"content":"**%s:** %s"%(author.name,msg)})        
        req = urllib2.Request(self.url, data, {
            'Content-Type': 'application/json',
            "User-Agent": "webhook"
        })
        try:
            urllib2.urlopen(req)
        except urllib2.HTTPError as ex:
            self.debug("err pushing data")
            self.debug("Data: %s\nCode: %s\nRead: %s" % (data, ex.code, ex.read()))

class DiscodPlugin(b3.plugin.Plugin):

    requiresConfigFile = True
    
    def onLoadConfig(self):
        #loading settings
        self.create_table = int(self.config.getint("settings","create_table"))
        self.warn_senior = int(self.config.getint("settings","warn_senior"))
        self.send_eligible = int(self.config.getint("settings","send_eligible"))
        self.min_interval = int(self.config.getint("settings","minInterval"))
        self.autoPromote = int(self.config.getint("settings","auto_promote"))
        self.autoDemote = int(self.config.getint("settings","auto_demote"))
        self.invite_link = str(self.config.get("settings","invite_link"))
        self.susinterval = int(self.config.get("settings","susinterval"))
        self.check_vpn = int(self.config.getint("settings","check_vpn"))
        self.check_duplicate = int(self.config.getint("settings","check_duplicate"))
        self.auto_ss = int(self.config.getint("settings","auto_ss"))
        self.store_misc = int(self.config.getint("settings","store_misc"))
        self.webhookurl_duplicate = str(self.config.get("settings","webhookurl_duplicate"))
        self.webhookurl_vpn_public = str(self.config.get("settings","webhookurl_vpn_public"))
        self.webhookurl_vpn_private = str(self.config.get("settings","webhookurl_vpn_private"))
        self.sqlpath = str(self.config.getpath("settings","sqlpath"))
        self.chatlog = self.config.getint("settings","chatlog")
        if self.chatlog:
            self.debug("chat logging to discord enabled.")
            self.webhookurl_chatlog = str(self.config.get("settings","webhookurl_chatlog"))
            self.chatLogger = chatLogger(self.webhookurl_chatlog)
            self.debug("will log chats @ %s"%self.webhookurl_chatlog)
            self.chat_evts = [b3.events.EVT_CLIENT_SAY,b3.events.EVT_CLIENT_TEAM_SAY,b3.events.EVT_CLIENT_SQUAD_SAY]
        else:
            pass

        #loading kills required
        self.reqKills = {}
        for level in self.config.options("kills"):
            self.reqKills[level] = (self.config.getint("kills",level))
        self.reqKills["user"] = 0
        self.reqKills["guest"] = 0

        #loading responses
        self.id_message = str(self.config.get("responses","id_message"))
        self.warn_message = str(self.config.get("responses","warn_reason"))
        self.success_message = str(self.config.get("responses","success_message"))
        self.reattempt_message = str(self.config.get("responses","reattempt_message"))
        self.notfound_message = str(self.config.get("responses","notFound_message"))
        self.linktest_message = str(self.config.get("responses","linktest_message"))
        self.linktest_pending_message = str(self.config.get("responses","linkPending_message"))
        self.autoPromotion_message = str(self.config.get("responses","autoPromotion_message"))
        self.autoPromotionEligible_message = str(self.config.get("responses","autoPromotionEligible_message"))
        self.autoDemotion_message = str(self.config.get("responses","autoDemotion_message"))
        self.ss_sus_announce = str(self.config.get("responses","ss_sus_announce"))
        
        #loading specific help docstrings for cmds
        funcs = [func for func in dir(self) if func.startswith("_") is False]
        for func in funcs:
            try:
                if func.startswith("cmd_"):
                    f1 = getattr(self,func)
                    f1.__func__.__doc__ = str(self.config.get("help",func))
            except Exception as ex:
                self.debug(ex)

    def onStartup(self):
        global pluginInstance
        pluginInstance = self
        self.screenshots = {}
        self._query = self.console.storage._query
        self.curr_guidz = {}
        self.curr_ipz = {}

        if self.check_duplicate==1:
            refresh_thread = threading.Thread(target=self.refreshGuids)
            refresh_thread.daemon = True
            refresh_thread.start()
  
        self._adminPlugin = self.console.getPlugin('admin')
        if not self._adminPlugin:
            self.debug('Could not find admin plugin')
            return False

        if 'commands' in self.config.sections():
            for cmd in self.config.options('commands'):
                level = self.config.get('commands', cmd)
                sp = cmd.split('-')
                alias = None
                if len(sp) == 2: cmd, alias = sp
                func = self.getCmd(cmd)
                if func: self._adminPlugin.registerCommand(self, cmd, level, func, alias)

        self.registerEvent(b3.events.EVT_CLIENT_AUTH)
        self.registerEvent(b3.events.EVT_CLIENT_DISCONNECT)
        self.registerEvent(b3.events.EVT_CLIENT_SAY)
        self.registerEvent(b3.events.EVT_CLIENT_TEAM_SAY)
        self.registerEvent(b3.events.EVT_CLIENT_SQUAD_SAY)

        # check if tables exist
        tableCheck = self._query("SHOW TABLES like 'discod'")
        rows = tableCheck.getRow()
        if rows == {}:
            if self.create_table:
                self.error("Required table \"disCOD\" doesn't exist. Querying table schema...")
                query = open(self.sqlpath+"\\discod.sql").read().replace("\n","")
                self._query(query)
        else:
            self.debug("Required table 'disCOD' exists.")

        if self.store_misc==1:
            tableCheck = self._query("SHOW TABLES like 'discod_clients_misc'")
            rows = tableCheck.getRow()
            if rows == {}:
                if self.create_table:
                    self.error("Required table for client misc. data doesn't exist. Querying table schema...")
                    query = open(self.sqlpath+"\\discod_clients_misc.sql").read().replace("\n","")
                    self.console.storage.query(query)
            else:
                self.debug("Required table for client misc. data exists.")

        if self.check_vpn==1:
            tableCheck = self._query("SHOW TABLES like 'discod_vpn_allowed'")
            rows = tableCheck.getRow()
            if rows == {}:
                if self.create_table:
                    self.error("Required table for VPN IDs doesn't exist. Querying table schema...")
                    query = open(self.sqlpath+"\\discod_vpn_allowed.sql").read().replace("\n","")
                    self._query(query)
            else:
                self.debug("Required table for VPN IDs exists.")
            
    def getCmd(self, cmd):
        cmd = 'cmd_%s' % cmd
        if hasattr(self, cmd):
            func = getattr(self, cmd)
            return func
        return None

    def cmd_id(self,data,client,cmd=None):
        if not data:
            cmd.sayLoudOrPM(client, self.id_message.format(client_name = client.name, client_id = client.id))
        else:
            inp = self._adminPlugin.parseUserCmd(data)
            client2 = self._adminPlugin.findClientPrompt(inp[0],client)
            if client2:
                cmd.sayLoudOrPM(client, self.id_message.format(client_name = client2.name, client_id = client2.id))
 
    def cmd_link(self,data,client,cmd=None):
        if not data:
            client.message('^7Incorrect command syntax. ^3!link <8-digit-pin>^7 or type ^2!help link')
            return False

        cursor = self._query("SELECT * FROM discod WHERE b3_id = %s;"%(str(client.id)))
        rows = cursor.getOneRow()
        if not rows:
            client.message(self.notfound_message.format(invite=self.invite_link))
        else:
            pin = rows['pass']
            linked = int(rows['linked'])
            if int(pin) == int(str(data).strip()):
                if linked == 1:
                    client.message(self.reattempt_message)
                    return False
                self._query("UPDATE discod SET linked = 1, linktime = UNIX_TIMESTAMP() WHERE b3_id = %s;"%(str(client.id)))
                cursor = self._query("SELECT dc_tag FROM discod WHERE b3_id = %s;"%(str(client.id)))
                rows = cursor.getOneRow()
                if rows['dc_tag']:
                    dc_tag = ""
                    for ch in rows['dc_tag']:
                        if not ch.isalnum() and not ch=="#" and not ch=="_" and not ch.isspace():
                            dc_tag+='?'
                        else: dc_tag+=ch
                cmd.sayLoudOrPM(client,self.success_message.format(id = client.id, dc_tag = dc_tag))
                promotion = self.getPromotion(client=client)
                if promotion is None: return
                else:
                    thread = threading.Thread(target=self.promoteClient,args=(client,promotion),)
                    thread.start()

            else:
                if linked == 1: client.message(self.reattempt_message)
                else:
                    if self.warn_senior==0:
                        if client.maxLevel < 80: self._adminPlugin.warnClient(client,self.warn_message)
                        else: client.message(self.warn_message)
                    else: self._adminPlugin.warnClient(client,self.warn_message)

    def cmd_unlink(self, data, client, cmd = None):
        if not data:
            client.message('^7Incorrect command syntax. ^3!unlink y^7')
            return False
        if str(data) == 'y':
            cursor = self._query("SELECT * FROM discod WHERE b3_id = %s;"%(str(client.id)))
            rows = cursor.getRow()
            if rows == {}:
                client.message(self.notfound_message.format(invite=self.invite_link))
            else:
                self._query("DELETE FROM discod WHERE b3_id = %s;"%(str(client.id)))
                cmd.sayLoudOrPM(client,"Unlinked your B3 ID from discod.")
     
    def cmd_linktest(self,data,client,cmd=None):
        if not data:
            self.getLinkStatus(client = client, cmd = cmd)
        else:
            inp = self._adminPlugin.parseUserCmd(data)
            client2 = self._adminPlugin.findClientPrompt(inp[0],client)
            if client2:
                self.getLinkStatus(client = client2, callerClient = client, cmd = cmd)

    def cmd_getss(self,data,client=None,cmd=None):
        if not data:
            client.message("Invalid parameters")
            return
        input = self._adminPlugin.parseUserCmd(data)
        sclient = self._adminPlugin.findClientPrompt(input[0], client)
        if not sclient:
            return
        if not sclient.cid:
            client.message("Invalid player")
            return
        client.message('Taking Screenshot of %s'%(sclient.name))
        try:
            self.Screenshot(sclient,client,True)
        except:
            return

    def Screenshot(self,client,taker,notifycheck):
        if notifycheck: strr = 'notify'
        else: strr = 'dontnotify'
        if not taker:
            self.console.write("getss %s" % (client.cid))
            return
        res = self.console.write("getss %s taker_slot_%s_%s_" % (client.cid,taker.cid,strr))
        self.screenshots[client]=time.time()
        return res

    def cmd_resolution(self,data,client,cmd=None):
        if not data:
            client.message("Invalid parameters")
            return
        input = self._adminPlugin.parseUserCmd(data)
        sclient = self._adminPlugin.findClientPrompt(input[0], client)
        if not sclient:
            return
        if not sclient.cid:
            client.message("Invalid player")
            return
        # checking for table 'discod_reso' onStartup
        check = self._query("SELECT * FROM discod_clients_misc WHERE client_id = %s;"%(str(sclient.id)))
        row = check.getOneRow()
        if not row:
            cmd.sayLoudOrPM(client,"Don't Know.")
            self.Screenshot(sclient,client,False)
            return
        time = datetime.fromtimestamp(int(row['time_edit'])).strftime("%d/%m/%Y")
        cmd.sayLoudOrPM(client,"^2%s ^7is playing at ^3%s, last checked %s"%(sclient.name,row['reso'],time))

    def getLinkStatus(self,client,callerClient=None,cmd=None):
        if not callerClient:
            callerClient = client
        cursor = self._query("SELECT * FROM discod WHERE b3_id = %s;"%(str(client.id)))
        rows = cursor.getOneRow()
        if not rows:
            callerClient.message(self.notfound_message.format(invite=self.invite_link))
        else:
            if int(rows['linked']) == 0:
                callerClient.message(self.linktest_pending_message)
            else:
                if rows['dc_tag']:
                    dc_tag = ""
                    for ch in rows['dc_tag']:
                        if not ch.isalnum() and not ch=="#" and not ch=="_" and not ch.isspace():
                            dc_tag+='?'
                        else: dc_tag+=ch
                time = datetime.fromtimestamp(int(rows['linktime'])).strftime("%Y/%m/%d %H:%M")
                cmd.sayLoudOrPM(callerClient,self.linktest_message.format(id=client.id, dc=dc_tag, time = time))

    def isLinked(self,client):
        res = self._query("SELECT * FROM discod WHERE b3_id = %s;"%client.id).getRow()
        if res == {}:
            return False
        else:
            if res["linked"]==1: return True
            else: return False
    
    def isDemoted(self,client):
        try:
            res = self._query("SELECT * FROM demotions WHERE client_id = %s;"%client.id).getRow()
            if res == {}:
                return False
            else:
                if res["inactive"]==1: return False
                else: return True
        except _mysql.ProgrammingError:
            #in case the demotions table doesn't exist
            return False

    def getKills(self,client):
        res = self._query("SELECT * FROM xlr_playerstats WHERE client_id = %s;"%client.id).getRow()
        if res=={}:
            return None
        else:
            return res["kills"]

    def getPromotion(self,client):
        cGroup = client.maxGroup.keyword
        cKills = self.getKills(client)
        if client.maxLevel == 100:
            return
        if self.isDemoted(client):
            self.debug("skipping promotion check for @%s cuz they have an active demotion."%client.id)
            return
        
        reqKills = sorted(self.reqKills.items(), key = lambda x:x[1])

        if cKills > self.reqKills[cGroup]:
            ind = None
            for i in range(0,len(reqKills)):
                if reqKills[i][0]==cGroup:
                    ind = i

        killsGroup = None

        for i in range(ind,len(reqKills)):
            if cKills>=reqKills[i][1]:
                killsGroup = reqKills[i][0]
            else:
                break

        group = Group(keyword=killsGroup)

        if group.keyword != cGroup:
            newGroup = self.console.storage.getGroup(group)
            return newGroup
        else:
            return None
    
    def getNextPromotion(self,client):
        cGroup = client.maxGroup.keyword
        cKills = self.getKills(client)
        if client.maxLevel == 100:
            return
        if self.isDemoted(client):
            self.debug("skipping promotion check for @%s cuz they have an active demotion."%client.id)
            return False
        
        if not self.isLinked(client):
            self.debug("skipping promotion check for @%s cuz they haven't linked."%client.id)
            return False
        
        reqKills = sorted(self.reqKills.items(), key = lambda x:x[1])
        ind = None
        if cKills > self.reqKills[cGroup]:
            ind = None
            for i in range(0,len(reqKills)):
                if reqKills[i][0]==cGroup:
                    ind = i

        killsGroup = None
        if ind == None: return False
        for i in range(ind,len(reqKills)):
            if cKills>=reqKills[i][1]:
                killsGroup = reqKills[i+1][0]
            else: break

        group = Group(keyword=killsGroup)

        if group.keyword != cGroup:
            newGroup = self.console.storage.getGroup(group)
            return newGroup
        else: return None
    
    def promoteClient(self,client,group):
        time.sleep(5)
        if not self.isLinked(client):
            if self.send_eligible==0:
                return
            timeDiff = int(time.time() - client.lastVisit)
            if timeDiff < self.min_interval:
                self.debug("not sending link reminder to @%s cuz client was last seen only %s seconds ago"%(client.id,timeDiff))
                return
            client.message(self.autoPromotionEligible_message.format(groupname=group.name,grouplevel=group.level,invite=self.invite_link))
        else:
            client.setGroup(group)
            client.save()
            client.message(self.autoPromotion_message.format(groupname=group.name,grouplevel=group.level))
        
    def onEvent(self,event):
        client = event.client
        if event.type in self.chat_evts:
            thr = threading.Thread(target = self.chatLogger.log,args=(event.client,event.data))
            thr.start()
        if event.type == b3.events.EVT_CLIENT_DISCONNECT:
            if client in self.screenshots:
                self.debug(self.screenshots[client])
                timediff = time.time() - self.screenshots[client]
                if timediff < self.susinterval:
                    self.console.say(self.ss_sus_announce % ("%s[^3@%s^7]" % (client.exactName,client.id), int(timediff)))
                del self.screenshots[client]
            if self.curr_guidz[client.guid].cid == event.client.cid:
                del self.curr_guidz[client.guid]
            '''if self.curr_ipz[client.ip].cid == event.client.cid:
                del self.curr_ipz[client.ip]'''
        if event.type == b3.events.EVT_CLIENT_AUTH:
            if self.store_misc==1:
                misc_thread = threading.Thread(target=self.misc,args=(event.client,))
                misc_thread.start()
            if self.check_duplicate==1:
                dup_thread = threading.Thread(target=self.checkDuplicate,args=(event.client,))
                dup_thread.start()
            if self.check_vpn==1:
                vpn_thread = threading.Thread(target=self.checkVpn,args=(event.client,))
                vpn_thread.start()
            if self.auto_ss==1:
                # self.autoSS(event.client)
                ss_thread = threading.Thread(target=self.autoSS,args=(event.client,))
                ss_thread.start()
            if self.autoDemote==1:
                if event.client.maxLevel>1:
                    if not self.isLinked(event.client):
                        group = Group(keyword="user")
                        newgroup = self.console.storage.getGroup(group)
                        event.client.setGroup(newgroup)
                        event.client.save()
                        event.client.message(self.autoDemotion_message)
                        self.debug("demoted @%s to user for not linking their account"%event.client.id)
            if self.autoPromote==1:
                if event.client.maxLevel == 0:
                    return
                promotion = self.getPromotion(client=event.client)
                if promotion is None: return
                else:
                    thread = threading.Thread(target=self.promoteClient,args=(event.client,promotion),)
                    thread.start()

    def cmd_nok(self,data,client,cmd=None):
        if data:
            inp = self._adminPlugin.parseUserCmd(data)
            client2 = self._adminPlugin.findClientPrompt(inp[0],client)
            if not client2: return
        else: client2 = client
        res = self.getNextPromotion(client2)
        self.debug(res)
        killdiff = None
        if res: killdiff = self.reqKills[res.keyword]-self.getKills(client2)
        if killdiff:
            cmd.sayLoudOrPM(client,self.config.get("responses","nok_message")%(killdiff,res.name,res.level))
            return
        cmd.sayLoudOrPM(client,"Not eligible for further promotion.")
    
    def cmd_allowvpn(self,data,client,cmd=None):
        if self.check_vpn != 1:
            client.message("VPN not being checked.")
        if not data:
            client.message("Invalid parameters.")
            return
        if data:
            inp = self._adminPlugin.parseUserCmd(data)
            client2 = self._adminPlugin.findClientPrompt(inp[0],client)
            if not client2: return
        res = self._query("select * from discod_vpn_allowed where client_id = %s"%client2.id).getOneRow()
        self.debug(res)
        if res == {} or res == None:
            self._query("insert into discod_vpn_allowed (client_id) values (%s);"%client2.id)
            cmd.sayLoudOrPM(client,"%s has been allowed to use VPN."%client2.name)
            embed = {
                    "title": "VPN allowed",
                    "description": "%s **@%s**\nAdmin: %s **%s**"%(client2.name,client2.id,client.name,client.id)
                }
            data = json.dumps({"embeds": [embed]})        
            req = urllib2.Request(self.webhookurl_vpn_private, data, {
                'Content-Type': 'application/json',
                "User-Agent": "webhook"
            })
            self.unblockVpn(client2)
            try:
                urllib2.urlopen(req)
            except urllib2.HTTPError as ex:
                self.debug("err pushing data")
                self.debug("Data: %s\nCode: %s\nRead: %s" % (data, ex.code, ex.read()))
        else:
            cmd.sayLoudOrPM(client,"Already allowed.")

    
    def sendDuplicate(self,data,client1,client2,type):
        embed = {
            "title": "Duplicate %s"%type,
            "description": "%s"%data,
            "fields": [
                {
                    "name": "Client 1",
                    "value": "%s [@%s] (%s)\n**IP:** %s\n**Steam ID:** %s"%(client1.name,client1.id,client1.cid,client1.ip,client1.var(self,"steam_id").toString()),
                    "inline": False
                },
                {
                    "name": "Client 2 (Kicked)",
                    "value": "%s [@%s] (%s)\n**IP:** %s\n**Steam ID:** %s"%(client2.name,client2.id,client2.cid,client2.ip,client2.var(self,"steam_id").toString()),
                    "inline": False
                }
            ]
        }
        data = json.dumps({"embeds": [embed]})        
        req = urllib2.Request(self.webhookurl_duplicate, data, {
            'Content-Type': 'application/json',
            "User-Agent": "webhook"
        })
        try:
            urllib2.urlopen(req)
        except urllib2.HTTPError as ex:
            self.debug("err pushing data")
            self.debug("Data: %s\nCode: %s\nRead: %s" % (data, ex.code, ex.read()))

    def checkDuplicate(self,client):
        if client.guid in self.curr_guidz:
            _ping = int(self.getCurrentPing(self.curr_guidz[client.guid]))
            self.debug("PEEEENG: %s"%_ping)
            if(_ping == 0 or _ping == 999):
                self.curr_guidz[client.guid].kick(self._adminPlugin.getReason('ci'), 'ci')
                self.debug("kicked duplicate entry for %s cuz it was ci."%client.guid)
            else:
                plist = self.console.getPlayerList()
                for ele in plist:
                    self.debug(plist[ele])
                self.console.write("clientkick %s Duplicate GUID. Contact Admins."%client.cid)
                self.sendDuplicate(client.guid,self.curr_guidz[client.guid],client,"GUID")
        else:
            self.curr_guidz[client.guid]=client
            self.debug("unique guid connected")
            self.debug(self.curr_guidz.keys())

        #checks for duplicate IP addresses but people can have same IPs for many reasons
        '''
        if client.ip in self.curr_ipz:
            self.console.write("clientkick %s Duplicate IP Address. Contact Admins."%client.cid)
            self.sendDuplicate(client.ip,self.curr_ipz[client.ip],client,"IP")
        else:
            self.curr_ipz[client.ip]=client
            self.debug("unique ip address connected")
            self.debug(self.curr_ipz.keys())'''
    
    def refreshGuids(self):
        while True:
            plist = self.console.getPlayerList()
            curr_guidz = [plist[ele]["guid"] for ele in plist]
            for ele in self.curr_guidz.keys():
                if ele not in curr_guidz:
                    del self.curr_guidz[ele]
                    self.debug("popped guid %s from cache cuz player is no longer online"%ele)
            time.sleep(10)

    def blockVpn(self,client):
        os.system("sudo iptables -I INPUT -s %s -j DROP"%client.ip)
        self.debug("IP %s added to iptables"%client.ip)
    
    def unblockVpn(self,client):
        data = os.popen("iptables -L INPUT -v -n").read()
        hehe = [ele.split() for ele in data.split("\n")]
        drop_ipz = []
        for ele in hehe:
            try:
                if ele[2]=="DROP":
                    drop_ipz.append(ele[7])
            except IndexError:
                continue
        self.debug(drop_ipz)
        self.debug(client.ip)
        if client.ip not in drop_ipz:
            self.debug("IP didn't exist in iptables")
            return
        else:
            os.system("sudo iptables -D INPUT -s %s -j DROP"%client.ip)
            self.debug("Removed IP %s from iptables"%client.ip)

    def checkVpn(self,client):
        api_url1 = "https://api.xdefcon.com/proxy/check/?ip=%s"%client.ip
        api_url2 = "http://ip-api.com/json/%s?fields=status,message,country,countryCode,region,regionName,city,timezone,isp,org,proxy,hosting"%client.ip
        # api_url3 = "https://check.getipintel.net/check.php?ip=%s&contact=haha@hehe.com"%client.ip
        api_url4 = "https://ipqualityscore.com/api/json/ip/<api-key-here>/%s"%client.ip
        check1 = '**false**'
        check2 = '**false**'
        check3 = '**false**'
        check4 = '**false**'
        res1 = requests.get(api_url1).json()
        res2 = requests.get(api_url2).json()
        # res3 = requests.get(api_url3)
        count = 0
        self.debug(res1)
        self.debug(res2)
        if True:
            row = self._query("select * from discod_vpn_allowed where client_id = %s;"%client.id).getOneRow()
            if row=={} or row==None:
                if not res1["success"]:
                    check1 = "**not checked**"
                elif res1["proxy"]:
                    check1 = "**true**"
                    count+=1
                if res2["status"]!="success":
                    check2 = "**not checked**"
                elif res2["hosting"] or res2["proxy"]:
                    check2 = "**true**"
                    count+=1
                # if float(res3.content)<0:
                    # check3 = "**not checked**"
                # elif(float(res3.content)>0.75):
                    # check3 = "**true** (**%s%%**)"%(float(res3.content)*100)
                    # count+=1
                if count!=0:
                    res4 = requests.get(api_url4).json()
                    self.debug(res4)
                    if not res4["success"]:
                        check4 = "**not checked**"
                    else:
                        if res4["vpn"]:
                            check4 = "**true**"
                            count+=1
                    
            if(count == 0):
                self.debug("%s @%s got no vpn"%(client.name,client.id))
                return
            else:
                self.debug("%s @%s got vpn"%(client.name,client.id))
                embed = {
                        "title": "VPN Detected",
                        "description": "%s **@%s**\nIP: **%s**"%(client.name,client.id,client.ip),
                        "color": 0x4a1e44,
                        "fields": [
                        {
                            "name": "API Response",
                            "value": "*xdefcon:* %s\n*ip-api:* %s\n*ipqualityscore:* %s"%(check1.upper(),check2.upper(),check4.upper()),
                            "inline": False
                        },
                        {
                            "name": "ISP",
                            "value": res2["isp"],
                            "inline": True
                        },
                        {
                            "name": "Location",
                            "value": "%s, %s (%s)"%(res2["city"],res2["regionName"],res2["countryCode"]),
                            "inline": True
                        },
                        {
                            "name": "Organization",
                            "value": "%s"%(res2["org"]),
                            "inline": True
                        }
                    ]
                    }
                data = json.dumps({"embeds": [embed]})        
                req = urllib2.Request(self.webhookurl_vpn_private, data, {
                    'Content-Type': 'application/json',
                    "User-Agent": "webhook"
                })
                try:
                    urllib2.urlopen(req)
                except urllib2.HTTPError as ex:
                    self.debug("err pushing data")
                    self.debug("Data: %s\nCode: %s\nRead: %s" % (data, ex.code, ex.read()))
                
                try:
                    urllib2.urlopen(req)
                except urllib2.HTTPError as ex:
                    self.debug("err pushing data")
                    self.debug("Data: %s\nCode: %s\nRead: %s" % (data, ex.code, ex.read()))
                if count>=2:
                    self.console.write("clientkick %s VPN detected. Ask admins over discord for permission. %s"%(client.cid,self.invite_link))
                    embed = {
                            "title": "VPN Detected",
                            "description": "%s **@%s**"%(client.name,client.id)
                    }
                    data = json.dumps({"embeds": [embed]})        
                    req = urllib2.Request(self.webhookurl_vpn_public, data, {
                        'Content-Type': 'application/json',
                        "User-Agent": "webhook"
                    })
                    self.blockVpn(client)

    def autoSS(self,client):
        time.sleep(10)	
        if client.maxLevel<20:
            self.Screenshot(client,taker=None,notifycheck=False)
    
    def getCurrentPing(self,client):
        res = self.console.write("status")
        lis = [ele.split() for ele in res.split("\n")]
        ind = 0
        for ele in lis:
            try:
                if ele[0]=="num" and ele[1]=="score":
                    ind = lis.index(ele)
            except IndexError:
                continue
        for i in range(ind+2,len(lis)-1):
            try:
                if client.cid == lis[i][0]:
                    return(lis[i][lis[i].index(client.cid)+2])
            except IndexError:
                continue
    
    def getSteamID(self,client):
        res = self.console.write("status")
        lis = [ele.split() for ele in res.split("\n")]
        ind = 0
        for ele in lis:
            try:
                if ele[0]=="num" and ele[1]=="score":
                    ind = lis.index(ele)
            except IndexError:
                continue
        for i in range(ind+2,len(lis)-1):
            try:
                if client.guid in lis[i]:
                    return(lis[i][lis[i].index(client.guid)+1])
            except IndexError:
                continue
    
    def misc(self,client):
        res = self._query("select * from discod_clients_misc where client_id = %s;"%client.id).getOneRow()
        self.debug(res)
        if res=={} or res==None:
            steamid = self.getSteamID(client)
            if str(steamid) == "0":
                self._query("insert into discod_clients_misc (client_id,time_add,time_edit) values (%s,unix_timestamp(),unix_timestamp())"%(client.id))
                self.debug("inserted steam id for client %s"%client.id)
            else:
                self._query("insert into discod_clients_misc (client_id,steam_id,time_add,time_edit) values (%s,%s,unix_timestamp(),unix_timestamp())"%(client.id,steamid))
                self.debug("inserted steam id for client %s"%client.id)
        else:
            steamid = self.getSteamID(client)
            self.debug(res["steam_id"])
            self.debug(str(steamid))
            if int(res["steam_id"])==int(steamid):
                return
            else:
                if len(str(res["steam_id"]))>len(str(steamid)):
                    return False
                self._query("update discod_clients_misc set steam_id = %s, time_edit = unix_timestamp() where client_id = %s;"%(steamid,client.id))
                self.debug("updated steam id for client %s"%client.id)
        client.setvar(self,"steam_id",self._query("select * from discod_clients_misc where client_id = %s"%(client.id)).getOneRow()["steam_id"])