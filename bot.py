#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import random
import re
import asyncio
import aiohttp
from collections import deque
import discord
import time
from pytz import timezone
import pytz
from discord import Game
from discord import message
from discord import ChannelType
from discord.ext import commands
from discord.ext.commands import Bot
from datetime import datetime

from src.config import secret_token, session, enabled_cmds
import src.generate.letmein as letmeingen
from src.formatter import BetterHelpFormatter
from src.smart_message import smart_message
from src.smart_command import smart_command
from src.list_embed import list_embed, dank_embed
from src.models import User, Admin, Command
from src.smart_player import smart_player
from src.commands.quote_command import quote_command

BOT_PREFIX = ("?", "!")
TOKEN = secret_token

PECHS_ID = '178700066091958273'
JOHNYS_ID = '214037134477230080'
MATTS_ID = '168722115447488512'
SIMONS_ID = '103027947786473472'
MONKEYS_ID = '189528269547110400'
RYTHMS_ID = '235088799074484224'


ROLES_DICT = {
    "black santa" : "🎅🏿",
    "whale" : "🐋",
    "fox" : "🦊",
    "pink" : "pink",
    "back on top soon" : "🔙🔛🔝🔜",
    "nsfw" : "nsfw",
    "pugger" : "pugger"
}

DEFAULT_ROLE = 'Admin'

smart_commands = {}
karma_dict = {}
admins = {}
tracked_messages = deque([], maxlen=20)
deletable_messages = []
starboarded_messages = []

AUT_EMOJI = "🅱"
NORM_EMOJI = "reee"
NICE_EMOJI = "❤"
TOXIC_EMOJI = "pech"
EDIT_EMOJI = "📝"
STAR_EMOJI = "⭐"

players = {}
from discord.ext.commands.formatter import HelpFormatter
client = Bot(command_prefix=BOT_PREFIX)#, formatter=HelpFormatter)
#client.remove_command('help')

@client.command(name='skip',
                description="Skip current song",
                brief="skip song",
                pass_context=True)
@commands.cooldown(1, 1, commands.BucketType.server)
async def skip(context):
    if ctx.message.channel.server.get_member(RYTHMS_ID): return
    player = players[context.message.channel.server.id]
    name = await player.skip()
    if (name):
        await client.send_message(context.message.channel, "Now playing: " + name)
    else:
        await client.send_message(context.message.channel, "No songs left. nice job. bye.")
        if (player.is_connected()):
            await player.voice.disconnect()

@client.command(name='pause',
                description="Pauses current song",
                brief="pause song",
                aliases=['stop'],
                pass_context=True)
async def pause(context):
    if ctx.message.channel.server.get_member(RYTHMS_ID): return
    player = players[context.message.channel.server.id]
    player.pause()

@client.command(name='clear',
                description="Remove all songs from queue.",
                brief="clear queue",
                pass_context=True)
async def clear(context):
    if ctx.message.channel.server.get_member(RYTHMS_ID): return
    player = players[context.message.channel.server.id]
    await client.send_message(context.message.channel, "Removed %d songs from queue." % len(player.q))
    player.clearq()

@client.command(name='resume',
                description="Resume current song",
                brief="resume song",
                pass_context=True)
async def resume(context):
    if ctx.message.channel.server.get_member(RYTHMS_ID): return
    player = players[context.message.channel.server.id]
    player.resume()


@client.command(name='play',
                description="![play|add] [url|search]",
                brief="play tunes",
                aliases=['add'],
                pass_context=True)
@commands.cooldown(1, 2, commands.BucketType.server)
async def play(ctx):
    if ctx.message.channel.server.get_member(RYTHMS_ID): return
    await enabled_cmds['play'].execute(ctx, client, players=players)

@client.command(name='8ball',
                description="Answers a yes/no question.",
                brief="Answers from the beyond.",
                aliases=['eight_ball', 'eightball', '8-ball'],
                pass_context=True)
async def eight_ball(context):
    possible_responses = [
        'That is a resounding no',
        'It is not looking likely',
        'Too hard to tell',
        'It is quite possible',
        'Definitely',
        'Yep.',
        'Possibly.'
    ]
    await client.say(random.choice(possible_responses) + ", " + context.message.author.mention)

