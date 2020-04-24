import logging
import random
from twitchio.ext import commands
from Classes import StreamChannel


LOGGER = logging.getLogger(__name__)

async def keepHighest(dice: list, numToKeep: int):
    return sorted(dice)[-numToKeep:]

async def keepLowest(dice: list, numToKeep: int):
    return sorted(dice)[:numToKeep]

async def dropHighest(dice: list, numToDrop: int):
    return sorted(dice)[:-numToDrop]

async def dropLowest(dice: list, numToDrop: int):
    return sorted(dice)[numToDrop:]

DICEDICT = {"kh": keepHighest,
            "kl": keepLowest,
            "dh": dropHighest,
            "dl": dropLowest}

@commands.cog()
class PollCog:
    def __init__(self, bot):
        self._bot = bot

    @commands.command(name="roll")
    async def roll(self, ctx):
        diceRaw: str = ctx.message.content.split("roll ")[1].lower()
        prefix = diceRaw.split("d")[0]
        if prefix == "":
            diceToRoll = 1
        else:
            diceToRoll = int(prefix)
        try:
            diceSides = int(diceRaw.split("d")[1].split(" ")[0])
        except IndexError:
            diceSides = int(diceRaw.split("d")[1])

        if "+" in diceRaw:
            try:
                modNum = int(diceRaw.split("+")[1].split(" ")[0])
            except ValueError:
                modNum = int(diceRaw.split("+")[1])
            mod = modNum
        elif "-" in diceRaw:
            try:
                modNum = int(diceRaw.split("-")[1].split("-")[0])
            except ValueError:
                modNum = int(diceRaw.split("-")[1])
            mod = -modNum
        else:
            mod = 0
        diceRolls = [random.randrange(1, diceSides+1) + mod for dice in range(diceToRoll)]

        if len(diceRolls) == 1:
            diceMessage = f"{diceRolls[0]}"
        else:
            diceMessage = f"{'+'.join([str(roll) for roll in diceRolls])}"

            for key, value in DICEDICT.items():
                if key in diceRaw:
                    try:
                        numDice = int(diceRaw.split(key)[1].split(" ")[0])
                    except IndexError:
                        numDice = int(diceRaw.split(key)[1])
                    except ValueError:
                        numDice = 1
                    finalDice = await value(diceRolls, numDice)
                    break
            else:
                finalDice = diceRolls
            diceMessage = f"{diceMessage}; Final Value = {sum(finalDice)}"

        await ctx.send(f"@{ctx.author.display_name} rolled {diceMessage}")
        LOGGER.info(f"{ctx.author.display_name} rolled {diceRolls}, = {sum(diceRolls)}")





