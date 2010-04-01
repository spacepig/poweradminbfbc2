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
#
#
#
__version__ = '0.1.1'
__author__  = 'Courgette, SpacepiG'

import b3
import b3.events
import b3.plugin
import string
import time
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


    def cmd_teams(self ,data , client, cmd=None):
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
                self.console.write(('admin.yell', 'WARNING: %s players from your team must switch team'%howManyMustSwitch, 10, 'team', bigTeam))
            if client.guid not in bigTeam:
                client.message('The other team has been notified')

    def cmd_teambalance(self, data, client=None, cmd=None):
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


    def cmd_serverinfo(self, data, client, cmd=None):
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


    def cmd_yell(self, data, client, cmd=None):
        """\
        <msg> [<seconds>]- Yell message to all players
        """
        seconds = 3 
        if client:
            if not data:
                client.message('missing paramter, try !help yell')
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
                    response = self.console.write(('admin.yell', message, seconds*1000, 'all'))
                except Bfbc2CommandFailedError, err:
                    self.error(err)
                    client.message('Error: %s' % err.response)
                    
                    
    def cmd_yellmates(self, data, client, cmd=None):
        """\
        <msg> [<seconds>]- Yell message to all players of my team
        """
        client.message('TODO: not working yet')
        pass
    
    
    def cmd_yellenemies(self, data, client, cmd=None):
        """\
        <msg> [<seconds>]- Yell message to all players of the other team
        """
        client.message('TODO: not working yet')
        pass
    
    def cmd_yellplayer(self, data, client, cmd=None):
        """\
        <msg> [<player>]- Yell message to a player
        """
        seconds = 5 
        if client:
            if not data:
                client.message('missing parameter, try !help yellplayer')
            else:
                try:
                    if len(data) == 2:
                        try:
                            player = data[1]
                        except Exception, err:
                            self.error(err)
                    message = data[0][:99] # admin.yell support 100 char max
                    response = self.console.write(('admin.yell', message, seconds*1000, player))
                except Bfbc2CommandFailedError, err:
                    self.error(err)
                    client.message('Error: %s' % err.response)

    
    def cmd_pamap(self, data, client, cmd=None):
        """\
        <map> switch to given map
        """
        if not data:
            client.message('You must supply a map to change to.')
            return
        match = self.getMapsSoundingLike(data)
        if len(match) > 1:
            client.message('Do you mean : %s' % string.join(match,', '))
            return True
        if len(match) == 1:
            mapname = match[0]
        else:
            client.message('cannot find any map like [%s].' % data)
            return False
        
        realMapName = self.getHardName(mapname)
        client.message('Changing map to %s' % mapname)
        time.sleep(1)
        
        self.console.write(('mapList.clear',))
        self.console.write(('mapList.append',realMapName))
        self.console.write(('admin.runNextLevel',))
        self.console.write(('mapList.load',))
        return True
        
    def getMapsSoundingLike(self, mapname):   
        maplist = self.getMapNames()
        data = mapname.lower()
        match = []
        if data in maplist:
            match = [data]
        else:
            for m in maplist:
                if m == data:
                    self.debug('probable map : %s', m)
                    match.append(m)
 
        if len(match) == 0:
            # suggest closest spellings
            shortmaplist = []
            for m in maplist:
                if m.find(data) != -1:
                    shortmaplist.append(m)
            if len(shortmaplist) > 0:
                #shortmaplist.sort(key=lambda map: levenshteinDistance(data, string.replace(string.replace(map.strip(), 'ut4_',''), 'ut_','')))
                self.debug("shortmaplist sorted by distance : %s" % shortmaplist)
                match = shortmaplist[:3]
            else:
                #maplist.sort(key=lambda map: levenshteinDistance(data, string.replace(string.replace(map.strip(), 'ut4_',''), 'ut_','')))
                self.debug("maplist sorted by distance : %s" % maplist)
                match = maplist[:3]
        return match
     
##################################################################################################  
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
            