@client.command(pass_context=True)
async def quote(ctx):
    await enabled_cmds['quote'].execute(ctx, client)


@client.event
async def on_server_join(server):
    players[server.id] = smart_player()
    admins[int(server.id)] = [int(server.owner.id)]
    smart_commands[int(server.id)] = []

@client.event
async def on_message_delete(message):
    # if (message.author.id == PECHS_ID):
    if not is_me(message) and message.id not in deletable_messages:
        est = get_datetime(message.timestamp)
        em = discord.Embed(title=est.strftime("%Y-%m-%d %I:%M %p"), description=message.content, colour=0xff002a)
        em.set_author(name=message.author.display_name, icon_url=message.author.avatar_url)
        if message.embeds:
            em.set_image(url=message.embeds[0]['url'])
        elif message.attachments:
            em.set_image(url=message.attachments[0]['url'])
        del_msg = await client.send_message(message.channel, embed=em)
        for sm in tracked_messages:
            if (sm.peek().id == message.id):
                sm.embed = del_msg
    else:
        if message.id in deletable_messages:
            deletable_messages.remove(message.id)

@client.event
async def on_message_edit(before, after):
    server = before.channel.server
    print('<%s>[%s](%s) - [%s](%s) %s(%s): %s CHANGED TO:' % (datetime.now(), server.name, server.id, before.channel.name, before.channel.id, before.author.display_name, before.author.id, before.content))
    print('<%s>[%s](%s) - [%s](%s) %s(%s): %s' % (datetime.now(), server.name, server.id, after.channel.name, after.channel.id, after.author.display_name, after.author.id, after.content))
    for sm in tracked_messages:
        if (sm.add_edit(before, after)):
            await edit_popup(before)
            return
    sm = smart_message(before)
    sm.add_edit(before, after)
    tracked_messages.append(sm)

@client.event
async def on_reaction_add(reaction, user):
    author = reaction.message.author
    for e in reaction.message.embeds:
        author_name, author_avatar = '',''
        try:
            author_name = e['author']['name']
            author_avatar = e['author']['icon_url']
        except:
            pass # not the type of embed we were expecting
        real_author = find_member(author_name, author_avatar, reaction.message.channel.server)
        if (real_author != None):
            author = real_author

    if (str(reaction.emoji) == EDIT_EMOJI or (reaction.custom_emoji and reaction.emoji.name == EDIT_EMOJI)):
        await add_popup(reaction.message)

    #if (str(reaction.emoji) == GULAG_EMOJI or (reaction.custom_emoji and reaction.emoji.name == GULAG_EMOJI)):
        #if reaction.count > 3
        #await add_popup(reaction.message)

    if (str(reaction.emoji) == STAR_EMOJI or (reaction.custom_emoji and reaction.emoji.name == STAR_EMOJI)):
        if reaction.count == 5:
            await starboard_post(reaction.message, reaction.message.channel.server)

    if ((author != user or user.id == JOHNYS_ID or user.id == MATTS_ID) and author != client.user and user != client.user):
        if (author.id not in karma_dict):
            karma_dict[author.id] = [2,2,2,2]
            new_user = User(author.id, karma_dict[author.id])
            session.add(new_user)

        if (str(reaction.emoji) == AUT_EMOJI or (reaction.custom_emoji and reaction.emoji.name == AUT_EMOJI)):
            karma_dict[author.id][0] += 1
        elif (str(reaction.emoji) == NORM_EMOJI or (reaction.custom_emoji and reaction.emoji.name == NORM_EMOJI)):
            karma_dict[author.id][1] += 1
        elif (str(reaction.emoji) == NICE_EMOJI or (reaction.custom_emoji and reaction.emoji.name == NICE_EMOJI)):
            karma_dict[author.id][2] += 1
        elif (str(reaction.emoji) == TOXIC_EMOJI or (reaction.custom_emoji and reaction.emoji.name == TOXIC_EMOJI)):
            karma_dict[author.id][3] += 1
        update_user(author.id)

