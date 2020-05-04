import discord
import logging
from discord.ext import commands
import random
import logger as _logger
import asyncio
import os
import re
from time import strftime, localtime
from auth import discord_token
from discordClasses import ServerClass


LOGGER = logging.getLogger(__name__)
_logger.setupLogger(LOGGER)
LOGGER.propagate = False

BOT = commands.Bot(command_prefix="!", case_insensitive=True)

SERVERS = {}
HEARTLIST = [u"\U0001F496", u"\U0001F49B", u"\U0001F499", u"\U0001F49A"	, u"\U0001F49C", u"\U0001F493",	u"\U0001F90D", 	u"\U0001F90E", 	u"\U0001F9E1", u"\U0001F5A4"]
TIDYTIME = 3600

ROLEDICT = {"quillYetu": 651408409652101120, "quillScience": 656217581816119326, "quillDove": 706466749457104936}
IMPORTANTDICT = {"Lucky Alliance": 290576301688094721, "Quill18": 651856272723017729, "Tooth and Tale": 327848930542878730,
                 "Scotbot Haggis Hill": 442377812708556813}
AUTHORCHARLIST = ["<@!", ">"]

ACTIVITYLIST = ["Bin Weevils \U0001F3AE", "Chess... against itself \u265A", "Human Simulator 2020 \U0001F3AE", "with it's drink \U0001F943",
                "World Domination Platinum Edition \U0001F310", "you like a fiddle \U0001F3BB", "hide and seek \U0001F3C3", "the fiddle in an irish band \U0001F3BB"]


if __name__ == '__main__':
    for extension in ["discord_cogs.diceRolls", "discord_cogs.wavelink", "discord_cogs.youtube"]:
        BOT.load_extension(extension)

@BOT.event
async def on_ready():
    for server in BOT.guilds:
        SERVERS[server.name] = ServerClass(server.name)

    BOT.loop.create_task(updatePresence(BOT))
    LOGGER.info(f"Logged in as {BOT.user.name}")
    LOGGER.info(f"Connecting to channels... {', '.join([server.name for server in SERVERS.values()])}")
    for idx, server in enumerate(SERVERS.values()):
        server: ServerClass
        server.guildClass = BOT.guilds[idx]
        server.channelChat = {channel.name: [] for channel in server.guildClass.text_channels}
    SERVERS["Direct Messages"] = ServerClass("Direct Messages")
    SERVERS["Direct Messages"].channelChat = {}

    BOT.loop.create_task(saveLogs(SERVERS))

@BOT.event
async def on_message(message: discord.Message):
    if message.author.name == "ScotBot":
        logLevel = 7
    else:
        logLevel = 5
    if message.guild is None:
        if message.channel.recipient in SERVERS["Direct Messages"].channelChat:
            SERVERS["Direct Messages"].channelChat[message.channel.recipient].append(f"{strftime('%d/%m/%Y %H:%M:%S')} | {message.author.name}: {message.content}\n")
        else:
            SERVERS["Direct Messages"].channelChat[message.channel.recipient] = [f"{strftime('%d/%m/%Y %H:%M:%S')} | {message.author.name}: {message.content}\n"]
    else:
        server: ServerClass = SERVERS[message.guild.name]
        server.channelChat[message.channel.name].append(f"{strftime('%d/%m/%Y %H:%M:%S')} | {message.author.name}: {message.content}\n")
        if message.type == discord.MessageType.pins_add and message.author.name == "ScotBot":
            await asyncio.sleep(TIDYTIME)
            await message.delete()
            LOGGER.info(f"{message.guild} | {message.channel} | Removed bot pin message")

    if message.type != discord.MessageType.default:
        return
    message.content = message.clean_content
    LOGGER.log(logLevel, f"{message.guild} | {message.channel} | {message.author.name}: {message.content}")

    await BOT.process_commands(message)

@BOT.command(name="pollOpen")
async def pollOpen(ctx):
    pollOptions = ctx.message.content.split("pollOpen ")[1].split("|")
    pollOptions = [option.strip() for option in pollOptions]
    outputMessage = await ctx.send(f"A poll has been opened! Click the corresponding heart! Options: {'; '.join([f'{option} = {HEARTLIST[idx]}' for idx, option in enumerate(pollOptions)])}")
    for idx, option in enumerate(pollOptions):
        await outputMessage.add_reaction(emoji=HEARTLIST[idx])
    await outputMessage.pin()
    await asyncio.sleep(TIDYTIME)
    await outputMessage.unpin()
    LOGGER.info(f"{ctx.message.guild} | {ctx.message.channel} | Removed pinned message")

