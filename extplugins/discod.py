import b3
import b3.events
import b3.plugin
from datetime import datetime
from MySQLdb import _mysql
import functools

__version__ = "v1.0"
__author__ = "someone"
pluginInstance = None

class DiscodPlugin(b3.plugin.Plugin):

    requiresConfigFile = True

    def exceptionsHandler(f):
        @functools.wraps(f)
        def func(*args,**kwargs):
            try:
                return f(*args,**kwargs)
            except Exception as ex:
                global pluginInstance
                pluginInstance.debug("ERROR in function %s : %s"%(f.__name__,ex))
        return func

    @exceptionsHandler
    def onLoadConfig(self):
        self.debug("config loaded normal")
        self.debug("now loading config messages...")
        self.min_level = int(self.config.get("settings","minimum_level"))
        self.warn_senior = int(self.config.get("settings","warn_senior"))

        self.id_message = str(self.config.get("messages","id_message"))
        self.warn_message = str(self.config.get("messages","warn_reason"))
        self.success_message = str(self.config.get("messages","success_message"))
        self.reattempt_message = str(self.config.get("messages","reattempt_message"))
        self.notfound_message = str(self.config.get("messages","notfound_message"))
        self.linktest_message = str(self.config.get("messages","linktest_message"))
        self.linktest_pending_message = str(self.config.get("messages","linktest_pending_message"))
        self.debug("config messages and settings loaded normal")

    @exceptionsHandler
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
            try:
                self.console.storage._query("select * from discod;")
                self.debug("located discod table")
            except _mysql.ProgrammingError as ex:
                self.error("error locating `discod` table:")
                self.error(ex)

    @exceptionsHandler
    def cmd_id(self,data,client,cmd=None):
        """\
        shows the B3 ID of the given player
        """
        if not data:
            cmd.sayLoudOrPM(client, self.id_message.format(client_name = client.name, client_id = client.id))
        else:
            inp = self._adminPlugin.parseUserCmd(data)
            client2 = self._adminPlugin.findClientPrompt(inp[0],client)
            if client2:
                cmd.sayLoudOrPM(client, self.id_message.format(client_name = client2.name, client_id = client2.id))

    @exceptionsHandler
    def cmd_link(self,data,client,cmd=None):
        """\
        ^3<8-digit-pin> ^0-^7 confirm the pin to link your discord account. If you do not have any pin, head over to ^0[^3v^0.^3F^0]^3's^7 discord and type !link <b3-id>
        """
        if not data:
            client.message('^7Incorrect command syntax. ^3!link <8-digit-pin>^7 or type ^2!help link')
            return False

        cursor = self.console.storage._query("select * from discod where b3_id = %s;"%(str(client.id)))
        rows = cursor.getOneRow()
        if not rows:
            client.message(self.notfound_message)
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

    @exceptionsHandler
    def cmd_unlink(self, data, client, cmd = None):
        """\
        y - confirm unlinking your discord account
        """
        if not data:
            client.message('^7Incorrect command syntax. ^3!unlink y^7')
            return False
        if str(data) == 'y':
            cursor = self.console.storage._query("select * from discod where b3_id = %s;"%(str(client.id)))
            rows = cursor.getOneRow()
            if len(rows) == 0:
                client.message(self.notfound_message)
            else:
                self.console.storage._query("delete from discod where b3_id = %s;"%(str(client.id)))
                cmd.sayLoudOrPM(client,"Unlinked your B3 ID from discod.")
                self.debug("@%s unlinked"%(client.id))
    
    @exceptionsHandler
    def cmd_linktest(self,data,client,cmd=None):
        """\
        check whether your b3 id is linked to a discord account
        """
        if not data:
            self.getLinkStatus(client = client, cmd = cmd)
        else:
            inp = self._adminPlugin.parseUserCmd(data)
            client2 = self._adminPlugin.findClientPrompt(inp[0],client)
            if client2:
                self.getLinkStatus(client = client2, callerClient = client, cmd = cmd)
    
    @exceptionsHandler
    def getLinkStatus(self,client,callerClient=None,cmd=None):
        if not callerClient:
            callerClient = client
        cursor = self.console.storage._query("select * from discod where b3_id = %s;"%(str(client.id)))
        rows = cursor.getOneRow()
        if not rows:
            callerClient.message(self.notfound_message)
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