@client.event
async def on_reaction_remove(reaction, user):
    author = reaction.message.author
    for e in reaction.message.embeds:
        try:
            author_name = e['author']['name']
            author_avatar = e['author']['icon_url']
        except:
            pass
        real_author = find_member(author_name, author_avatar, reaction.message.channel.server)
        if (real_author != None):
            author = real_author

    if (str(reaction.emoji) == EDIT_EMOJI or (reaction.custom_emoji and reaction.emoji.name == EDIT_EMOJI)):
        for react in reaction.message.reactions:
            if (str(reaction.emoji) == EDIT_EMOJI or (reaction.custom_emoji and reaction.emoji.name == EDIT_EMOJI)):
                return
        await delete_popup(reaction.message)

    if ((author != user or user.id == JOHNYS_ID) and author != client.user):
        if (author.id not in karma_dict):
            karma_dict[author.id] = [2,2,2,2]
            new_user = User(author.id, karma_dict[author.id])
            session.add(new_user)
        if (str(reaction.emoji) == AUT_EMOJI or (reaction.custom_emoji and reaction.emoji.name == AUT_EMOJI)):
            karma_dict[author.id][0] -= 1
        elif (str(reaction.emoji) == NORM_EMOJI or (reaction.custom_emoji and reaction.emoji.name == NORM_EMOJI)):
            karma_dict[author.id][1] -= 1
        elif (str(reaction.emoji) == NICE_EMOJI or (reaction.custom_emoji and reaction.emoji.name == NICE_EMOJI)):
            karma_dict[author.id][2] -= 1
        elif (str(reaction.emoji) == TOXIC_EMOJI or (reaction.custom_emoji and reaction.emoji.name == TOXIC_EMOJI)):
            karma_dict[author.id][3] -= 1

        update_user(author.id)


@client.command(name='check',
        description="See how autistic one person is",
        brief="check up on one person",
        aliases=[],
        pass_context=True)
async def check(context):
    await client.send_typing(context.message.channel)
    for member in context.message.mentions:
        if (member == client.user):
            await client.send_message(context.message.channel, "Leave me out of this, " + context.message.author.mention)
            return
        if (member.id not in karma_dict):
            karma_dict[member.id] = [2,2,2,2]
            new_user = User(member.id, karma_dict[member.id])
            session.add(new_user)
        response = member.display_name + " is "
        response += ("{:3.1f}% autistic".format(get_autism_percent(member.id)) if (get_autism_percent(member.id) >= get_normie_percent(member.id)) else "{:3.1f}% normie".format(get_normie_percent(member.id)))
        response += " and " + ("{:3.1f}% toxic.".format(get_toxc_percent(member.id)) if (get_toxc_percent(member.id) >= get_nice_percent(member.id)) else "{:3.1f}% nice.".format(get_nice_percent(member.id)))
        await client.send_message(context.message.channel, response)

@client.command(name='letmein',
        description="!letmein [thing] [@user]",
        brief="meme",
        pass_context=True)
async def letmein(ctx):
    args = ctx.message.content.split(' ')
    del args[0]
    del args[len(args) - 1]
    letmeingen.generate(ctx.message.mentions[0].display_name, ' '.join(args))
    with open('res/meme.png', 'rb') as f:
        await client.send_file(ctx.message.channel, f, content="Here you go, " + ctx.message.author.mention)


@client.command(pass_context=True)
async def test(context):
    if (message.author.id != JOHNYS_ID):
        await client.send_message(context.message.channel, "it works")
        return
    lem = list_embed('https://giphy.com/gifs/vv41HlvfogHAY', context.message.channel.mention, context.message.author)
    await client.send_message(context.message.channel, embed=lem.get_embed())

    emojis = client.get_all_emojis()
    for emoji in emojis:
        if (emoji.name == 'reee'):
            NORM_EMOJI_OBJ = str(emoji)
        elif (emoji.name == 'pech'):
            TOXIC_EMOJI_OBJ = str(emoji)

    await client.send_message(context.message.channel, context.message.channel.id)
    await client.send_message(context.message.channel, ":heart:")
    await client.send_message(context.message.channel, next(client.get_all_emojis()))
    await client.send_message(context.message.channel, NORM_EMOJI_OBJ)


