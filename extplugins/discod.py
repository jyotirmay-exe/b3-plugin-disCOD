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
        #loading settings
        self.create_table = int(self.config.getint("settings","create_table"))
        self.warn_senior = int(self.config.getint("settings","warn_senior"))
        self.send_eligible = int(self.config.getint("settings","send_eligible"))
        self.min_interval = int(self.config.getint("settings","minInterval"))
        self.autoPromote = int(self.config.getint("settings","auto_promote"))
        self.autoDemote = int(self.config.getint("settings","auto_demote"))
        self.invite_link = str(self.config.get("settings","invite_link"))
        self.susinterval = int(self.config.get("settings","susinterval"))

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
        
        self._adminPlugin = self.console.getPlugin('admin')
        if not self._adminPlugin:
            self.debug('Could not find admin plugin')
            return False

        # check if tables exist
        tableCheck = self.console.storage._query("SHOW TABLES like 'discod'")
        rows = tableCheck.getOneRow()
        if rows == {}:
            self.error("Required table for disCOD plugin doesn't exist")
            return False

        tableCheck = self.console.storage._query("SHOW TABLES like 'discod_reso'")
        rows = tableCheck.getOneRow()
        if rows == {}:
            self.debug("'discod_reso' table does not exist")
            self.resoTableExists = False
        else: self.resoTableExists = True

        tableCheck = self.console.storage._query("SHOW TABLES like 'demotions'")
        rows = tableCheck.getOneRow()
        if rows == {}:
            self.debug("demotions does not exist")
            self.demotionsTableExists = False
        else: self.demotionsTableExists = True

## works but cant get optional commands this way
        # if 'commands' in self.config.sections():
        #     for cmd in self.config.options('commands'):
        #         level = self.config.get('commands', cmd)
        #         sp = cmd.split('-')
        #         alias = None
        #         if len(sp) == 2: cmd, alias = sp
        #         func = self.getCmd(cmd)
        #         if func: self._adminPlugin.registerCommand(self, cmd, level, func, alias)

        self._adminPlugin.registerCommand(self, "id", self.config.get('commands', "id"), self.cmd_id )
        self._adminPlugin.registerCommand(self, "link", self.config.get('commands', "link"), self.cmd_link )
        self._adminPlugin.registerCommand(self, "linktest", self.config.get('commands', "linktest"), self.cmd_linktest )
        self._adminPlugin.registerCommand(self, "unlink", self.config.get('commands', "unlink"), self.cmd_unlink )
        if self.autoPromote:
            self._adminPlugin.registerCommand(self, "nok", self.config.get('commands', "nok"), self.cmd_nok )
        if self.resoTableExists:
            self._adminPlugin.registerCommand(self, "resolution", self.config.get('commands', "resolution"), self.cmd_resolution, "reso" )
            self._adminPlugin.registerCommand(self, "getss", self.config.get('commands', "getss"), self.cmd_getss, "ss" )    

        self.registerEvent(b3.events.EVT_CLIENT_AUTH)
        self.registerEvent(b3.events.EVT_CLIENT_DISCONNECT)

    # def getCmd(self, cmd):
    #     cmd = 'cmd_%s' % cmd
    #     if hasattr(self, cmd):
    #         func = getattr(self, cmd)
    #         return func
    #     return None

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

        cursor = self.console.storage._query("SELECT * FROM discod WHERE b3_id = %s;"%(str(client.id)))
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
                self.console.storage._query("UPDATE discod SET linked = 1, linktime = UNIX_TIMESTAMP() WHERE b3_id = %s;"%(str(client.id)))
                cursor = self.console.storage._query("SELECT dc_tag FROM discod WHERE b3_id = %s;"%(str(client.id)))
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
            cursor = self.console.storage._query("SELECT * FROM discod WHERE b3_id = %s;"%(str(client.id)))
            rows = cursor.getRow()
            if rows == {}:
                client.message(self.notfound_message.format(invite=self.invite_link))
            else:
                self.console.storage._query("DELETE FROM discod WHERE b3_id = %s;"%(str(client.id)))
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
        check = self.console.storage._query("SELECT * FROM discod_reso WHERE client_id = %s;"%(str(sclient.id)))
        row = check.getOneRow()
        if not row:
            cmd.sayLoudOrPM(client,"Don't Know.")
            self.Screenshot(sclient,client,False)
            return
        time = datetime.fromtimestamp(int(row['time_edit'])).strftime("%Y/%m/%d")
        cmd.sayLoudOrPM(client,"^2%s ^7is playing at ^3%s, last checked %s"%(sclient.name,row['reso'],time))

    def getLinkStatus(self,client,callerClient=None,cmd=None):
        if not callerClient:
            callerClient = client
        cursor = self.console.storage._query("SELECT * FROM discod WHERE b3_id = %s;"%(str(client.id)))
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
        res = self.console.storage._query("SELECT * FROM discod WHERE b3_id = %s;"%client.id).getRow()
        if res == {}:
            return False
        else:
            if res["linked"]==1: return True
            else: return False
    
    def isDemoted(self,client):
        if not self.demotionsTableExists:
            return False
        res = self.console.storage._query("SELECT * FROM demotions WHERE client_id = %s;"%client.id).getRow()
        if res == {}:
            return False
        else:
            if res["inactive"]==1: return False
            else: return True


    def getKills(self,client):
        res = self.console.storage._query("SELECT * FROM xlr_playerstats WHERE client_id = %s;"%client.id).getRow()
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
            else: break

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
        if event.type == b3.events.EVT_CLIENT_DISCONNECT:
            if client in self.screenshots:
                self.debug(self.screenshots[client])
                timediff = time.time() - self.screenshots[client]
                if timediff < self.susinterval:
                    self.console.say(self.ss_sus_announce % ("%s[^3@%s^7]" % (client.exactName,client.id), int(timediff)))
                del self.screenshots[client]
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