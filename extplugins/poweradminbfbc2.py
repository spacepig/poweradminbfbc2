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
__version__ = '0.1'
__author__  = 'Courgette'

import b3
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
    
     
##################################################################################################    
     
     
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
            
