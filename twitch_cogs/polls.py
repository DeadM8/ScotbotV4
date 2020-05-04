"""Polls Module"""
import logging
from twitchio.ext import commands
from twitchClasses import StreamChannel
import logger as _logger

LOGGER = logging.getLogger(__name__)
_logger.setupLogger(LOGGER)

@commands.cog()
class PollCog:
    """Poll Cog"""
    def __init__(self, bot):
        self._bot = bot

    @commands.command(name="pollOpen")
    async def pollOpen(self, ctx):
        """Opens a poll"""
        if await self._bot.checkMod(ctx):
            channel: StreamChannel = self._bot.channels[ctx.channel.name]
            pollOptions = ctx.message.content.split("pollOpen ")[1].split("|")
            pollOptions = [option.strip() for option in pollOptions]
            for option in pollOptions:
                channel.pollOptions[option] = 0
            await ctx.send(f"A new poll has been opened! Options: {'; '.join([f'{idx+1}: {option}' for idx, option in enumerate(pollOptions)])}. "
                           f"Please type '!vote 1' to vote for option 1, '!vote 2' for option 2 etc")

            LOGGER.info(f"{channel.name} | Poll opened")

    @commands.command(name="vote")
    async def vote(self, ctx):
        """Vote Command"""
        channel: StreamChannel = self._bot.channels[ctx.channel.name]
        if channel.pollOptions and ctx.author.name not in channel.pollEntrants:
            vote = int(ctx.message.content.split("vote ")[1])
            channel.pollOptions[list(channel.pollOptions.keys())[vote-1]] += 1
            channel.pollEntrants.append(ctx.author.name)

    @commands.command(name="pollClose")
    async def pollClose(self, ctx):
        """Closes a Poll"""
        if await self._bot.checkMod(ctx):
            channel: StreamChannel = self._bot.channels[ctx.channel.name]
            if channel.pollOptions:
                await ctx.send(f"The poll has been closed! Results: "
                               f"{'; '.join([f'{key}: {value}' for key, value in channel.pollOptions.items()])}")
                channel.pollOptions.clear()
                channel.pollEntrants.clear()
