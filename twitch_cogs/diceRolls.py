"""Dice Roll module"""
import logging
import logger as _logger
from twitchio.ext import commands
from rollFunctions import returnRoll

LOGGER = logging.getLogger(__name__)
_logger.setupLogger(LOGGER)

@commands.cog()
class DiceCog:
    """Dice Cog"""
    def __init__(self, bot):
        self._bot = bot

    @commands.command(name="roll")
    async def roll(self, ctx):
        """Rolls the dice"""
        diceMessage = await returnRoll(ctx.message.content)
        await ctx.send(f"@{ctx.author.display_name} rolled {diceMessage}")
        LOGGER.info(f"{ctx.guild} | {ctx.author} | {ctx.author.display_name} used !roll")
