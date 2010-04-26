#
# PowerAdmin Plugin for BigBrotherBot(B3) (www.bigbrotherbot.com)
# Copyright (C) 2008 Mark Weirath (xlr8or@xlr8or.com)
# 
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA
#
#
# CHANGELOG :
#
# 6/4/2010 - 0.1.2 -SpacepiG
# added:
# paset, paget, pamap, macyclemap, pamaprestart, pamapreload
# payell, payellteam, payellenemy, payellplayer, paversion, pasetnextmap, paident
#
# 8/4/2010 - 0.1.3 -SpacepiG
# added:
# pakill, pachangeteam
# Removed:
# pamap, pacyclemap - exist in bfbc2 parser/admin
# Modified:
# payell, payellteam, payellenemy, payellplayer
#
# 9/4/2010 - 0.1.4 -SpacepiG
# Modified:
# payell
#
# 11/4/2010 - 0.2 - Bakes
# Rewrote many of the functions to be more efficient.
#
# 12/4/2010 - 0.2.1 - Bakes
# Added:
# payellsquad
#
# 12/4/2010 - 0.2.2 - Bakes
# Modified:
# paserverinfo
# paset
# paident
#
# 19/04/2010 - 0.3 - Courgette
# * add !pamatch command that allow teams to ready up and does a count down
# * teambalancer now move players to the other team instead of just warning them.
#   It is not scheduled yet but can be run with the !pateams command for instant
#   balancing. If this works well, we'll schedule it
# * fixes to !payellteam, !payellenemies, !payellplayer, !paset, !paget, !pasetnextmap
#   !paident, !pakill, !pachangeteam, !paspectate
# 19/04/2010 - 0.3.1 - Courgette
# * merge with Bakes
# 25/04/2010 - 0.4 - Courgette
# * match mode now requires all players to type !ready
# * make sure to reset the ready state for all players when !match on 
# * add tests for match mode
# * add !parush !paconquest !pasqdm !pasqrush commands to change mod
# 26/04/2010 - 0.5 - Courgette
# * move cmd_ready to the MatchManager class
# * a player cannot unready once the match countdown started

__version__ = '0.5'
__author__  = 'Courgette, SpacepiG, Bakes'

import b3, time, re
import b3.events
import b3.plugin
import b3.parsers.bfbc2 as bfbc2
import string
from b3.parsers.bfbc2.bfbc2Connection import Bfbc2CommandFailedError

#--------------------------------------------------------------------------------------------------
class Poweradminbfbc2Plugin(b3.plugin.Plugin):

    _adminPlugin = None
    _enableTeamBalancer = None
    
    _matchmode = False
    _match_plugin_disable = []
    _matchManager = None
    
    _parseUserCmdRE = re.compile(r'^(?P<cid>[^\s]{2,}|@[0-9]+)\s?(?P<parms>.*)$')
    
    _ignoreBalancingTill = 0
    
    def startup(self):
        """\
        Initialize plugin settings
        """

        # get the admin plugin so we can register commands
        self._adminPlugin = self.console.getPlugin('admin')
        if not self._adminPlugin:
            # something is wrong, can't start without admin plugin
            self.error('Could not find admin plugin')
            return False
    
        # register our commands
        if 'commands' in self.config.sections():
            for cmd in self.config.options('commands'):
                level = self.config.get('commands', cmd)
                sp = cmd.split('-')
                alias = None
                if len(sp) == 2:
                    cmd, alias = sp
            
                func = self.getCmd(cmd)
                if func:
                    self._adminPlugin.registerCommand(self, cmd, level, func, alias)

        # do not balance on the 1st minute after bot start
        self._ignoreBalancingTill = self.console.time() + 60

        # Register our events
        self.verbose('Registering events')
        self.registerEvent(b3.events.EVT_CLIENT_TEAM_CHANGE)
        self.registerEvent(b3.events.EVT_GAME_ROUND_START)
        self.registerEvent(b3.events.EVT_CLIENT_AUTH)
        self.debug('Started')


    def getCmd(self, cmd):
        cmd = 'cmd_%s' % cmd
        if hasattr(self, cmd):
            func = getattr(self, cmd)
            return func
    
        return None


    def onLoadConfig(self):
        self.LoadTeamBalancer()
        self.LoadMatchMode()

    def LoadTeamBalancer(self):
        # TEAMBALANCER SETUP
        try:
            self._enableTeamBalancer = self.config.getboolean('teambalancer', 'enabled')
        except:
            self._enableTeamBalancer = False
            self.debug('Using default value (%s) for Teambalancer enabled', self._enableTeamBalancer)
      
    def LoadMatchMode(self):
        # MATCH MODE SETUP
        self._match_plugin_disable = []
        try:
            self.debug('pamatch_plugins_disable/plugin : %s' %self.config.get('pamatch_plugins_disable/plugin'))
            for e in self.config.get('pamatch_plugins_disable/plugin'):
                self.debug('pamatch_plugins_disable/plugin : %s' %e.text)
                self._match_plugin_disable.append(e.text)
        except:
            self.debug('Can\'t setup pamatch disable plugins because there is no plugins set in config')


