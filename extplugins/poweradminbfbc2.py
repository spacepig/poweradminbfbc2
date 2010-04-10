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
# 9/4/2010 - 0.1.3 -SpacepiG
# Modified:
# payell
#
__version__ = '0.1.4'
__author__  = 'Courgette, SpacepiG'

import b3, time, re
import b3.events
import b3.plugin
import string
from b3.parsers.bfbc2.bfbc2Connection import Bfbc2CommandFailedError

#--------------------------------------------------------------------------------------------------
class Poweradminbfbc2Plugin(b3.plugin.Plugin):

    _adminPlugin = None
    _enableTeamBalancer = None

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

        # Register our events
        self.verbose('Registering events')
        self.registerEvent(b3.events.EVT_CLIENT_TEAM_CHANGE)
    
        self.debug('Started')


    def getCmd(self, cmd):
        cmd = 'cmd_%s' % cmd
        if hasattr(self, cmd):
            func = getattr(self, cmd)
            return func
    
        return None


    def onLoadConfig(self):
        self.LoadTeamBalancer()

    def LoadTeamBalancer(self):
        # TEAMBALANCER SETUP
        try:
            self._enableTeamBalancer = self.config.getboolean('teambalancer', 'enabled')
        except:
          self._enableTeamBalancer = False
          self.debug('Using default value (%s) for Teambalancer enabled', self._enableTeamBalancer)
      


