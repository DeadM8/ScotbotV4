import http3
import logging
import logger as _logger
from discord.ext import commands
from discord import Embed, Colour
from auth import CHANNELID

client = http3.AsyncClient()




maxResults = "50"
part = "snippet"

ENDDICT = {"Videos": "EgIQAQ%253D%253D", "Playlists": "EgIQAw%253D%253D"}


LOGGER = logging.getLogger(__name__)
_logger.setupLogger(LOGGER)

class YoutubeCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.PARAMS = {"part": part, "maxResults": maxResults}

    @staticmethod
    async def getRequest(requestType, params):
        url = f"https://www.googleapis.com/youtube/v3/{requestType}?"
        r = await client.get(url, params=params)
        return r.json()

    @staticmethod
    async def returnShorten(url):
        r = await client.get(url=f"http://tinyurl.com/api-create.php?url={url}")
        return r.text

    async def sendError(self, ctx, query, term):
        await ctx.send(f"ERROR: Check there are Playlists with containing {query} at"
                       f"{await self.returnShorten(f'https://www.youtube.com/results?search_query={query}+{CHANNELID[ctx.guild.name][1]}&sp={ENDDICT[term]}')}")

    async def sendEmbed(self, ctx: commands.Context, term: str, outputData: list, query: str):
        embed = Embed(
            title=f"See more at {await self.returnShorten(f'https://www.youtube.com/results?search_query={query}+{CHANNELID[ctx.guild.name][1]}&sp={ENDDICT[term]}')}",
            description=f"Showing the top {len(outputData)}",
            colour=Colour.red()
        )
        embed.set_thumbnail(url=CHANNELID[ctx.guild.name][2])
        for result in outputData[:5]:
            embed.add_field(name=result["title"], value=await self.returnShorten(result["link"]), inline=False)
        avatarURL = "https://cdn.discordapp.com/attachments/176727246160134144/491033960877391892/ScotBot5Shadow.png"
        embed.set_footer(icon_url=avatarURL, text="Scotbot - Created by DeadM8 for the QEB Community")
        await ctx.send(content=f"Showing {term.lower()} for the term: {query}", embed=embed)

    @commands.command(name="videos")
    async def videos(self, ctx: commands.Context):
        async with ctx.channel.typing():
            query = ctx.message.content.split("videos ")[1]
            self.PARAMS["q"] = query
            self.PARAMS["channelId"] = CHANNELID[ctx.guild.name][0]
            self.PARAMS["key"] = "AIzaSyCCdy96OcfyVDlAhSNuVh0xh3iMTJdEqIc"
            term = "Videos"
            outputData = []
            resultsRaw = await self.getRequest("search", self.PARAMS)
            results = resultsRaw["items"]
            for result in results:
                if result["id"]["kind"] == "youtube#video":
                    videoID = result["id"]["videoId"]
                    title = result["snippet"]["title"].replace("&#39;", "'").replace("&quot;", '"')
                    outputData.append({"link": f"http://www.youtube.com/watch?v={videoID}", "title": title})
        if len(outputData) == 0:
            await ctx.send(f"There were no videos found for the term {query}")
        else:
            await self.sendEmbed(ctx, term, outputData, query)
        LOGGER.info(f"{ctx.guild} | {ctx.author} used !videos for term {self.PARAMS['q']} and got {len(outputData)} results")
        del self.PARAMS["q"]
        del self.PARAMS["channelId"]
        del self.PARAMS["key"]

    @commands.command(name="playlists")
    async def playlists(self, ctx: commands.Context):
        async with ctx.channel.typing():
            query = ctx.message.content.split("playlists ")[1]
            term = "Playlists"
            self.PARAMS["key"] = "AIzaSyAmea94YXMDn8DP1wYjemqPiWHMgNHUIGY"
            self.PARAMS["channelId"] = CHANNELID[ctx.guild.name][0]
            outputData = []
            while len(outputData) <= 5:
                resultsRaw = await self.getRequest("playlists", self.PARAMS)
                if "nextPageToken" in resultsRaw:
                    self.PARAMS["pageToken"] = resultsRaw["nextPageToken"]
                else:
                    LOGGER.info(f"Reached last page")
                    break
                try:
                    results = resultsRaw["items"]
                except KeyError:
                    await self.sendError(ctx, query, term)
                for result in results:
                    playlistID = result["id"]
                    title = result["snippet"]["title"].replace("&#39;", "'").replace("&quot;", '"')
                    if query.lower() in title.lower():
                        outputData.append({"link": f"http://www.youtube.com/playlist?list={playlistID}", "title": title})

            if len(outputData) == 0:
                await ctx.send(f"There were no Playlists found for the term: {query}. Check at "
                               f"{await self.returnShorten(f'https://www.youtube.com/results?search_query={query}+{CHANNELID[ctx.guild.name][1]}&sp={ENDDICT[term]}')}")
            else:
                await self.sendEmbed(ctx, term, outputData, query)
            LOGGER.info(f"{ctx.guild} | {ctx.author} used !playlists for term '{query}' and got {len(outputData)} results")
            del self.PARAMS["channelId"]
            del self.PARAMS["key"]
            del self.PARAMS["pageToken"]

def setup(bot):
    bot.add_cog(YoutubeCog(bot))