##################################################################################################

    def onEvent(self, event):
        """\
        Handle intercepted events
        """
        if event.type == b3.events.EVT_CLIENT_TEAM_CHANGE:
            self.onTeamChange(event.data, event.client)
        elif event.type == b3.events.EVT_GAME_ROUND_START:
            # do not balance on the 1st minute after bot start
            self._ignoreBalancingTill = self.console.time() + 60
        elif event.type == b3.events.EVT_CLIENT_AUTH:
            self.onClientAuth(event.data, event.client)

    def cmd_pateams(self ,data , client, cmd=None):
        """\
        Make the teams balanced
        """
        if client:
            team1players, team2players = self.getTeams()
            
            # if teams are uneven by one or even, then stop here
            gap = abs(len(team1players) - len(team2players))
            if gap <= 1:
                client.message('Teams are balanced, T1: %s, T2: %s (diff: %s)' %(len(team1players), len(team2players), gap))
            else:
                self.teambalance()


    def cmd_pateambalance(self, data, client=None, cmd=None):
        """\
        <on/off> - Set teambalancer on/off
        Setting teambalancer on will warn players that make teams unbalanced
        """
        if not data:
            if client:
                if self._enableTeamBalancer:
                    client.message("team balancing is on")
                else:
                    client.message("team balancing is off")
            else:
                self.debug('No data sent to cmd_teambalance')
        else:
            if data.lower() in ('on', 'off'):
                if data.lower() == 'off':
                    self._enableTeamBalancer = False
                    client.message('Teambancer is now disabled')
                elif data.lower() == 'on':
                    self._enableTeamBalancer = True
                    client.message('Teambancer is now enabled')
            else:
                if client:
                    client.message("Invalid data, expecting 'on' or 'off'")
                else:
                    self.debug('Invalid data sent to cmd_teambalance : %s' % data)
    
    
    def cmd_runscript(self, data, client, cmd=None):
        """\
        <configfile.cfg> - Execute a server configfile.
        """
        if not data:
            client.message('missing paramter, try !help runscript')
        else:
            if re.match('^[a-z0-9_.]+.cfg$', data, re.I):
                self.debug('Executing configfile = [%s]', data)
                try:
                    response = self.console.write(('admin.runScript', '%s' % data))
                except Bfbc2CommandFailedError, err:
                    self.error(err)
                    client.message('Error: %s' % err.response)
            else:
                self.error('%s is not a valid configfile', data)


    def cmd_pb_sv_command(self, data, client, cmd=None):
        """\
        <punkbuster command> - Execute a punkbuster command
        """
        if not data:
            client.message('missing paramter, try !help pb_sv_command')
        else:
            self.debug('Executing punkbuster command = [%s]', data)
            try:
                response = self.console.write(('punkBuster.pb_sv_command', '%s' % data))
            except Bfbc2CommandFailedError, err:
                self.error(err)
                client.message('Error: %s' % err.response)


    def cmd_paserverinfo(self, data, client, cmd=None):
        """\
        get server info
        """
        data = self.console.write(('serverInfo',))
        client.message('Server Name: %s' % data[0])
        client.message('Current Players: %s' % data[1])
        client.message('Max Players: %s' % data[2])
        client.message('GameType: %s' % data[3])
        client.message('Map: %s' % self.console.getEasyName(data[4]))


    def cmd_payell(self, data, client, cmd=None):
        """\
        <msg>- Yell message to all players
        """
        if client :
            if not data:
                client.message('missing parameter, try !help payell')
                return False
            self.console.saybig('%s: %s' % (client.exactName, data))
                    
                    
    def cmd_payellteam(self, data, client, cmd=None):
        """\
        <msg> Yell message to all players of your team
        """ 
        if not data:
            client.message('missing parameter, try !help payellteam')
            return False
        for c in self.console.clients.getList():
            if c.team == client.team:
                c.messagebig(data)

    def cmd_payellsquad(self, data, client, cmd=None):
        """\
        <msg> Yell message to all players of your squad
        """ 
        if not data:
            client.message('missing parameter, try !help payellsquad')
            return False
        for c in self.console.clients.getList():
            if c.squad == client.squad and c.team == client.team:
                c.messagebig(data)
    
    
    def cmd_payellenemy(self, data, client, cmd=None):
        """\
        <msg> - Yell message to all players of the other team
        """
        if not data:
            client.message('missing parameter, try !help payellenemy')
            return False
        for c in self.console.clients.getList():
            if c.team != client.team:
                c.messagebig(data)

    def cmd_payellplayer(self, data, client, cmd=None):
        """\
        <player> <msg> - Yell message to a player
        """
        m = self._adminPlugin.parseUserCmd(data)
        if not m:
            client.message('invalid parameters, try !help payellplayer')
            return False
        cid, message = m
        sclient = self._adminPlugin.findClientPrompt(cid, client)
        if not sclient:
            return False
        sclient.messagebig(message)
        
        
    def cmd_paversion(self, data, client, cmd=None):
        """\
        This command identifies PowerAdminBFBC2 version and creator.
        """
        #client.message(message)
        cmd.sayLoudOrPM(client, 'I am PowerAdminBFBC2 version %s by %s' % (__version__, __author__))
        return None
        
    def cmd_pamaplist(self, data, client, cmd=None):
        """\
        <maplist.txt> - Load a server maplist.
        (You must use the command exactly as it is! )
        """
        if not data:
            client.message('Invalid or missing data, try !help pamaplist')
            return False
        else:
            if re.match('^[a-z0-9_.]+.txt$', data, re.I):
                self.debug('Loading maplist = [%s]', data)
                self.console.write(('mapList.load %s' % data))
            else:
                self.error('%s is not a valid maplist', data)
        
     
    def cmd_pamaprestart(self, data, client, cmd=None):
        """\
        Restart the current map.
        (You can safely use the command without the 'pa' at the beginning)
        """
        self.console.say('Restarting map')
        time.sleep(1)
        self.console.write(('admin.restartMap',))
        return True
        
    
    def cmd_pamapreload(self, data, client, cmd=None):
        """\
        Reload the current map.
        (You can safely use the command without the 'pa' at the beginning)
        """
        self.console.say('Reloading map')
        time.sleep(1)
        data = self.console.write(('admin.currentLevel',))
        self.console.write(('mapList.clear',))
        self.console.write(('mapList.append', data))
        self.console.write(('admin.runNextLevel',))
        self.console.write(('mapList.load',))
        return True
        
        
    def cmd_paset(self, data, client, cmd=None):
        """\
        <var> <value> - Set a server var to a certain value.
        (You must use the command exactly as it is! )
        """
        if client:
            if not data:
                client.message('Invalid or missing data, try !help paset')
            else:
                # are we still here? Let's write it to console
                input = data.split(' ',1)
                varName = input[0]
                value = input[1]
                try:
                    self.console.write(('vars.%s' % varName, value))
                    client.message('%s set' % varName)
                except Bfbc2CommandFailedError, err:
                    client.message('ERROR setting %s : %s' % (varName, err))



    def cmd_paget(self, data, client, cmd=None):
        """\
        <var> - Returns the value of a servervar.
        (You must use the command exactly as it is! )
        """
        if not data:
            client.message('Invalid or missing data, try !help paget')
        else:
            # are we still here? Let's write it to console
            var = data.split(' ')
            cvar = self.console.getCvar(var[0])
            client.message('%s' % cvar.value)

        
        
    def cmd_pasetnextmap(self, data, client=None, cmd=None):
        """\
        <mapname> - Set the nextmap (partial map name works)
        """
        if not data:
            client.message('Invalid or missing data, try !help setnextmap')
        else:
            match = self.console.getMapsSoundingLike(data)
            if len(match) > 1:
                client.message('do you mean : %s ?' % string.join(match,', '))
                return
            if len(match) == 1:
                levelname = match[0]
                
                currentLevelCycle = self.console.write(('mapList.list',))
                try:
                    newIndex = currentLevelCycle.index(levelname)
                    self.console.write(('mapList.nextLevelIndex', newIndex))
                except ValueError:
                    # the wanted map is not in the current cycle
                    # insert the map in the cycle
                    mapindex = self.console.write(('mapList.nextLevelIndex',))
                    self.console.write(('mapList.insert', mapindex, levelname))
                if client:
                    cmd.sayLoudOrPM(client, 'nextmap set to %s' % self.console.getEasyName(levelname))
            else:
                client.message('do you mean : %s.' % ", ".join(data))
      
      
    def cmd_paident(self, data, client, cmd=None):
        """\
        [<name>] - show the ip and guid of a player
        (You can safely use the command without the 'pa' at the beginning)
        """
        input = self.parseUserCmd(data)
        if not input:
            # assume the player wants his own ident
            try:
                cmd.sayLoudOrPM(client, '%s %s %s' % (client.cid, client.ip, client.guid))
            except Bfbc2CommandFailedError, err:
                client.message('Error, server replied %s' % err)
        else:
            try:
                # input[0] is the player id
                sclient = self._adminPlugin.findClientPrompt(input[0], client)
                if sclient:
                    cmd.sayLoudOrPM(client, '%s %s %s' % (sclient.cid, sclient.ip, sclient.guid))
            except Bfbc2CommandFailedError, err:
                client.message('Error, server replied %s' % err)
        
        
    def cmd_pakill(self, data, client, cmd=None):
        """\
        <name> <reason> - kill a player
        """
        m = self.parseUserCmd(data)
        if not m:
            client.message('Invalid data, try !help pakill')
        else:
            cid, keyword = m
            reason = self._adminPlugin.getReason(keyword)
    
            if not reason and client.maxLevel < self._adminPlugin.config.getint('settings', 'noreason_level'):
                client.message('ERROR: You must supply a reason')
            else:
                sclient = self._adminPlugin.findClientPrompt(cid, client)
                if sclient:
                    self.console.saybig('%s was terminated by server admin' % sclient.name)
                    try:
                        self.console.write(('admin.killPlayer', sclient.cid))
                        if reason:
                            self.console.say('%s was terminated by server admin for : %s' % (sclient.name, reason))
                    except Bfbc2CommandFailedError, err:
                        client.message('Error, server replied %s' % err)
     

    def cmd_pachangeteam(self, data, client, cmd=None):
        """\
        [<name>] - change a player to the other team
        """
        input = self.parseUserCmd(data)
        if not input:
            client.message('Invalid data, try !help pachangeteam')
        else:
            # input[0] is the player id
            sclient = self._adminPlugin.findClientPrompt(input[0], client)
            if sclient:
                if sclient.teamId == '1':
                    newteam = '2'
                else:
                    newteam = '1' 
                try:
                    self.console.write(('admin.movePlayer', sclient.cid, newteam, 0, 'true'))
                    cmd.sayLoudOrPM(client, '%s forced to the other team' % sclient.cid)
                except Bfbc2CommandFailedError, err:
                    client.message('Error, server replied %s' % err)
        
        
    def cmd_paspectate(self, data, client, cmd=None):
        """\
        [<name>] - move a player to spectate
        """
        input = self.parseUserCmd(data)
        if not input:
            client.message('Invalid data, try !help paspectate')
        else:
            # input[0] is the player id
            sclient = self._adminPlugin.findClientPrompt(input[0], client)
            if sclient:
                try:
                    self.console.write(('admin.movePlayer', sclient.cid, 0, 0, 'true'))
                    cmd.sayLoudOrPM(client, '%s forced to spectate' % sclient.name)
                except Bfbc2CommandFailedError, err:
                    client.message('Error, server replied %s' % err)
        
    def cmd_pamatch(self, data, client, cmd=None): 
        """\
        Set server match mode on/off
        (You can safely use the command without the 'pa' at the beginning)
        """
        if not data or str(data).lower() not in ('on','off'):
            client.message('Invalid or missing data, expecting "on" or "off"')
            return False
        else:
            if data.lower() == 'on':
                
                self._matchmode = True
                self._enableTeamBalancer = False
                
                for e in self._match_plugin_disable:
                    self.debug('Disabling plugin %s' %e)
                    plugin = self.console.getPlugin(e)
                    if plugin:
                        plugin.disable()
                        client.message('plugin %s disabled' % e)
                
                self.console.say('match mode: ON')
                if self._matchManager:
                    self._matchManager.stop()
                self._matchManager = MatchManager(self)
                self._matchManager.initMatch()

            elif data.lower() == 'off':
                self._matchmode = False
                if self._matchManager:
                    self._matchManager.stop()
                self._matchManager = None
                
                # enable plugins
                for e in self._match_plugin_disable:
                    self.debug('enabling plugin %s' %e)
                    plugin = self.console.getPlugin(e)
                    if plugin:
                        plugin.enable()
                        client.message('plugin %s enabled' % e)

                self.console.say('match mode: OFF')
                
    def _changeMode(self, data, client, cmd=None, mode=None):
        if mode is None:
            self.error('mode cannot be None')
        elif mode not in ('CONQUEST', 'RUSH', 'SQDM', 'SQRUSH'):
            self.error('invalid game mode %s' % mode)
        else:
            try:
                self.console.write(('admin.setPlaylist', mode))
                client.message('Server playlist changed to %s' % mode)
                client.message('type !map <some map> to change server mode now')
            except Bfbc2CommandFailedError, err:
                client.message('Failed to change game mode. Server replied with: %s' % err)
            
    def cmd_paconquest(self, data, client, cmd=None): 
        """\
        change server mode to CONQUEST
        """
        self._changeMode(data, client, cmd, mode='CONQUEST')
        
    def cmd_parush(self, data, client, cmd=None): 
        """\
        change server mode to RUSH
        """
        self._changeMode(data, client, cmd, mode='RUSH')
        
    def cmd_pasqdm(self, data, client, cmd=None): 
        """\
        change server mode to SQDM
        """
        self._changeMode(data, client, cmd, mode='SQDM')
        
    def cmd_pasqrush(self, data, client, cmd=None): 
        """\
        change server mode to SQRUSH
        """
        self._changeMode(data, client, cmd, mode='SQRUSH')
        
      
                
        
