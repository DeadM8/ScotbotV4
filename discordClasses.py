import os

class ServerClass:
    def __init__(self, name):
        self.name: str = name
        self.guildClass = None
        self.channelChat: dict = {}
        self.chatLogPath = os.path.join(os.getcwd(), "Chat_Logs", "Discord", self.name)
        if not os.path.exists(self.chatLogPath):
            os.makedirs(self.chatLogPath)

    # def checkChannelLogs(self):
    #     for channel in self.guildClass.text_channels:
    #         filename = os.path.join(self.chatLogPath, channel.name)
    #         if not os.path.exists(filename):
    #             os.makedirs(filename)
