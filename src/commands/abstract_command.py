import discord
from discord import ChannelType
from pytz import timezone
import pytz
 
class abstract_command():
 
    def __init__(self, name, aliases=[]): 
        self.name = name
        self.aliases = aliases
        super().__init__()

    async def execute(self, context, client, **kwargs):
        self.context = context
        self.client = client
        self.message = context.message
        self.content = self.message.content
        self.args = self.content.split(' ')
        self.channel = self.message.channel
        self.server = self.message.channel.server
        self.author = self.message.author
        await self.exec_cmd(**kwargs)
   
    def get_aliases(self):
        return [self.name] + aliases

    def get_help(self):
        raise NotImplementedError

    def get_usage(self):
        raise NotImplementedError

    async def exec_cmd(self, **kwargs):
        raise NotImplementedError

    def get_datetime(self, timestamp):
        utc = timestamp.replace(tzinfo=timezone('UTC'))
        est = utc.astimezone(timezone('US/Eastern'))
        return est

    def get_channel_by_name(self, server, name):
        channels = []
        for channel in server.channels:
            if channel.name.lower() == name.lower() and channel.type == ChannelType.text:
                channels.append(channel)
        return channels
