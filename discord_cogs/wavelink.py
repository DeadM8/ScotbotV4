import asyncio
import discord
import itertools
import re
import sys
import traceback
import wavelink
import logging
import logger as _logger
from discord.ext import commands
from typing import Union
from auth import VALIDSERVERS


RURL = re.compile('https?:\/\/(?:www\.)?.+')
SURL = re.compile('https://open.spotify.com?.+playlist/([a-zA-Z0-9]+)')
REMOVEAFTER = 15

LOGGER = logging.getLogger(__name__)
_logger.setupLogger(LOGGER)

class MusicController:

    def __init__(self, bot, guild_id):
        self.bot = bot
        self.guild_id = guild_id
        self.channel = None

        self.next = asyncio.Event()
        self.queue = asyncio.Queue()

        self.volume = 40
        self.now_playing = None

        self.bot.loop.create_task(self.controller_loop())

    async def controller_loop(self):
        await self.bot.wait_until_ready()

        player = self.bot.wavelink.get_player(self.guild_id)
        await player.set_volume(self.volume)

        while True:
            if self.now_playing:
                await self.now_playing.delete()

            self.next.clear()

            song = await self.queue.get()
            await player.play(song)
            self.now_playing = await self.channel.send(f'Now playing: `{song}`')

            await self.next.wait()


class MusicCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.controllers = {}

        if not hasattr(bot, 'wavelink'):
            self.bot.wavelink = wavelink.Client(self.bot)

        self.bot.loop.create_task(self.start_nodes())

    async def start_nodes(self):
        await self.bot.wait_until_ready()

        # Initiate our nodes. For this example we will use one server.
        # Region should be a discord.py guild.region e.g sydney or us_central (Though this is not technically required)
        node = await self.bot.wavelink.initiate_node(host='localhost',
                                                     port=2333,
                                                     rest_uri='http://localhost:2333',
                                                     password='youshallnotpass',
                                                     identifier='TEST',
                                                     region='us_central')

        # Set our node hook callback
        node.set_hook(self.on_event_hook)

    async def on_event_hook(self, event):
        """Node hook callback."""
        if isinstance(event, (wavelink.TrackEnd, wavelink.TrackException)):
            controller = self.get_controller(event.player)
            controller.next.set()

    async def checkIfIdle(self, ctx):
        player = self.bot.wavelink.get_player(ctx.guild.id)
        while player.is_connected:
            for timeTick in range(300):
                if not player.paused or player.is_playing:
                    break
                await asyncio.sleep(10)
            else:
                await ctx.send("Disconnecting due to idle")
                await player.disconnect()
            await asyncio.sleep(10)

    def get_controller(self, value: Union[commands.Context, wavelink.Player]):
        if isinstance(value, commands.Context):
            gid = value.guild.id
        else:
            gid = value.guild_id

        try:
            controller = self.controllers[gid]
        except KeyError:
            controller = MusicController(self.bot, gid)
            self.controllers[gid] = controller

        return controller

    async def cog_check(self, ctx):
        """A local check which applies to all commands in this cog."""
        if not ctx.guild:
            raise commands.NoPrivateMessage
        return True

    async def cog_command_error(self, ctx, error):
        """A local error handler for all errors arising from commands in this cog."""
        if isinstance(error, commands.NoPrivateMessage):
            try:
                return await ctx.send('This command can not be used in Private Messages.')
            except discord.HTTPException:
                pass

        print('Ignoring exception in command {}:'.format(ctx.command), file=sys.stderr)
        traceback.print_exception(type(error), error, error.__traceback__, file=sys.stderr)

    @commands.command(name='connect')
    async def connect_(self, ctx, *, channel: discord.VoiceChannel = None):
        """Connect to a valid voice channel."""
        if ctx.guild.name in VALIDSERVERS:
            if not channel:
                try:
                    channel = ctx.author.voice.channel
                except AttributeError:
                    raise discord.DiscordException('No channel to join. Please either specify a valid channel or join one.')

            player = self.bot.wavelink.get_player(ctx.guild.id)
            await ctx.message.add_reaction(emoji=u"\U0001F3B5")
            await player.connect(channel.id)

            controller = self.get_controller(ctx)
            controller.channel = ctx.channel
            self.bot.loop.create_task(self.checkIfIdle(ctx))

    @commands.command()
    async def play(self, ctx, *, query: str):
        """Search for and add a song to the Queue."""
        if ctx.guild.name in VALIDSERVERS:
            player = self.bot.wavelink.get_player(ctx.guild.id)
            if not player.is_connected:
                await ctx.send(f"I am not connected to any channels! Please add me with `!connect <channel_name>`", delete_after=REMOVEAFTER)
                return

            if not RURL.match(query):
                query = f'ytsearch:{query}'

            tracks = await self.bot.wavelink.get_tracks(f'{query}')

            if not tracks:
                await ctx.send('Could not find any songs with that query.')
                await self.removeClutter(ctx.message)
                return

            track = tracks[0]

            controller = self.get_controller(ctx)
            await controller.queue.put(track)
            await ctx.send(f'Added {str(track)} to the queue.', delete_after=REMOVEAFTER)
            await self.removeClutter(ctx.message)

    @commands.command()
    async def pause(self, ctx):
        """Pause the player."""
        if ctx.guild.name in VALIDSERVERS:
            player = self.bot.wavelink.get_player(ctx.guild.id)
            if not player.is_playing:
                await ctx.send('I am not currently playing anything!', delete_after=REMOVEAFTER)
                await self.removeClutter(ctx.message)
                return

            await ctx.send('Pausing the song!', delete_after=REMOVEAFTER)
            await player.set_pause(True)
            await self.removeClutter(ctx.message)

    @commands.command()
    async def resume(self, ctx):
        """Resume the player from a paused state."""
        if ctx.guild.name in VALIDSERVERS:
            player = self.bot.wavelink.get_player(ctx.guild.id)
            if not player.paused:
                await ctx.send('I am not currently paused!', delete_after=REMOVEAFTER)
                await self.removeClutter(ctx.message)
                return

            await ctx.send('Resuming the player!', delete_after=REMOVEAFTER)
            await player.set_pause(False)
            await self.removeClutter(ctx.message)

    @commands.command()
    async def skip(self, ctx):
        """Skip the currently playing song."""
        if ctx.guild.name in VALIDSERVERS:
            player = self.bot.wavelink.get_player(ctx.guild.id)

            if not player.is_playing:
                await ctx.send('I am not currently playing anything!', delete_after=REMOVEAFTER)
                await self.removeClutter(ctx.message)
                return

            await ctx.send('Skipping the song!', delete_after=REMOVEAFTER)
            await player.stop()
            await self.removeClutter(ctx.message)

    @commands.command()
    async def volume(self, ctx, *, vol: int):
        """Set the player volume."""
        if ctx.guild.name in VALIDSERVERS:
            player = self.bot.wavelink.get_player(ctx.guild.id)
            controller = self.get_controller(ctx)

            vol = max(min(vol, 1000), 0)
            controller.volume = vol

            await ctx.send(f'Setting the player volume to `{vol}`', delete_after=REMOVEAFTER)
            await player.set_volume(vol)
            await self.removeClutter(ctx.message)

    @commands.command(aliases=['np', 'current', 'nowplaying'])
    async def now_playing(self, ctx):
        """Retrieve the currently playing song."""
        if ctx.guild.name in VALIDSERVERS:
            player = self.bot.wavelink.get_player(ctx.guild.id)

            if not player.current:
                await ctx.send('I am not currently playing anything!', deleted_after=REMOVEAFTER)
                await self.removeClutter(ctx.message)
                return

            controller = self.get_controller(ctx)
            await controller.now_playing.delete()
            controller.now_playing = await ctx.send(f'Now playing: `{player.current}`', deleted_after=REMOVEAFTER)
            await self.removeClutter(ctx.message)

    @commands.command(aliases=['q'])
    async def queue(self, ctx):
        """Retrieve information on the next 5 songs from the queue."""
        if ctx.guild.name in VALIDSERVERS:
            player = self.bot.wavelink.get_player(ctx.guild.id)
            controller = self.get_controller(ctx)

            if not player.current or not controller.queue._queue:
                await ctx.send(f'There are no songs currently in the queue.', delete_after=REMOVEAFTER)
                await self.removeClutter(ctx.message)
                return

            upcoming = list(itertools.islice(controller.queue._queue, 0, 5))

            fmt = '\n'.join(f'**`{str(song)}`**' for song in upcoming)
            embed = discord.Embed(title=f'Upcoming - Next {len(upcoming)}', description=fmt)

            await ctx.send(embed=embed, remove_after=REMOVEAFTER)
            await self.removeClutter(ctx.message)
        
    @commands.command(aliases=['disconnect', 'dc'])
    async def stop(self, ctx):
        """Stop and disconnect the player and controller."""
        if ctx.guild.name in VALIDSERVERS:
            player = self.bot.wavelink.get_player(ctx.guild.id)

            try:
                del self.controllers[ctx.guild.id]
            except KeyError:
                await player.disconnect()
                await ctx.message.add_reaction(emoji=u"\U0001F3B5")
                return

            await player.disconnect()
            await ctx.message.add_reaction(emoji=u"\U0001F3B5")

    @staticmethod
    async def removeClutter(message):
        await asyncio.sleep(REMOVEAFTER)
        await message.delete()

def setup(bot):
    bot.add_cog(MusicCog(bot))
