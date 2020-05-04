"""Handles Spotify Cog"""
import os
import logging
import asyncio
import spotipy
import pandas as pd

import logger as _logger
from twitchio.ext import commands
from twitchClasses import StreamChannel
from auth import spotify_client_secret, spotify_client_id, redirect_url, LOGGERDICT

LOGGER = logging.getLogger(__name__)

@commands.cog()
class SpotifyCog:
    """Spotify Cog"""
    def __init__(self, bot):
        self._bot = bot

    @staticmethod
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

    @commands.command(name="song")
    async def song(self, ctx):
        """Gets the currently played song if there is a song playing and the channel is live"""
        await self._bot.checkIfLive(self, self._bot.channels)
        channel: StreamChannel = self._bot.channels[ctx.channel.name]
        if channel.isLive and channel.spotifyNameSecret is not None:
            if not await self.getCurrentSong(channel):
                await ctx.send(f"@{ctx.author.display_name}, there is no song currently playing!")
        elif not channel.isLive:
            await ctx.send(f"@{ctx.author.display_name}, the channel is not live just now!")

    async def checkForNewSong(self, channel: StreamChannel):
        """Checks for a new song for a channel every 30 seconds and responds if channel is live and there is a new song"""
        while channel.isLive:
            await self.getCurrentSong(channel)
            await asyncio.sleep(30)

    async def checkIfLive(self, channels: dict):
        """Checks if any channels have gone live based on file LiveStatus.csv"""
        stamp = None
        while True:
            filename = os.path.join(os.getcwd(), "LiveStatus.csv")
            if stamp != os.stat(filename).st_mtime:
                df = pd.read_csv(filename)
                for channel in channels.values():
                    streamInfo = df.loc[df["Channel"] == channel.name]
                    if channel.isLive is not streamInfo.iloc[0]["liveStatus"]:
                        channel.isLive = streamInfo.iloc[0]["liveStatus"]
                        channel.currentlyPlaying = streamInfo.iloc[0]["Game"]
                        LOGGER.info(f"{channel.name} | Live Status updated to: {channel.isLive}")
                        if channel.isLive and channel.spotifyNameSecret is not None:
                            self._bot.loop.create_task(self.checkForNewSong(channel))
                        if channel.isLive and channel.name == "deadm8":
                            gameInfo = await self._bot.cogs.get("GameCog").findGame(channel.currentlyPlaying)
                            LOGGER.debug("Checking Game")
                            if gameInfo:
                                await self._bot.cogs.get("GameCog").updateWhatgame(channel)
                stamp = os.stat(filename).st_mtime
            await asyncio.sleep(60)