##################################################################################################

    def onEvent(self, event):
        """\
        Handle intercepted events
        """
        if event.type == b3.events.EVT_CLIENT_TEAM_CHANGE and self._enableTeamBalancer:
            self.onTeamChange(event.data, event.client)


    def cmd_pateams(self ,data , client, cmd=None):
        """\
        Will tell the team with the higher num of players to switch
        """
        if client:
            # get teams
            team1players = []
            team2players = []
            for name, clientdata in self.console.getPlayerList():
                if str(clientdata['teamId']) == '1':
                    team1players.append(name)
                elif str(clientdata['teamId']) == '2':
                    team1players.append(name)
                    
            # if teams are unvent by one or even, then stop here
            gap = abs(len(team1players) - len(team2players))
            if gap <= 1:
                client.message('Teams are balanced')
                return
            else:
                howManyMustSwitch = int(gap / 2)
                bigTeam = 1
                if len(team2players) > len(team1players):
                    bigTeam = 2
                self.console.write(('admin.say', 'WARNING: %s players from your team must switch team'%howManyMustSwitch, 'team', bigTeam))
            if client.guid not in bigTeam:
                client.message('The other team has been notified')

    def cmd_pateambalance(self, data, client=None, cmd=None):
        """\
        <on/off> - Set teambalancer on/off
        Setting teambalancer on will warn players that make teams unbalanced
        """
        if not data:
            if client:
                client.message("Invalid parameter, expecting 'on' or 'off'")
            else:
                self.debug('No data sent to cmd_teambalance')
        else:
            if data in ('on', 'off'):
                if client:
                    client.message('Teambancer: %s' % (data))
                else:
                    self.debug('Teambancer: %s' % (data))
                if data == 'off':
                    self._enableTeamBalancer = False
                elif data == 'on':
                    self._enableTeamBalancer = True
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
        if client:
            try:
                response = self.console.write(('serverInfo',))
                client.message(str(response))
            except Bfbc2CommandFailedError, err:
                self.error(err)
                client.message('Error: %s' % err.response)


    def cmd_payell(self, data, client, cmd=None):
        """\
        <msg>- Yell message to all players
        """
        seconds = 10
        if client:
            if not data:
                client.message('missing paramter, try !help payellteam')
            else:
                try:
                    #if len(data) == 2:
                    #    try:
                    #        seconds = int(data[1])
                    #        if seconds > 60:
                    #            seconds = 60
                    #    except Exception, err:
                    #        self.error(err)
                    #message = data[0][:99] # admin.yell support 100 char max
                    response = self.console.write(('admin.yell', data, seconds*1000, 'all'))
                except Bfbc2CommandFailedError, err:
                    self.error(err)
                    client.message('Error: %s' % err.response)
                    
                    
    def cmd_payellteam(self, data, client, cmd=None):
        """\
        <msg> [<seconds>]- Yell message to all players of my team
        """
        seconds = 3 
        sclient = self._adminPlugin.findClientPrompt(input[0], client)
        myteam = self.console.getClient(sclient.cid)
        if client:
            if not data:
                client.message('missing paramter, try !help payellteam')
            else:
                try:
                    if len(data) == 2:
                        try:
                            seconds = int(data[1])
                            if seconds > 60:
                                seconds = 60
                        except Exception, err:
                            self.error(err)
                    message = data[0][:99] # admin.yell support 100 char max
                    response = self.console.write('admin.yell', message, seconds*1000, 'team', myteam[3])
                except Bfbc2CommandFailedError, err:
                    self.error(err)
                    client.message('Error: %s' % err.response)
    
    
    def cmd_payellenemy(self, data, client, cmd=None):
        """\
        <msg> [<seconds>]- Yell message to all players of the other team
        """
        client.message('TODO: not working yet')
        pass
    
    def cmd_payellplayer(self, data, client, cmd=None):
        """\
        <msg> [<player>]- Yell message to a player
        """
        seconds = 5 
        if client:
            if not data:
                client.message('missing parameter, try !help payellplayer')
            else:
                try:
                    if len(data) == 2:
                        try:
                            player = data[1]
                        except Exception, err:
                            self.error(err)
                    message = data[0][:99] # admin.yell support 100 char max
                    response = self.console.write(('admin.yell', message, seconds*1000, 'player', player))
                except Bfbc2CommandFailedError, err:
                    self.error(err)
                    client.message('Error: %s' % err.response)
        
        
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
          client.message('^7Invalid or missing data, try !help pamaplist')
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
        if not data:
            client.message('^7Invalid or missing data, try !help paset')
            return False
        else:
            # are we still here? Let's write it to console
            input = data.split(' ',1)
            varName = input[0]
            value = input[1]
            self.console.write(('vars.%s' % varName, value))

        return True

    def cmd_paget(self, data, client, cmd=None):
        """\
        <var> - Returns the value of a servervar.
        (You must use the command exactly as it is! )
        """
        if not data:
            client.message('^7Invalid or missing data, try !help paget')
            return False
        else:
            # are we still here? Let's write it to console
            getvar = data.split(' ')
            getvarvalue = self.console.getCvar(( '%s' % getvar[0],))
            client.message('%s' % getvarvalue)

        return True
        
        
    def cmd_pasetnextmap(self, data, client=None, cmd=None):
        """\
        <mapname> - Set the nextmap (partial map name works)
        """
        if not data:
            client.message('^7Invalid or missing data, try !help setnextmap')
            return False
        else:
            match = self.getMapsSoundingLike(data)
            if len(match) > 1:
                client.message('do you mean : %s ?' % string.join(match,', '))
                return True
            if len(match) == 1:
                mapname = match[0]
                realMapName = self.getHardName(mapname)
                mapindex = self.console.write(('mapList.nextLevelIndex',))
                self.console.write(('mapList.insert', mapindex, realMapName))
                if client:
                    cmd.sayLoudOrPM(client, 'nextmap set to %s' % mapname)
            else:
                client.message('cannot find any map like [%s].' % data)
                return False
      
      
    def cmd_paident(self, data, client, cmd=None):
        """\
        <name> - show the ip and guid of a player
        (You can safely use the command without the 'pa' at the beginning)
        """
        input = self._adminPlugin.parseUserCmd(data)
        if not input:
            client.message('^7Invalid data, try !help paident')
            return False
        else:
            # input[0] is the player id
            sclient = self._adminPlugin.findClientPrompt(input[0], client)
        if not sclient:
            # a player matchin the name was not found, a list of closest matches will be displayed
            # we can exit here and the user will retry with a more specific player
            return False

        cmd.sayLoudOrPM(client, ' %s %s %s' % (sclient.exactName, sclient.ip, sclient.guid))
        return True
        
        
    def cmd_pakill(self, data, client, cmd=None):
        """\
        <name> - kill a player
        """
        input = self._adminPlugin.parseUserCmd(data)
        if not input:
            client.message('^7Invalid data, try !help pakill')
            return False
        else:
            # input[0] is the player id
            sclient = self._adminPlugin.findClientPrompt(input[0], client)
        if not sclient:
            # a player matchin the name was not found, a list of closest matches will be displayed
            # we can exit here and the user will retry with a more specific player
            return False

        self.console.write(('admin.yell', '%s was terminated by server admin' % sclient.name, 3000, 'all'))
        self.console.write(('admin.killPlayer', sclient.cid))
        return True
     
     
    def cmd_pachangeteam(self, data, client, cmd=None):
        """\
        <name> - change a player to the other team
        """
        input = self._adminPlugin.parseUserCmd(data)
        newsquad = 0 
        if not input:
            client.message('^7Invalid data, try !help paident')
            return False
        else:
            # input[0] is the player id
            sclient = self._adminPlugin.findClientPrompt(input[0], client)
            myteam = self.console.getClient(sclient.cid)
            if myteam.team == '1':
                newteam = '2'
            else:
                newteam = '1' 
            client.message(' Old teamid: %s ' % myteam.team)
        if not sclient:
            # a player matchin the name was not found, a list of closest matches will be displayed
            # we can exit here and the user will retry with a more specific player
            return False
     
        self.console.write(('admin.movePlayer', sclient.cid, newteam, newsquad, 'true'))
        cmd.sayLoudOrPM(client, ' Changed team for player: %s' % (sclient.name))
        return True
        
        
    def cmd_paspectate(self, data, client, cmd=None):
        """\
        <name> - move a player to spectate
        """
        input = self._adminPlugin.parseUserCmd(data)
        newsquad = '0' 
        newteam = '0'
        if not input:
            client.message('^7Invalid data, try !help paident')
            return False
        else:
            # input[0] is the player id
            sclient = self._adminPlugin.findClientPrompt(input[0], client)
            myteam = self.console.getClient(sclient.cid)   
        if not sclient:
            # a player matchin the name was not found, a list of closest matches will be displayed
            # we can exit here and the user will retry with a more specific player
            return False
        
        self.console.write(('admin.movePlayer', sclient.cid, newteam, newsquad, 'true'))
        cmd.sayLoudOrPM(client, ' Moved player: %s to spectate' % (sclient.name))
        return True        
        