##################################################################################################  

    def parseUserCmd(self, cmd, req=False):
        """Parse command arguments to extract a player id as a first paramenter
        from the other params
        """
        m = re.match(self._parseUserCmdRE, cmd)

        if m:
            cid = m.group('cid')
            parms = m.group('parms')

            if req and not len(parms): return None

            if cid[:1] == "'" and cid[-1:] == "'":
                cid = cid[1:-1]

            return (cid, parms)
        else:
            return None
        
        
    def removeClantag(self, dirtyname):
        #sclient = self._adminPlugin.findClientPrompt(input[0], client)
        dirtyname = self.console.stripColors(dirtyname) 
        m = re.search('(?<=' ')\w+', dirtyname)
        return (m.group(0))
    

    def onClientAuth(self, data, client):
        #store the time of teamjoin for autobalancing purposes 
        client.setvar(self, 'teamtime', self.console.time())
        
    def onTeamChange(self, data, client):
        #store the time of teamjoin for autobalancing purposes 
        client.setvar(self, 'teamtime', self.console.time())
        self.verbose('Client variable teamtime set to: %s' % client.var(self, 'teamtime').value)
        
        if self._enableTeamBalancer:
            
            if self.console.time() < self._ignoreBalancingTill:
                return
            
            if client.team in (b3.TEAM_SPEC, b3.TEAM_UNKNOWN):
                return
            
            # get teams
            team1players, team2players = self.getTeams()
            
            # if teams are uneven by one or even, then stop here
            if abs(len(team1players) - len(team2players)) <= 1:
                return
            
            biggestteam = team1players
            if len(team2players) > len(team1players):
                biggestteam = team2players
            
            # has the current player gone contributed to making teams uneven ?
            if client.cid in biggestteam:
                self.debug('%s has contributed to unbalance the teams')
                client.message('do not make teams unbalanced')
                if client.teamId == '1':
                    newteam = '2'
                else:
                    newteam = '1' 
                try:
                    self.console.write(('admin.movePlayer', client.cid, newteam, 0, 'true'))
                except Bfbc2CommandFailedError, err:
                    self.warning('Error, server replied %s' % err)
                
                
    def teambalance(self):
        if self._enableTeamBalancer:
            # get teams
            team1players, team2players = self.getTeams()
            
            # if teams are uneven by one or even, then stop here
            gap = abs(len(team1players) - len(team2players))
            if gap <= 1:
                self.verbose('Teambalance: Teams are balanced, T1: %s, T2: %s (diff: %s)' %(len(team1players), len(team2players), gap))
                return
            
            howManyMustSwitch = int(gap / 2)
            bigTeam = 1
            smallTeam = 2
            if len(team2players) > len(team1players):
                bigTeam = 2
                smallTeam = 1
                
            self.verbose('Teambalance: Teams are NOT balanced, T1: %s, T2: %s (diff: %s)' %(len(team1players), len(team2players), gap))
            self.console.saybig('Autobalancing Teams!')

            ## we need to change team for howManyMustSwitch players from bigteam
            playerTeamTimes = {}
            clients = self.console.clients.getList()
            for c in clients:
                if c.teamId == bigTeam:
                    teamTimeVar = c.isvar(self, 'teamtime')
                    if not teamTimeVar:
                        self.debug('client has no variable teamtime')
                        c.setvar(self, 'teamtime', self.console.time())
                        self.verbose('Client variable teamtime set to: %s' % c.var(self, 'teamtime').value)
                    playerTeamTimes[c.cid] = teamTimeVar.value
            
            self.debug('playerTeamTimes: %s' % playerTeamTimes)
            sortedPlayersTeamTimes = sorted(playerTeamTimes.iteritems(), key=lambda (k,v):(v,k))
            self.debug('sortedPlayersTeamTimes: %s' % sortedPlayersTeamTimes)

            for c, teamtime in sortedPlayersTeamTimes[:howManyMustSwitch]:
                try:
                    self.debug('forcing %s to the other team' % c.cid)
                    self.console.write(('admin.movePlayer', c.cid, smallTeam, 0, 'true'))
                except Bfbc2CommandFailedError, err:
                    self.error(err)
                
                    
    def getTeams(self):
        """Return two lists containing the names of players from both teams"""
        team1players = []
        team2players = []
        for name, clientdata in self.console.getPlayerList().iteritems():
            if str(clientdata['teamId']) == '1':
                team1players.append(name)
            elif str(clientdata['teamId']) == '2':
                team1players.append(name)
        return team1players, team2players
       