@client.command(name='remove',
        description="Remove users from the spectrum if they are a sad boi",
        brief="Remove user from the spectrum",
        aliases=[],
        pass_context=True)
async def remove(context):
    server = context.message.channel.server
    for member in context.message.mentions:
        if (member.id in karma_dict):
            karma_dict.pop(member.id)
            update_admin(member, server, delete=True)
            await client.send_message(context.message.channel, member.mention + " has been removed")

def find_member(name, icon, server):
    for m in server.members:
        if (name == m.display_name and icon == m.avatar_url):
            return m
    return None

def get_datetime(timestamp):
    utc = timestamp.replace(tzinfo=timezone('UTC'))
    est = utc.astimezone(timezone('US/Eastern'))
    return est

def get_channel_by_name(server, name):
    channels = []
    for channel in server.channels:
        if channel.name.lower() == name.lower() and channel.type == ChannelType.text:
            channels.append(channel)
    return channels

def is_me(m):
    return m.author == client.user

def get_autism_percent(m):
    if (karma_dict[m][0] + karma_dict[m][1] == 0):
        return 
    return ((karma_dict[m][0] - karma_dict[m][1]) / (karma_dict[m][0] + karma_dict[m][1])) * 100
def get_normie_percent(m):
    if (karma_dict[m][0] + karma_dict[m][1] == 0):
        return 0
    return ((karma_dict[m][1] - karma_dict[m][0]) / (karma_dict[m][1] + karma_dict[m][0])) * 100
def get_nice_percent(m):
    if (karma_dict[m][2] + karma_dict[m][3] == 0):
        return 0
    return ((karma_dict[m][2] - karma_dict[m][3]) / (karma_dict[m][2] + karma_dict[m][3])) * 100
def get_toxc_percent(m):
    if (karma_dict[m][2] + karma_dict[m][3] == 0):
        return 0
    return ((karma_dict[m][3] - karma_dict[m][2]) / (karma_dict[m][3] + karma_dict[m][2])) * 100


@client.command(name='spectrum',
        description="Vote :pech: for toxic, 🅱️for autistic, ❤ for nice, and :reee: for normie." ,
        brief="Check if autistic.",
        aliases=[],
        pass_context=True)
@commands.cooldown(1, 5, commands.BucketType.server)
async def spectrum(ctx):
    await enabled_cmds['spectrum'].execute(ctx, client, karma_dict=karma_dict)


@client.command(name='purge',
                description="Deletes the bot's spam.",
                brief="Delete spam.",
                pass_context=True)
@commands.cooldown(1, 5, commands.BucketType.server)
async def purge(context):
    channel = context.message.channel
    await client.send_typing(channel)
    if (int(context.message.author.id) in admins[int(channel.server.id)]):
        deleted = await client.purge_from(context.message.channel, limit=100, check=is_me)
        await client.send_message(channel, 'Deleted {} message(s)'.format(len(deleted)))
    else:
        await client.send_message(channel, 'lul %s' % context.message.author.mention)

@client.event
async def on_member_join(member):
    if member.server.id != '416020909531594752':
        return
    try:
        await client.add_roles(member, next(filter(lambda role: role.name == DEFAULT_ROLE, member.server.role_hierarchy)))
    except:
        print("could not add %s to %s" % (member.display_name, DEFAULT_ROLE))

@client.command(name='role',
                description="`!role list` for list of available roles",
                brief="Assign a role.",
                aliases=['join', 'rank'],
                pass_context=True)
async def role(ctx):
    if ctx.message.channel.server.id != '416020909531594752':
        await client.send_message(ctx.message.channel, 'Not implemented for this server yet')
        return
    await enabled_cmds['role'].execute(ctx, client, ROLES_DICT=ROLES_DICT)

