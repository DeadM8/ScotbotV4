"""ScotBot version 4 for Twitch"""
from abc import ABC
import sys
import os
import logging
import traceback
import asyncio
from time import strftime, localtime
from twitchio.ext import commands
import logger as _logger


from auth import client_id, token, DISCORD, CHANNELS, LOGGERDICT
from twitchClasses import StreamChannel

LOGGER = logging.Logger("root")
_logger.setupLogger(LOGGER)
LOGGER.propagate = False

class ScotBot(commands.Bot, ABC):
    """BOT Class Scotbot"""
    def __init__(self):
        super().__init__(prefix="!", irc_token=token, client_id=client_id,
                         nick="ScotBotM8", initial_channels=list(CHANNELS.keys()))
        self.channels = {channel: StreamChannel(channel) for channel in list(CHANNELS.keys())}
        # self.server = WebhookServer(loop=self.loop, postCallback=self.parseWebhook)
        for channel in self.channels.values():
            channel: StreamChannel
            channel.displayName = CHANNELS[channel.name][0]
            channel.id = CHANNELS[channel.name][1]
            channel.spotifyNameSecret = CHANNELS[channel.name][2]
            channel.discordId = DISCORD[channel.name][0]
            channel.discordToken = DISCORD[channel.name][1]

    async def event_ready(self):
        LOGGER.info(f"Logged in as {self.nick}")
        LOGGER.info(f"Connecting to channels... {', '.join(self.initial_channels)}")
        for channel in self.channels.values():
            channel.channelObject = BOT.get_channel(channel.name)
        cogs = ["twitch_cogs.polls", "twitch_cogs.giveaways", "twitch_cogs.diceRolls", "twitch_cogs.spotify", "twitch_cogs.gameFunctions"]
        for cog in cogs:
            self.load_module(cog)
        self.loop.create_task(self.saveLogs(self.channels))
        self.loop.create_task(self.cogs.get("SpotifyCog").checkIfLive(self.channels))

        # LOGGER.info(f"Sanic Server started")
    @staticmethod
    async def saveLogs(channels: dict):
        """Saves chat logs to file every 10 mins and clears chat list"""
        while True:
            for channel in channels.values():
                if len(channel.chat) > 0:
                    month, monthAbv, year = strftime("%m", localtime()), strftime("%b", localtime()), strftime("%Y", localtime())
                    filename = os.path.join(channel.chatLogPath, f"{year}-{month}({monthAbv})_{channel}_chat_log.txt")
                    with open(filename, "a+", encoding='utf-8') as chatFile:
                        for message in channel.chat:
                            chatFile.write(f"{message}")
                    LOGGER.info(f"{channel.name} | {len(channel.chat)} message(s) saved to file")
                    channel.chat.clear()
            await asyncio.sleep(600)

    @staticmethod
    async def checkMod(ctx):
        """Checks if user is mod and outputs permission if not"""
        if not ctx.author.is_mod:
            await ctx.send("You don't have permission to use that command!")
            return False
        return True

    @staticmethod
    async def logCommand(ctx):
        """Logs a command"""
        LOGGER.log(6, f"'!{ctx.command.name}' used by {ctx.message.author.display_name} in channel '{ctx.channel.name}'")

    async def event_message(self, message):
        channel: StreamChannel = self.channels[message.channel.name]
        LOGGER.log(LOGGERDICT["bot"] if message.author.name == "scotbotm8" else LOGGERDICT["message"],
                   f"{message.channel.name} | {message.author.display_name}: {message.content}")
        channel.chat.append(f"{strftime('%d/%m/%Y %H:%M:%S')} | {message.author.display_name}: {message.content}\n")
        if "bits=" in message.raw_data:
            cheerAmount = message.raw_data.split("bits=")[1].split(";")[0]
            if int(cheerAmount) >= 10:
                await message.channel.send(f"@{message.author.display_name} just gave {cheerAmount} bits! Thank you! <3")
                LOGGER.info(f"{message.author.display_name} gave {cheerAmount} bits to '{message.channel.name}'")
            return
        if "HOSTTARGET" in message.raw_data:
            hostingChannel = message.raw_data.split("hosting_channel :"[1].split("[")[0])
            hostedViewers = message.raw_data.split("[")[1].split("]")[0]
            await message.channel.send(f"Please welcome the {hostedViewers} viewers from {hostingChannel}!")
            LOGGER.info(f"{hostingChannel} hosted '{message.channel.name}' with {hostedViewers}")
            return

        if channel.giveawayWord is not None:
            if message.content.lower().startswith(channel.giveawayWord):
                if message.author.name not in channel.giveawayEntrants:
                    channel.giveawayEntrants.append(f"{message.author.name}")

        await self.handle_commands(message)

    async def event_command_error(self, ctx, error):
        if isinstance(error, commands.CommandNotFound):
            pass
        else:
            LOGGER.error(f"[{ctx.channel.name}] {error}")
            traceback.print_exception(type(error), error, error.__traceback__, file=sys.stderr)

    @commands.command(name="dammit")
    async def dammit(self, ctx):
        """Dammit command"""
        await ctx.send(f"I blame {ctx.message.content.split('dammit ')[1]}. Cause reasons!")
        await self.logCommand(ctx)

    @commands.command(name="scotbotTest")
    async def scotbotTest(self, ctx):
        """Testing command"""
        await ctx.send(f"Version 4 of me is alive and well!")
        await self.logCommand(ctx)

    async def event_raw_usernotice(self, channel, tags):
        """Responds to subs, resubs, raids and gifted subs"""
        channelClass: StreamChannel = self.channels[channel.name]
        if tags["msg-id"] == "raid":
            raiderChannel = tags["display-name"]
            raiders = tags["msg-param-viewerCount"]
            LOGGER.info(f"Raiding '{channel.name}' from {raiderChannel} with {raiders} raiders")
            channelClass.chat.append(f"{strftime('%d/%m/%Y %H:%M:%S')} | USERNOTICE | {channel.name} raided by {raiderChannel}")
            await channel.send(f"Please welcome the {raiders} raiders from {raiderChannel}!")

        if tags["msg-id"] == "subgift":
            subGiver = tags["display-name"]
            subReceiver = tags["msg-param-recipient-display-name"]
            LOGGER.info(f"Sub gift from {subGiver} to {subReceiver} in '{channel.name}'")
            channelClass.chat.append(f"{strftime('%d/%m/%Y %H:%M:%S')} | USERNOTICE | {subGiver} gave sub to {subReceiver}")
            await channel.send(f"Thank you to {subGiver} for gifting a sub to {subReceiver}! <3")

        if tags["msg-id"] == "anonsubgift":
            subGiver = "Anonymous"
            subReceiver = tags["msg-param-recipient-display-name"]
            LOGGER.info(f"Anonymous sub gift to {subReceiver} in '{channel.name}'")
            channelClass.chat.append(f"{strftime('%d/%m/%Y %H:%M:%S')} | USERNOTICE | {subGiver} gave sub to {subReceiver}")
            await channel.send(f"Thank you to {subGiver} for gifting a sub to {subReceiver}! <3")

        if tags["msg-id"] == "ritual":
            newChatter = tags["display-name"]
            LOGGER.info(f"{newChatter} is new to '{channel.name}'")
            channelClass.chat.append(f"{strftime('%d/%m/%Y %H:%M:%S')} | USERNOTICE | {newChatter} has joined the channel")
            await channel.send(f"Please welcome @{newChatter} to the channel!")

        if tags["msg-id"] == "sub":
            user = tags["display-name"]
            LOGGER.info(f"{user} subscribed to '{channel.name}'")
            channelClass.chat.append(f"{strftime('%d/%m/%Y %H:%M:%S')} | USERNOTICE | {user} subbed")
            await channel.send(f"Thanks for the sub @{user}, and welcome tae aw the fun! <3")

        if tags["msg-id"] == "resub":  # and "quill18" not in channel.name:
            user = tags["display-name"]
            LOGGER.info(f"{user} resubscribed to '{channel.name}'")
            channelClass.chat.append(f"{strftime('%d/%m/%Y %H:%M:%S')} | USERNOTICE | {user} resubbed")
            await channel.send(f"Thanks for the {tags['msg-param-cumulative-months']}-month resub, @{user} - Welcome back! <3")

BOT = ScotBot()
BOT.run()
