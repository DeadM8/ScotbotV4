import os
import sanic
import requests
from sanic import response

class StreamChannel:
    def __init__(self, name):
        self.name: str = name
        self.chat: list = []
        self.chatLogPath = os.path.join(os.getcwd(), "Chat_Logs", "Twitch", self.name)
        self.giveawayPath = os.path.join(os.getcwd(), "Giveaways", self.name)
        if not os.path.exists(self.chatLogPath):
            os.makedirs(self.chatLogPath)
        if not os.path.exists(self.giveawayPath):
            os.makedirs(self.giveawayPath)
        self.isLive: bool = False
        self.giveawayWord = None
        self.giveawayEntrants = []
        self.spotifyNameSecret = None
        self.spotifyTrack = None
        self.channelObject = None
        self.currentlyPlaying = None
        self.displayName = name
        self.id: int = 0
        self.webhookToken: str = ""
        self.webhookId: int = 0
        self.liveTime = 0
        self.pollOptions = {}
        self.pollEntrants = []

    def __repr__(self):
        return self.name

    async def entrantsFile(self):
        return os.path.join(self.giveawayPath, f"{self.giveawayWord}_giveaway_entrants.txt")

    async def winnersFile(self):
        return os.path.join(self.giveawayPath, f"{self.giveawayWord}_giveaway_winners.txt")

class WebhookServer(sanic.Sanic):
    def __init__(self, loop, postCallback):
        super().__init__()
        self._app = sanic.Sanic(__name__, configure_logging=False)
        self._app.add_route(self.handle_post, "/", methods=["POST"])
        self._app.add_route(self.handle_get, "/", methods=["GET"])
        self._host = "0.0.0.0"
        self._port = 8000
        self._loop = loop
        self._postCallback = postCallback

    async def handle_post(self, request):
        self._loop.create_task(self._postCallback(request))
        return response.HTTPResponse(body="202: OK", status=202)

    async def handle_get(self, request):
        if "hub.challenge" in request.args:
            return response.HTTPResponse(body=request.args['hub.challenge'][0], headers={'Content-Type': 'application/json'})
