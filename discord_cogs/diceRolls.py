import logging
import logger as _logger
from discord.ext import commands

from rollFunctions import returnRoll
LOGGER = logging.getLogger(__name__)
_logger.setupLogger(LOGGER)

class RollsCog(commands.Cog):
    """Dice Cog"""
    def __init__(self, bot):
        self._bot = bot

    @commands.command(name="roll")
    async def roll(self, ctx: commands.Context):
        diceMessage = await returnRoll(ctx.message.content)
        await ctx.send(f"{ctx.author.mention} rolled {diceMessage}")
        LOGGER.info(f"{ctx.guild} | {ctx.channel} | {ctx.author} used !roll")

def setup(bot):
    bot.add_cog(RollsCog(bot))