##################################################################################################  
    def removeClantag(self, dirtyname):
        #sclient = self._adminPlugin.findClientPrompt(input[0], client)
        dirtyname = self.console.stripColors(dirtyname) 
        m = re.search('(?<=' ')\w+', dirtyname)
        return (m.group(0))
    
    
    
    def getHardName(self, mapname):
        """ Change real name to level name """
        
        if mapname.startswith('panama canal'):
            return 'Levels/MP_001'
            
        elif mapname.startswith('val paraiso'):
            return 'Levels/MP_002'

        elif mapname.startswith('laguna alta'):
            return 'Levels/MP_003'

        elif mapname.startswith('isla inocentes'):
            return 'Levels/MP_004'

        elif mapname.startswith('atacama desert'):
            return 'Levels/MP_005'

        elif mapname.startswith('arica harbor'):
            return 'Levels/MP_006'

        elif mapname.startswith('white pass'):
            return 'Levels/MP_007'

        elif mapname.startswith('nelson bay'):
            return 'Levels/MP_008'

        elif mapname.startswith('laguna preza'):
            return 'Levels/MP_009'

        elif mapname.startswith('port valdez'):
            return 'Levels/MP_012'
        
        else:
            self.warning('unknown level name \'%s\'. Please report this on B3 forums' % mapname)
            return mapname
  
    def getEasyName(self, mapname):
        """ Change levelname to real name """
        if mapname.startswith('Levels/MP_001'):
            return 'panama canal'
            
        elif mapname.startswith('Levels/MP_002'):
            return 'valparaiso'

        elif mapname.startswith('Levels/MP_003'):
            return 'laguna alta'

        elif mapname.startswith('Levels/MP_004'):
            return 'isla inocentes'

        elif mapname.startswith('Levels/MP_005'):
            return 'atacama desert'

        elif mapname.startswith('Levels/MP_006'):
            return 'arica harbor'

        elif mapname.startswith('Levels/MP_007'):
            return 'white pass'

        elif mapname.startswith('Levels/MP_008'):
            return 'nelson bay'

        elif mapname.startswith('Levels/MP_009'):
            return 'laguna preza'

        elif mapname.startswith('Levels/MP_012'):
            return 'port valdez'
        
        else:
            self.warning('unknown level name \'%s\'. Please report this on B3 forums' % mapname)
            return mapname

    def getMapNames(self):
        """Return the map list
        """
        data = self.console.write(('mapList.list',))
        mapList = []
        for map in data:
            mapList.append(self.getEasyName(map))
        return mapList 
     
    def onTeamChange(self, data, client):
        """
        will give a warning to the player if he goes to the team with 
        the most players
        """
        
        # get teams
        team1players = []
        team2players = []
        for name, clientdata in self.console.getPlayerList():
            if str(clientdata['teamId']) == '1':
                team1players.append(name)
            elif str(clientdata['teamId']) == '2':
                team1players.append(name)
        
        # if teams are uneven by one or even, then stop here
        if abs(len(team1players) - len(team2players)) <= 1:
            self.debug("not making teams uneven")
            return
        
        biggestteam = team1players
        if len(team2players) > len(team1players):
            biggestteam = team2players
        
        # has the current player gone contributed to making teams uneven ?
        if client.guid in biggestteam:
            self.debug('%s has contributed to unbalance the teams')
            self._adminPlugin.warnClient(client, 'Do not make teams unbalanced !')
            
