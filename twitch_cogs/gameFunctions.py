"""Module for defining game updates, getting games from Steam, setting !whatgame etc"""
import os
import ast
import logging
import logger as _logger
import pandas as pd
import twitchio.ext
from steam import get_request
from twitchClasses import StreamChannel

LOGGER = logging.getLogger(__name__)
_logger.setupLogger(LOGGER)

@twitchio.ext.commands.cog()
class GameCog:
    """Game Cog"""
    def __init__(self, bot):
        self._bot = bot

    async def updateWhatgame(self, channel: StreamChannel):
        """Updates the whatgame based upon the game provided"""
        gameInfo = await self.findGame(channel.currentlyPlaying)
        if gameInfo:
            await channel.channelObject.send(f"!editcom !whatgame {channel.displayName} is playing the {gameInfo['category']} "
                                             f"{gameInfo['genres']} game, {gameInfo['name']}! {gameInfo['description']}. LINK: {gameInfo['link']}")
            return True
        return False

    @staticmethod
    async def findGame(gameName):
        """Returns a steam link for given game name"""
        games = pd.read_csv(os.path.join(os.getcwd(), "steamGameInfo.csv"))
        gameNameDB = gameName.lower()
        gameInfo = games.loc[games["Name"] == gameNameDB]
        if not gameInfo.empty:
            gameDescription = gameInfo.iloc[0]["Description"].split(". ")[0]
            gameCategories = ast.literal_eval(gameInfo.iloc[0]["Categories"])
            gameGenres = ast.literal_eval(gameInfo.iloc[0]["Genres"])
            gameLink = gameInfo.iloc[0]["Link"]
        else:
            steamGames = pd.read_csv(os.path.join(os.getcwd(), "steamIDs.csv"))
            try:
                gameID = steamGames.loc[steamGames["name"].str.lower() == gameNameDB, "appid"].item()
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

            jsonAppData = get_request("http://store.steampowered.com/api/appdetails/", parameters={"appids": gameID})[str(gameID)]
            if jsonAppData['success']:
                data = jsonAppData['data']
            else:
                return False
            gameDescription = data["short_description"].split(". ")[0]
            LOGGER.info(f"Adding {gameNameDB} to the database")
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

    @twitchio.ext.commands.command(name="getGame")
    async def getGame(self, ctx):
        """Gets information regarding the game given"""
        gameName = ctx.message.content.split("getGame ")[1]
        gameInfo = await self.findGame(gameName)
        if gameInfo:
            await ctx.send(f"{gameInfo['name']} is a {gameInfo['category']} {gameInfo['genres']} game. {gameInfo['description']}. LINK: "
                           f"{gameInfo['link']}")
        else:
            await ctx.send(f"@{ctx.author.display_name}, the game {gameName} could not be found in Steam!")
        await self._bot.logCommand(ctx)

    @twitchio.ext.commands.command(name="updateWhatgame")
    async def updateWhatgameCommand(self, ctx):
        """Updates the whatgame according to the game given in the command"""
        if await self._bot.checkMod(ctx):
            channel: StreamChannel = self._bot.channels[ctx.channel.name]
            channel.currentlyPlaying = ctx.message.content.split("updateWhatgame ")[1]
            if not await self.updateWhatgame(channel):
                ctx.send(f"@{ctx.author.display_name}, there was a problem updating the whatgame. Ensure that the game is available under the same name on Steam!")
        await self._bot.logCommand(ctx)
