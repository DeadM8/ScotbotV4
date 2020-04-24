"""ScotBot version 4 for Twitch"""

from abc import ABC
import sys
import os
import logging
import traceback
import asyncio
import random
import ast
import json
import requests
import time
from time import strftime, localtime
import sanic
from sanic import response
import pandas as pd
import spotipy
import twitchio
from twitchio.ext import commands
import logger as _logger

from discord import Webhook, RequestsWebhookAdapter, Embed, Colour

from auth import client_id, token, spotify_client_id, spotify_client_secret, redirect_url
from steam import get_request
from Classes import StreamChannel, WebhookServer

app = sanic.Sanic(__name__)

LOGGER = logging.Logger("root")
_logger.setupLogger(LOGGER)

LOGGER.propagate = False

LOGGERDICT = {"spotify": 8, "bot": 7, "message": 5}
CHANNELS = {"deadm8": ["DeadM8", 56403701, "deadm8"],
            "quill18": ["Quill18", 18219250, None],
            "akiss4luck": ["aKiss4Luck", 37538116, None],
            "scotbotm8": ["ScotBotM8", 157817372, None]}
DISCORD = {"deadm8": [568111338270752768, "2blNd_5u9fhVeBNs2Z8mpXucBi4ZaqD_WnIQUZ4s6Yh7OqU5en5pdHFO0bk0792qoSyK"],
           "quill18": [538743285234008084, "hJaIEF0xmyIhgnIPNWFuP0g2F3N9JYCOJTOMLjUjeS4K6qUm2vy0eucGNbrx_3a5pjRN"],
           "akiss4luck": [568111338270752768, "2blNd_5u9fhVeBNs2Z8mpXucBi4ZaqD_WnIQUZ4s6Yh7OqU5en5pdHFO0bk0792qoSyK"],
           "scotbotm8": [568084609066336258, "TL2_Gbt1UDzJDBszpa00PMbJU4TRG0BycjYIekFb6t8Ms1l0-ziJUub3Ax_g28J8t9vO"]}

async def logCommand(ctx):
    """Logs a command"""
    LOGGER.log(6, f"'!{ctx.command.name}' used by {ctx.message.author.display_name} in channel '{ctx.channel.name}'")

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

async def getGame(gameName):
    """Returns a steam link for given game name"""
    games = pd.read_csv(os.path.join(os.getcwd(), "steamGameInfo.csv"))
    gameNameDB = gameName.lower().replace(" & ", " and").replace(":", "")
    gameInfo = games.loc[games["Name"] == gameNameDB]
    if not gameInfo.empty:
        gameDescription = gameInfo.iloc[0]["Description"].split(". ")[0]
        gameCategories = ast.literal_eval(gameInfo.iloc[0]["Categories"])
        gameGenres = ast.literal_eval(gameInfo.iloc[0]["Genres"])
        gameLink = gameInfo.iloc[0]["Link"]
    else:
        steamGames = pd.read_csv(os.path.join(os.getcwd(), "steamIDs.csv"))

        try:
            gameID = steamGames.loc[steamGames["name"].str.lower() == gameName.lower(), "appid"].item()
        except ValueError:
            try:
                gameID = steamGames.loc[steamGames["name"].str.lower() == gameName.lower().replace(" and ", " & "), "appid"].item()
            except ValueError:
                try:
                    gameID = steamGames.loc[steamGames["name"].str.lower() == gameName.lower().replace(" & ", " and "), "appid"].item()
                except ValueError:
                    try:
                        gameID = steamGames.loc[steamGames["name"].str.lower() == gameName.lower().replace(":", ""), "appid"].item()
                    except ValueError:
                        return False
        url = "http://store.steampowered.com/api/appdetails/"
        parameters = {"appids": gameID}
        jsonData = get_request(url, parameters=parameters)
        jsonAppData = jsonData[str(gameID)]
        if jsonAppData['success']:
            data = jsonAppData['data']
        else:
            return False
        gameDescription = data["short_description"].split(". ")[0]
        gameCategories = [category["description"] for category in data["categories"] if int(category["id"]) <= 2]
        genres = data["genres"]
        genres.sort(key=lambda elem: elem["id"])
        gameGenres = [genre["description"] for genre in genres]
        gameNameDB = gameName.lower().replace(" & ", " and ").replace(":", "")
        gameLink = f"store.steampowered.com/app/{gameID}"
        newGame = pd.DataFrame([(gameNameDB, gameID, gameDescription, gameCategories, gameGenres, gameLink)], index=[games.shape[0]])

        newGame.to_csv(os.path.join(os.getcwd(), "steamGameInfo.csv"), mode="a", header=False)
    if len(gameCategories) > 1:
        gameCategories = " and ".join(gameCategories)
    else:
        gameCategories = gameCategories[0]

    gameBlurb = {"name": gameName, "category": gameCategories, "genres": '-'.join(gameGenres), "description": gameDescription, "link": gameLink}
    return gameBlurb