@BOT.command(name="scotbotTest")
async def scotbotTest(ctx):
    await ctx.send(f"Version 4 of me is alive and well!")
    LOGGER.info(f"{ctx.message.guild} | {ctx.message.channel} | {ctx.author.name} used '!scotbotTest'")

@BOT.command(name="dammit")
async def dammit(ctx):
    await ctx.send(f"I blame {ctx.message.content.split('dammit ')[1]}. 'cause reasons!")
    LOGGER.info(f"{ctx.message.guild} | {ctx.message.channel} | {ctx.author.name} used '!dammit'")


@BOT.event
async def on_member_join(member: discord.Member):
    generalChannel = [channel for channel in member.guild.channels if channel.name == "general"]
    server: discord.abc.GuildChannel = member.guild.get_channel(IMPORTANTDICT[member.guild.name])
    await generalChannel[0].send(f"Welcome to the {member.guild.name} discord server, {member.mention}! Please make sure to check {server.mention}, and enjoy your stay!")

@BOT.event
async def on_member_update(before, after):
    before: discord.Member
    if before.guild.name == "Quill18":
        if "Twitch Subscriber" in [role.name for role in before.roles] and "Twitch Subscriber" not in [role.name for role in after.roles]:
            await before.send("Hey there! It appears your Twitch sub to Quill18 has lapsed! If you'd like to continue to support Quill, and retain the perks that subscribing gives you, including "
                              "access to the sub-only Discord, then make sure to renew your subcription. Thanks! NOTE: This is an automated message. Please contact DeadM8 for queries")
            LOGGER.info(f"Sub lapse notification send to {before.name}")

@BOT.event
async def on_raw_reaction_add(payload: discord.RawReactionActionEvent):
    if payload.message_id == 651856904993112084:
        guild: discord.Guild = BOT.get_guild(payload.guild_id)
        user: discord.Member = guild.get_member(payload.user_id)
        newRole: discord.Role = guild.get_role(ROLEDICT[payload.emoji.name])
        if not any(role.id == newRole.id for role in user.roles):
            await user.add_roles(newRole)
            try:
                await user.send(f"Hey there! You've been added to the {newRole.name} role in the {guild.name} Discord server")
            except discord.Forbidden:
                LOGGER.info(f"{guild.name} | Unable to send DM to {user.name} - Direct Messages disabled")
            LOGGER.info(f"{guild.name} | {user.name} added to {newRole.name} role")

@BOT.event
async def on_raw_reaction_remove(payload: discord.RawReactionActionEvent):
    if payload.message_id == 651856904993112084:
        guild: discord.Guild = BOT.get_guild(payload.guild_id)
        user: discord.Member = guild.get_member(payload.user_id)
        newRole: discord.Role = guild.get_role(ROLEDICT[payload.emoji.name])
        if any(role.id == newRole.id for role in user.roles):
            await user.remove_roles(newRole)
            await user.send(f"Hey there! You've been removed from the {newRole.name} role in the {guild.name} Discord server")
            LOGGER.info(f"{guild.name} | {user.name} removed from {newRole.name} role")

async def saveLogs(servers):
    """Saves chat logs to file every 10 mins and clears chat list"""
    while True:
        for server in servers.values():
            for name, channelChat in server.channelChat.items():
                if len(channelChat) > 0:
                    month, monthAbv, year = strftime("%m", localtime()), strftime("%b", localtime()), strftime("%Y", localtime())
                    filepath = os.path.join(server.chatLogPath, str(name))
                    if not os.path.exists(filepath):
                        os.makedirs(filepath)
                    filename = os.path.join(filepath, f"{year}-{month}({monthAbv})_chat_log.txt")
                    with open(filename, "a+", encoding='utf-8') as chatFile:
                        for message in channelChat:
                            chatFile.write(f"{message}")
                    LOGGER.info(f"{server.name} | {name} | {len(channelChat)} message(s) saved to file")
                    channelChat.clear()
        await asyncio.sleep(600)

async def updatePresence(_BOT: commands.Bot):
    await _BOT.change_presence(activity=discord.Game(name=ACTIVITYLIST[random.randrange(len(ACTIVITYLIST))]))
    await asyncio.sleep(43200)

BOT.run(discord_token)
