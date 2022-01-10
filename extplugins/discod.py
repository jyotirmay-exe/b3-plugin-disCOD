import b3
import b3.events
import b3.plugin
import time
import threading
from datetime import datetime
from MySQLdb import _mysql
from b3.clients import Group

pluginInstance = None

class DiscodPlugin(b3.plugin.Plugin):

    requiresConfigFile = True
    
    def onLoadConfig(self):
        f = open(".\\b3\\extplugins\\conf\\disCOD.sql")
        temp = f.read().splitlines()
        self.tableQuery = ""
        for ele in temp:
            self.tableQuery+=ele
        self.debug("config loaded normal")
        self.debug("now loading config messages...")
        #loading settings
        self.create_table = int(self.config.getint("settings","create_table"))
        self.min_level = int(self.config.getint("settings","min_level"))
        self.warn_senior = int(self.config.getint("settings","warn_senior"))
        self.send_eligible = int(self.config.getint("settings","send_eligible"))
        self.min_interval = int(self.config.getint("settings","minInterval"))
        self.autoPromote = int(self.config.getint("settings","auto_promote"))
        self.autoDemote = int(self.config.getint("settings","auto_demote"))
        self.invite_link = str(self.config.get("settings","invite_link"))

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
        
        #loading specific help docstrings for cmds
        funcs = [func for func in dir(self) if func.startswith("_") is False]
        for func in funcs:
            try:
                if func.startswith("cmd_"):
                    f1 = getattr(self,func)
                    f1.__func__.__doc__ = str(self.config.get("help",func))
            except Exception as ex:
                self.debug(ex)

        self.debug("config messages and settings loaded normal")

    def onStartup(self):
        global pluginInstance
        pluginInstance = self
    
        self._adminPlugin = self.console.getPlugin('admin')
        if not self._adminPlugin:
            self.debug('Could not find admin plugin')
            return False
        else:
            self.debug('plugin started normal')
            self._adminPlugin.registerCommand(self, "id", self.min_level, self.cmd_id)
            self.debug('[ID] command registered in the admin plugin')
            self._adminPlugin.registerCommand(self, 'link', self.min_level, self.cmd_link)
            self.debug('[LINK] command registered in the admin plugin')
            self._adminPlugin.registerCommand(self, 'unlink', self.min_level, self.cmd_unlink)
            self.debug('[UNLINK] command registered in the admin plugin')
            self._adminPlugin.registerCommand(self, 'linktest', self.min_level, self.cmd_linktest)
            self.debug('[LINKTEST] command registered in the admin plugin')
            self._adminPlugin.registerCommand(self, "nok", self.min_level, self.cmd_nok)
            self.debug('[NOK] command registered in the admin plugin')
            self.registerEvent(b3.events.EVT_CLIENT_AUTH)
            try:
                self.console.storage._query("select * from discod;")
                self.debug("located discod table")
            except _mysql.ProgrammingError as ex:
                self.error("error locating `discod` table:")
                self.error(ex)
                if self.create_table==1:
                    self.console.storage._query(self.tableQuery)
                    self.debug("created discod table as it didn't exist")
    
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

        cursor = self.console.storage._query("select * from discod where b3_id = %s;"%(str(client.id)))
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
                self.console.storage._query("update discod set linked = 1, linktime = UNIX_TIMESTAMP() where b3_id = %s;"%(str(client.id)))
                cursor = self.console.storage._query("select dc_tag from discod where b3_id = %s;"%(str(client.id)))
                rows = cursor.getOneRow()
                if rows['dc_tag']:
                    dc_tag = ""
                    for ch in rows['dc_tag']:
                        if not ch.isalnum() and not ch=="#" and not ch=="_" and not ch.isspace():
                            dc_tag+='?'
                        else:
                            dc_tag+=ch
                self.debug("@%s linked to %s"%(client.id,dc_tag))
                cmd.sayLoudOrPM(client,self.success_message.format(id = client.id, dc_tag = dc_tag))
                promotion = self.getPromotion(client=client)
                if promotion is None:
                    return
                else:
                    thread = threading.Thread(target=self.promoteClient,args=(client,promotion),)
                    thread.start()

            else:
                if linked == 1:
                    client.message(self.reattempt_message)
                else:
                    if self.warn_senior==0:
                        if client.maxLevel < 80:
                            self._adminPlugin.warnClient(client,self.warn_message)
                        else:
                            client.message(self.warn_message)
                    else:
                        self._adminPlugin.warnClient(client,self.warn_message)

    def cmd_unlink(self, data, client, cmd = None):
        if not data:
            client.message('^7Incorrect command syntax. ^3!unlink y^7')
            return False
        if str(data) == 'y':
            cursor = self.console.storage._query("select * from discod where b3_id = %s;"%(str(client.id)))
            rows = cursor.getRow()
            if rows == {}:
                client.message(self.notfound_message.format(invite=self.invite_link))
            else:
                self.console.storage._query("delete from discod where b3_id = %s;"%(str(client.id)))
                cmd.sayLoudOrPM(client,"Unlinked your B3 ID from discod.")
                self.debug("@%s unlinked"%(client.id))
     
    def cmd_linktest(self,data,client,cmd=None):
        if not data:
            self.getLinkStatus(client = client, cmd = cmd)
        else:
            inp = self._adminPlugin.parseUserCmd(data)
            client2 = self._adminPlugin.findClientPrompt(inp[0],client)
            if client2:
                self.getLinkStatus(client = client2, callerClient = client, cmd = cmd)
    
    
    def getLinkStatus(self,client,callerClient=None,cmd=None):
        if not callerClient:
            callerClient = client
        cursor = self.console.storage._query("select * from discod where b3_id = %s;"%(str(client.id)))
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
                        else:
                            dc_tag+=ch
                time = (datetime.fromtimestamp(int(rows['linktime'])).strftime("%Y/%m/%d %H:%M:%S"))
                cmd.sayLoudOrPM(callerClient,self.linktest_message.format(id=client.id, dc=dc_tag, time = time))

    def isLinked(self,client):
        res = self.console.storage._query("select * from discod where b3_id = %s;"%client.id).getRow()
        if res == {}:
            return False
        else:
            if res["linked"]==1:
                return True
            else:
                return False
    
    def isDemoted(self,client):
        try:
            res = self.console.storage._query("select * from demotions where client_id = %s;"%client.id).getRow()
            if res == {}:
                return False
            else:
                if res["inactive"]==1:
                    return False
                else:
                    return True
        except _mysql.ProgrammingError:
            #in case the demotions table doesn't exist
            return False

    def getKills(self,client):
        res = self.console.storage._query("select * from xlr_playerstats where client_id = %s;"%client.id).getRow()
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
        if ind == None:
            return False
        for i in range(ind,len(reqKills)):
            if cKills>=reqKills[i][1]:
                killsGroup = reqKills[i+1][0]
            else:
                break

        group = Group(keyword=killsGroup)

        if group.keyword != cGroup:
            newGroup = self.console.storage.getGroup(group)
            return newGroup
        else:
            return None
    
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
        if event.type == b3.events.EVT_CLIENT_AUTH:
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
                promotion = self.getPromotion(client=event.client)
                if promotion is None:
                    return
                else:
                    thread = threading.Thread(target=self.promoteClient,args=(event.client,promotion),)
                    thread.start()

    def cmd_nok(self,data,client,cmd=None):
        if data or not data:
            res = self.getNextPromotion(client)
            self.debug(res)
            if res:
                self.debug(self.reqKills[res.keyword])
                self.debug(self.getKills(client))
                killdiff = self.reqKills[res.keyword]-self.getKills(client)
                if killdiff:
                    cmd.sayLoudOrPM(client,self.config.get("responses","nok_message")%(killdiff,res.name,res.level))
                    return
            client.message("Your are not eligible for further promotion.")