################################################################################## 
import threading
class MatchManager:
    plugin = None
    _adminPlugin = None
    console = None
    playersReady = {}
    countDown = 10
    running = True
    timer = None
    countdownStarted = None
    
    def __init__(self, plugin):
        self.plugin = plugin
        self.console = plugin.console
        self._adminPlugin = self.console.getPlugin('admin')
        if not self._adminPlugin:
            # something is wrong, can't start without admin plugin
            raise Exception('Could not find admin plugin')
    
    def stop(self):
        try: self.timer.cancel()
        except: pass
        self.running = False
        self.unregisterCommandReady()
        
    def initMatch(self):
        for c in self.console.clients.getList():
            c.setvar(self.plugin, 'ready', False)
        self.countdownStarted = False
        self.registerCommandReady()
        self.console.saybig('MATCH starting soon !!')
        self.console.say('ALL PLAYERS : type !ready when you are ready')
        self.console.saybig('ALL PLAYERS : type !ready when you are ready')
        self.timer = threading.Timer(10.0, self._checkIfEveryoneIsReady)
        self.timer.start()
    
    def registerCommandReady(self):
        self._adminPlugin.registerCommand(self.plugin, 'ready', 0, self.cmd_ready)
    
    def unregisterCommandReady(self):
        # unregister the !ready command
        try:
            cmd = self._adminPlugin._commands['ready']
            if cmd.plugin == self.plugin:
                self.plugin.debug('unregister !ready command')
                del self._adminPlugin._commands['ready']
        except KeyError:
            pass
    
    def yellToClient(self, message, duration, client):
        """We need this to bypass the message queue managed by the BFBC2 parser"""
        self.console.write(('admin.yell', message, duration, 'player', client.cid))

    def _checkIfEveryoneIsReady(self):
        self.console.debug('checking if all players are ready')
        isAllPlayersReady = True
        waitingForPlayers = []
        for c in self.console.clients.getList():
            isReady = c.var(self.plugin, 'ready', False).value
            self.plugin.debug('is %s ready ? %s' % (c.cid, isReady))
            if isReady is False:
                waitingForPlayers.append(c)
                self.yellToClient('we are waiting for you. type !ready', 10000, c)
                isAllPlayersReady = False
    
        if len(waitingForPlayers) > 0 and len(waitingForPlayers) <= 6:
            self.console.say('waiting for %s' % ', '.join([c.cid for c in waitingForPlayers]))
        
        try: self.timer.cancel()
        except: pass
        
        if isAllPlayersReady is True:
            self.console.say('All players are ready, starting count down')
            self.countDown = 10
            self.countdownStarted = True
            self.timer = threading.Timer(0.9, self._countDown)
        else:
            self.timer = threading.Timer(10.0, self._checkIfEveryoneIsReady)
            
        if self.running:
            self.timer.start()

    def _countDown(self):
        self.plugin.debug('countdown: %s' % self.countDown)
        if self.countDown > 0:
            self.console.write(('admin.yell', 'MATCH STARTING IN %s' % self.countDown, 900, 'all'))
            self.countDown -= 1
            if self.running:
                self.timer = threading.Timer(1.0, self._countDown)
                self.timer.start()
        else:    
            # make sure to have a brief big text
            self.console.write(('admin.yell', 'FIGHT !!!', 6000, 'all'))
            self.console.say('Match started. GL & HF')
            self.console.write(('admin.restartMap',))
            self.stop()

    def cmd_ready(self, data, client, cmd=None): 
        """\
        Notify other teams you are ready to start the match
        """
        self.plugin.debug('MatchManager::ready(%s)' % client.cid)
        if self.countdownStarted:
            client.message('Count down already started. You cannot change your ready state')
        else:
            wasReady = client.var(self.plugin, 'ready', False).value
            if wasReady:
                client.setvar(self.plugin, 'ready', False)
                self.yellToClient('You are not ready anymore', 3000, client)
                client.message('You are not ready anymore')
            else:
                client.setvar(self.plugin, 'ready', True)
                self.yellToClient('You are now ready', 3000, client)
                client.message('You are now ready')
            self._checkIfEveryoneIsReady()





