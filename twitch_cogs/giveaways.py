"""Module which deals with giveaways"""
import logging
import os
import random
import asyncio
from twitchio.ext import commands
from twitchClasses import StreamChannel
import logger as _logger

LOGGER = logging.getLogger(__name__)
_logger.setupLogger(LOGGER)

@commands.cog()
class GiveawayCog:
    """Giveaway Cog"""
    def __init__(self, bot):
        self._bot = bot

    @staticmethod
    async def saveGiveawayEntrants(channel: StreamChannel):
        """Saves giveaway entrants to file"""
        if len(channel.giveawayEntrants) > 0:
            with open(await channel.entrantsFile(), "a+", encoding='utf-8') as entrantsFile:
                for entrant in channel.giveawayEntrants:
                    entrantsFile.write(f"{entrant}\n")
            LOGGER.info(f"{channel} | {len(channel.giveawayEntrants)} entrant(s) added to the giveaway")
            channel.giveawayEntrants.clear()
        else:
            LOGGER.info(f"{channel} | Entrants list checked")

    async def saveGiveawayEntrantsLoop(self, channel: StreamChannel):
        """Starts giveaway entrants saving loop, stops when poll finishes (giveaway word is None)"""
        while channel.giveawayWord is not None:
            await self.saveGiveawayEntrants(channel)
            await asyncio.sleep(30)

    @commands.command(name="giveawayOpen")
    async def giveawayOpen(self, ctx):
        """Opens a giveaway and starts loops which saves entrants to file"""
        if await self._bot.checkMod(ctx):
            channel: StreamChannel = self._bot.channels[ctx.channel.name]
            if channel.giveawayWord is not None:
                await ctx.send(f"There is already a giveaway open! Please use '!giveawayClose' to close it first")
            else:
                if len(ctx.message.content.split(" ")[1]) <= 3:
                    await ctx.send(f"@{ctx.author.display_name}, please ensure the keyword is more than 3 characters long!")
                    return
                channel.giveawayWord = ctx.message.content.split(" ")[1].lower()

                entrantsFile = await channel.entrantsFile()
                if os.path.exists(entrantsFile):
                    os.remove(entrantsFile)
                winnersFile = await channel.winnersFile()
                if os.path.exists(winnersFile):
                    os.remove(winnersFile)
                self._bot.loop.create_task(self.saveGiveawayEntrantsLoop(channel))
                await ctx.send(f"Giveaway opened by {ctx.message.author.display_name}. To enter, please type: {channel.giveawayWord}")
                LOGGER.info(f"Giveaway with keyword '{channel.giveawayWord}' opened")

    @commands.command(name="giveawayDraw")
    async def giveawayDraw(self, ctx):
        """Draws a winner for the giveaway and whispers it to the person that calls the command"""
        if await self._bot.checkMod(ctx):
            channel: StreamChannel = self._bot.channels[ctx.channel.name]
            if channel.giveawayWord is None:
                await ctx.send(f"@{ctx.author.display_name}, there is no open giveaway to draw! Please use '!giveawayOpen' to start one")
            else:
                await self.saveGiveawayEntrants(channel)
                with open(await channel.entrantsFile(), "r", encoding="utf-8") as entrantsFile:
                    for entrant in entrantsFile:
                        channel.giveawayEntrants.append(entrant)
                winner = channel.giveawayEntrants.pop(random.randrange(len(channel.giveawayEntrants))).strip("\n")
                LOGGER.info(f"{channel} | {winner} won the giveaway")
                with open(await channel.winnersFile(), "a+") as winnersFile:
                    winnersFile.write(f"{winner}\n")
                await self._bot._ws._websocket.send(f"PRIVMSG #jtv :/w {ctx.author.name} {winner} won the giveaway with the giveaway word: {channel.giveawayWord}\r\n")
                with open(await channel.entrantsFile(), "w", encoding="utf-8") as entrantsFile:
                    for entrant in channel.giveawayEntrants:
                        entrantsFile.write(f"{entrant}\n")
                await ctx.send(f"@{ctx.message.author.display_name}, please check your whispers for the winner!")
                LOGGER.info(f"Whisper sent to {ctx.author.display_name}")

    @commands.command(name="giveawayClose")
    async def giveawayClose(self, ctx):
        """Closes the giveaway and stops the enter giveaways loop"""
        if await self._bot.checkMod(ctx):
            channel: StreamChannel = self._bot.channels[ctx.channel.name]
            if channel.giveawayWord is None:
                await ctx.send(f"@{ctx.message.author.display_name}, there is no open giveaway to draw! Please use '!giveawayOpen' to start one")
            else:
                await self.saveGiveawayEntrants(channel)
                entrants = len(open(await channel.entrantsFile(), "r").readlines()) + len(open(await channel.winnersFile(), "r").readlines())
                channel.giveawayWord = None
                await ctx.send(f"Giveaway closed! Thank you to the {entrants} people that entered!")
                LOGGER.info(f"{channel} | Giveaway closed")