async def checkIfLive(self, channels: dict):
    """Checks if any channels have gone live based on file LiveStatus.txt"""
    stamp = None
    while True:
        filename = os.path.join(os.getcwd(), "LiveStatus.txt")
        if stamp != os.stat(filename).st_mtime:
            with open(filename, "r") as liveStatus:
                liveDictInfo = {line.split(" | ")[0]: [False if line.split(" | ")[1] == "False" else True, line.split(" | ")[2].strip()] for line in
                                liveStatus.readlines()}
                # playingDict = {line.split(" | ")[0]: line.split(" | ")[2].strip() for line in liveStatus.readlines()}
                for channel in channels.values():
                    if channel.isLive is not liveDictInfo[channel.name][0]:
                        channel.isLive = liveDictInfo[channel.name][0]
                        channel.currentlyPlaying = liveDictInfo[channel.name][1]
                        LOGGER.info(f"{channel.name} | Live Status updated to: {channel.isLive}")
                        if channel.isLive and channel.spotifyNameSecret is not None:
                            self.loop.create_task(self.checkForNewSong(channel))
                        if channel.isLive and channel.name == "deadm8":
                            gameInfo = await getGame(channel.currentlyPlaying)
                            LOGGER.debug("Checking Game")
                            if gameInfo:
                                await self.updateWhatgame(channel)
            stamp = os.stat(filename).st_mtime
        await asyncio.sleep(60)


async def getCurrentSong(channel: StreamChannel):
    """Gets currently played song for channel, returns None if no song playing"""
    scope = "user-read-currently-playing"
    spotifyToken = spotipy.util.prompt_for_user_token(channel.spotifyNameSecret, scope, client_id=spotify_client_id,
                                                      client_secret=spotify_client_secret, redirect_uri=redirect_url)
    spotifyClient = spotipy.Spotify(auth=spotifyToken)
    currentTrack = spotifyClient.current_user_playing_track()
    trackInfo = {}
    if currentTrack is not None:
        trackInfo["name"] = currentTrack['item']['name']
        trackInfo["artist"] = currentTrack['item']['artists'][0]['name']
        trackInfo["URL"] = currentTrack['item']['external_urls']['spotify']

        if trackInfo is not None and channel.spotifyTrack != trackInfo["name"]:
            channel.spotifyTrack = trackInfo["name"]
            await channel.channelObject.send(f"The current song is \"{trackInfo['name']}\" by {trackInfo['artist']}. Listen to it at"
                                             f" {trackInfo['URL']}")
            LOGGER.log(LOGGERDICT["spotify"], f"{channel.name} | New song ({trackInfo['name']}) found")
            return True
    return False

class ScotBot(commands.Bot, ABC):
    """BOT class ScotBot"""
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

    async def checkMod(self, ctx):
        """Checks if user is mod and outputs permission if not"""
        if not ctx.author.is_mod:
            await ctx.send("You don't have permission to use that command!")
            return False
        return True

    async def event_ready(self):
        LOGGER.info(f"Logged in as {self.nick}")
        LOGGER.info(f"Connecting to channels... {', '.join(self.initial_channels)}")
        for channel in self.channels.values():
            channel.channelObject = BOT.get_channel(channel.name)
        cogs = ["cogs.polls", "cogs.giveaways", "cogs.diceRolls"]
        for cog in cogs:
            self.load_module(cog)
        self.loop.create_task(saveLogs(self.channels))
        self.loop.create_task(checkIfLive(self, self.channels))
        # LOGGER.info(f"Sanic Server started")

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

    async def updateWhatgame(self, channel: StreamChannel):
        """Updates the whatgame based upon the game provided"""
        gameInfo = await getGame(channel.currentlyPlaying)
        if gameInfo:
            await channel.channelObject.send(f"!editcom !whatgame {channel.displayName} is playing the {gameInfo['category']} "
                                             f"{gameInfo['genres']} game, {gameInfo['name']}! '{gameInfo['description']}.' LINK: {gameInfo['link']}")
            return True
        return False

    async def checkForNewSong(self, channel: StreamChannel):
        """Checks for a new song for a channel every 30 seconds and responds if channel is live and there is a new song"""
        while channel.isLive:
            await getCurrentSong(channel)
            await asyncio.sleep(30)

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
        await logCommand(ctx)

    @commands.command(name="scotbotTest")
    async def scotbotTest(self, ctx):
        """Testing command"""
        await ctx.send(f"Version 4 of me is alive and well!")
        await logCommand(ctx)

    @commands.command(name="song")
    async def song(self, ctx):
        """Gets the currently played song if there is a song playing and the channel is live"""
        await checkIfLive(self, self.channels)
        channel: StreamChannel = self.channels[ctx.channel.name]
        if channel.isLive and channel.spotifyNameSecret is not None:
            if not await getCurrentSong(channel):
                await ctx.send(f"@{ctx.author.display_name}, there is no song currently playing!")
        elif not channel.isLive:
            await ctx.send(f"@{ctx.author.display_name}, the channel is not live just now!")

    @commands.command(name="getGame")
    async def getGame(self, ctx):
        """Gets information regarding the game given"""
        if await self.checkMod(ctx):
            gameName = ctx.message.content.split("getGame ")[1]
            gameInfo = await getGame(gameName)
            if gameInfo:
                await ctx.send(f"{gameInfo['name']} is a {gameInfo['category']} {gameInfo['genres']} game. '{gameInfo['description']}.' STEAM: "
                               f"{gameInfo['link']}")
            else:
                await ctx.send(f"@{ctx.author.display_name}, the game {gameName} could not be found in Steam!")

    @commands.command(name="updateWhatgame")
    async def updateWhatgameCommand(self, ctx):
        """Updates the whatgame according to the game given in the command"""
        if await self.checkMod(ctx):
            channel: StreamChannel = self.channels[ctx.channel.name]
            channel.currentlyPlaying = ctx.message.content.split("updateWhatgame ")[1]
            if not await self.updateWhatgame(channel):
                ctx.send(f"@{ctx.author.display_name}, there was a problem updating the whatgame. Ensure that the game is available under the same name on Steam!")

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