@client.command(pass_context=True)
async def admin(context):
    server = context.message.channel.server
    if ("remove" in context.message.content and context.message.author.id == server.owner.id):
        for member in context.message.mentions:
            if (member == context.message.author):
                await client.send_message(context.message.channel, "🤔")
                return
            update_admin(member, server, delete=True)
            admins[int(server.id)].remove(int(member.id))
            await client.send_message(context.message.channel, "Removed %s." % member.display_name)
        return

    if ("list" in context.message.content):
        print("serverid: " +server.id);
        print(admins)
        names = ''
        for userid in admins[int(server.id)]:
            names += (server.get_member(str(userid))).display_name + ' '
        await client.send_message(context.message.channel, names)
        return
    if (context.message.author.id == server.owner.id):
        for member in context.message.mentions:
            admins.setdefault(int(server.id), [])
            if (member.id not in admins[int(server.id)]):
                new_admin = Admin(server.id, member.id, member.name)
                session.add(new_admin)
                admins[int(server.id)].append(int(member.id))
                update_admin(member, server)
                await client.send_message(context.message.channel, "Added %s." % member.display_name)
    else:
        await client.send_message(context.message.channel, "Nice try. You have been reported.")

#@client.command(pass_context=True)
async def log(context):
    await client.send_typing(context.message.channel)
    msgs = []
    do_filter = bool(context.message.mentions)
    try:
        num = int(re.search(r'\d+', context.message.content).group())
    except:
        num = 0
    num = 25 if num == 0 or num > 25 else num
    author = client.user

    em = discord.Embed(title='Last %s messages' % (str(num)), description='My Embed Content.', colour=0x5998ff)
    if (do_filter):
        author = context.message.mentions[0]
    lembed = list_embed('Last %s messages' % (str(num)), 'here you go', author)
    async for message in client.logs_from(context.message.channel, limit=1000):
        if (not do_filter or message.author == context.message.mentions[0]):
            msgs.append(message)
        if (len(msgs) >= num):
            break
    for message in reversed(msgs):
        lembed.add(author.display_name, message.content)
    await client.send_message(context.message.channel, embed=lembed.get_embed())

@client.command(pass_context=True,
                description="!set trigger::response - use [adj], [adv], [noun], [member], [owl], [comma,separted items], [author], [capture], [count], or [:<react>:] in your response.  Set response to 'remove' to remove.",
                brief="create custom command")
async def set(ctx):
    await enabled_cmds['set'].execute(ctx, client, session=session, smart_commands=smart_commands, admins=admins)

@client.event
async def on_message(message):
    server = message.channel.server
    url = message.embeds[0]['url'] if message.embeds else ''
    url = message.attachments[0]['url'] if message.attachments else ''
    print('<%s>[%s](%s) - [%s](%s) %s(%s): %s <%s>' % (datetime.now(), server.name, server.id, message.channel.name, message.channel.id, message.author.display_name, message.author.id, message.content, url))
    if 'gfycat.com' in message.content or 'clips.twitch' in message.content and not message.author.bot:
        if message.channel in get_channel_by_name(server, 'general'):
            parser = re.compile('(clips\.twitch\.tv\/|gfycat\.com\/)([^ ]+)', re.IGNORECASE)
            match = parser.search(message.content)
            if match:
                highlights = get_channel_by_name(server, 'highlights')[0]
                url = 'https://' + match.group(1) + match.group(2)
                await client.send_message(highlights, url)

    if not message.author.bot:
        await client.process_commands(message)
        for command in smart_commands[int(message.channel.server.id)]:
            if (command.triggered(message.content)):
                resp = command.generate_response(message.author, message.content)
                update_command(command.raw_trigger, command.raw_response, command.count, command.server, command.author_id)
                reacts = command.generate_reacts()
                if resp:
                    await client.send_message(message.channel, resp)
                for react in reacts:
                    await client.add_reaction(message, react)
                break

async def edit_popup(message):
    for sm in tracked_messages:
        if (message.id == sm.peek().id or (sm.embed != None and message.id == sm.embed.id)):
            if (not sm.has_popup()):
                return
            else:
                lem = sm.add_popup()
                await client.edit_message(sm.popup, embed=lem)
async def add_popup(message):
    for sm in tracked_messages:
        if (message.id == sm.peek().id or (sm.embed != None and message.id == sm.embed.id)):
            if (not sm.has_popup()):
                lem = sm.add_popup()
                popup = await client.send_message(message.channel, embed=lem)
                sm.popup = popup
            else:
                await edit_popup(message)

async def delete_popup(message):
    for sm in tracked_messages:
        if (message.id == sm.peek().id):
            if (sm.has_popup()):
                await client.delete_message(sm.popup)
                sm.popup = None