if __name__ == '__main__':
    import time
    
    from b3.fake import fakeConsole
    fakeConsole.gameName = 'bfbc2'

    from b3.fake import joe, simon, moderator, superadmin
            
    from b3.config import XmlConfigParser
    conf = XmlConfigParser()
    conf.setXml("""
    <configuration plugin="poweradminbfbc2">
        <settings name="commands">
            <set name="runscript">100</set>
            <set name="pb_sv_command-pbcmd">100</set>
            <set name="paset">100</set>
            <set name="paget">100</set>
    
            <set name="parush-rush">60</set>
            <set name="paconquest-conq">60</set>
            <set name="pasqdm-sqdm">60</set>
            <set name="pasqrush-sqru">60</set>
            
            <set name="pamaplist-maplist">60</set>
            <set name="pamaprestart-maprestart">60</set>
            <set name="pamapreload-mapreload">60</set>
            <set name="pasetnextmap-setnextmap">60</set>
    
            <set name="pachangeteam-ct">60</set>
            <set name="paspectate-spectate">60</set>
            <set name="pakill-kill">60</set>
    
            <set name="paserverinfo">40</set>
            <set name="paversion">20</set>
    
            <set name="pateambalance">40</set>
            <set name="pateams-teams">20</set>
    
            <set name="payell-yell">20</set>
            <set name="payellteam-yt">20</set>
            <set name="payellenemy-ye">20</set>
            <set name="payellplayer-yp">20</set>
            <set name="payellsquad-ys">20</set>
    
            <set name="paident-id">20</set>
    
            <!-- set match mode on/off. Will wait for teams leaders to type !ready
                and then start a count down -->
            <set name="pamatch-match">20</set>
        </settings>
    
        <settings name="teambalancer">
            <!-- on/off - if 'on' the bot will switch players making teams unbalanced -->
            <set name="enabled">off</set>
        </settings>
    
        <pamatch_plugins_disable>
            <!-- The Plugins that need to be disabled during matchmode -->
            <plugin>spree</plugin>
            <plugin>adv</plugin>
            <plugin>tk</plugin>
            <plugin>pingwatch</plugin>
        </pamatch_plugins_disable>
    </configuration>
    """)

    
    ## create an instance of the plugin to test
    p = Poweradminbfbc2Plugin(fakeConsole, conf)
    p.onStartup()

    joe.connects('Joe')
    simon.connects('Simon')
    moderator.connects('Mod')
    
    def testMatch1():
        print """-----------------------
        usual scenario"""
        moderator.says('!match on')
        time.sleep(1)
        
        joe.says('!ready')
        time.sleep(1)
    
        simon.says('!ready')
        time.sleep(1)
    
        moderator.says('!ready')
        time.sleep(15)
        p._matchManager.stop()
        
    def testMatch2():
        print """-----------------------
        joe types !ready a second time"""
        moderator.says('!match on')
        time.sleep(1)
        
        joe.says('!ready')
        time.sleep(1)
    
        simon.says('!ready')
        time.sleep(1)

        joe.says('!ready')
        time.sleep(1)
    
        moderator.says('!ready')
        time.sleep(15)
        
        p._matchManager.stop()
        
    def testMatch3():
        print """-----------------------
        moderator types !match off"""
        moderator.says('!match on')
        time.sleep(1)
        
        joe.says('!ready')
        time.sleep(1)
    
        simon.says('!ready')
        time.sleep(1)
    
        moderator.says('!match off')
        time.sleep(15)
        
        print "p._matchManager : %s" % p._matchManager

    def testMatch4():
        print """-----------------------
        moderator types !match on a second time"""
        moderator.says('!match on')
        time.sleep(1)
        
        joe.says('!ready')
        time.sleep(1)
    
        simon.says('!ready')
        time.sleep(1)
    
        moderator.says('!match on')
        time.sleep(15)
        
        joe.says('!ready')
        time.sleep(1)
    
        simon.says('!ready')
        time.sleep(12)
        
        moderator.says('!ready')
        
        time.sleep(12)
        print "p._matchManager : %s" % p._matchManager
        
        
    def testMatch5():
        print """-----------------------
        a player got kicked"""
        p.console.PunkBuster = None
        
        moderator.says('!match on')
        time.sleep(1)
        
        joe.says('!ready')
        time.sleep(1)
    
        moderator.says('!ready')
        time.sleep(15)
        
        simon.kick('AFL')
        time.sleep(30)
        p._matchManager.stop()
        
    def testMatch6():
        print """-----------------------
        a player tries to type !ready after the count down started"""
        p.console.PunkBuster = None
        
        moderator.says('!match on')
        time.sleep(1)
        
        joe.says('!ready')
        time.sleep(1)
    
        moderator.says('!ready')
        time.sleep(1)
        
        simon.says('!ready')
        time.sleep(5)
        
        simon.says('!ready')
        time.sleep(10)
        p._matchManager.stop()

    def testServerModeChange():
        superadmin.connects('Superman')
        superadmin.says('!parush')
        superadmin.says('!rush')
        superadmin.says('!pasqrush')
        superadmin.says('!pasqru')
        superadmin.says('!paconquest')
        superadmin.says('!conq')
        superadmin.says('!pasqrush')
        superadmin.says('!sqru')
        
    testMatch6()