async def starboard_post(message, server):
    starboard_ch = get_channel_by_name(server, 'starboard')
    if message.id in starboarded_messages or not starboard_ch or is_me(message):
        return
    starboarded_messages.append(message.id)
    est = get_datetime(message.timestamp)
    em = discord.Embed(title=est.strftime("%Y-%m-%d %I:%M %p"), description=message.content, colour=0x42f468)
    em.set_author(name=message.author.display_name, icon_url=message.author.avatar_url)
    #print(message.embeds)
    #print(message.attachments)
    if message.embeds:
        em.set_image(url=message.embeds[0]['url'])
    elif message.attachments:
        em.set_image(url=message.attachments[0]['url'])
    await client.send_message(starboard_ch[0], embed=em)

@client.event
async def on_ready():
    initialize_players()
    initialize_scores()
    initialize_admins()
    initialize_commands()
    print("Logged in as " + client.user.name)
    await client.change_presence(game=Game(name="the tragedy of darth plagueis the wise", url='https://www.twitchquotes.com/copypastas/2202', type=2))

async def list_servers():
    await client.wait_until_ready()
    while not client.is_closed:
        print("Current servers:")
        for server in client.servers:
            print("%s - %s" % (server.name, server.id))
        await asyncio.sleep(600)

def initialize_players():
    for server in client.servers:
        players[server.id] = smart_player(client)

def initialize_admins():
    admin_list = session.query(Admin).all()
    for server in client.servers:
        admins[int(server.id)] = [int(server.owner.id)]
        admins[int(server.id)].append(int(JOHNYS_ID))
    for admin in admin_list:
        admins.setdefault(admin.server_id, [])
        admins[admin.server_id].append(admin.discord_id)

def initialize_roles():
    role_list = session.query(Role).all()
    for server in client.servers:
        roles.setdefault(int(server.id), [])
    for role in role_list:
        roles.setdefault(role.server_id, [])
        roles[role.server_id].append((role.target_role_id, role.required_role_id))

def initialize_scores():
    users = session.query(User).all()
    for user in users:
        karma_dict[user.discord_id] = user.as_entry()

def initialize_commands():
    command_list = session.query(Command).all()
    for server in client.servers:
        smart_commands.setdefault(int(server.id), [])
    for command in command_list:
        smart_commands.setdefault(command.server_id, [])
        smart_commands[command.server_id].append(smart_command(command.trigger.replace(str(command.server_id), '', 1), command.response, command.count, client.get_server(str(command.server_id)), command.author_id))
    for server, cmds in smart_commands.items():
        smart_commands[server].sort()

def update_role(target_role_id, server_id, required_role_id=None, delete=False):
    if (delete):
        session.query(Role).filter_by(target_role_id = target_role_id).delete()
        session.commit()
        return
    new_data = {
            'server_id': server_id,
            'required_role_id': required_role_id
            }
def update_user(disc_id, delete=False):
    if (delete):
        session.query(User).filter_by(discord_id = disc_id).delete()
        session.commit()
        return
    new_data = {
            'aut_score': karma_dict[disc_id][0],
            'norm_score': karma_dict[disc_id][1],
            'nice_score': karma_dict[disc_id][2],
            'toxic_score': karma_dict[disc_id][3]
            }
    session.query(User).filter_by(discord_id = disc_id).update(new_data)
    session.commit()

def update_admin(member, server, delete=False):
    if (delete):
        session.query(Admin).filter_by(discord_id = member.id).delete()
        session.commit()
        return
    new_data = {
            'server_id': server.id,
            'username': member.name
            }
    session.query(Admin).filter_by(discord_id = member.id).update(new_data)
    session.commit()

def update_command(triggerkey, response, count, server, author_id, delete=False):
    if (delete):
        session.query(Command).filter_by(trigger = server.id + triggerkey).delete()
        session.commit()
        return
    new_data = {
            'server_id': server.id,
            'response': response,
            'count': count,
            'author_id': int(author_id)
            }
    session.query(Command).filter_by(trigger = server.id + triggerkey).update(new_data)
    session.commit()

client.loop.create_task(list_servers())
client.run(TOKEN)
