from twitchio import Message
import asyncio
from configparser import ConfigParser
from twitchio.ext import commands

# Read config.ini file
from twitchio.ext.commands import bot

config_object = ConfigParser()
config_object.read("config.ini", encoding='utf-8')

botinfo = config_object["BOTINFO"]
config = config_object["CONFIG"]


def pretty_array_print(text, array, n_break):
    print(text)
    line_break = 0
    for item in array:
        print(f"{item} ", end="")
        line_break = line_break + 1
        if (line_break % n_break) == 0:
            print("")
    print("\n")


class Bot(commands.Bot):
    def __init__(self):
        # Initialise our Bot with our access token, prefix and a list of channels to join on boot...
        super().__init__(token=botinfo["TOKEN"],
                         prefix=botinfo["PREFIX"],
                         nick=botinfo["BOT_NICK"],
                         initial_channels=[x.lower().strip() for x in config["CHANNELS"].split(',')])
        self._current_channels = set([x.lower().strip() for x in config["CHANNELS"].split(',')])
        self._auth_users = [x.lower().strip() for x in config["AUTH_USERS"].split(',')]
        self._feedback_channels = [x.lower().strip() for x in config["BOT_FEEDBACK_CHANNEL"].split(',')]
        self._history_file_name = config["HISTORY_FILE"]
        self._history_file = open(self._history_file_name, 'a', encoding='utf-8')
        self._available_commands = ["help", "auth", "ping", "count", "join", "leave", "where", "silent", "state"]
        self._available_commands = [botinfo["PREFIX"] + command for command in self._available_commands]
        self._recorded_messages = 0
        self._silent = False

    async def event_ready(self) -> None:
        # We are logged in and ready to chat and use commands...
        print(f'{self.nick} is Online! Beep Boop... ({self.user_id})\n')
        # pretty_array_print("Currently in these channels:", self._current_channels, 5)

    async def record_message(self, message: Message) -> None:
        message_to_save = f"[{message.channel.name}] {message.author.name}: {message.content}"

        self._history_file.write(message_to_save + '\n')
        self._history_file.flush()

    async def event_message(self, message: Message) -> None:
        if not message.author:
            return

        if self._recorded_messages % int(config["MILESTONE"]) == 0 and self._recorded_messages != 0:
            milestone_message = f'Message count reached: {self._recorded_messages}'
            print(milestone_message)

            if not self._silent:
                channel = bot.get_channel(self._feedback_channels[0])
                loop = asyncio.get_event_loop()
                loop.create_task(channel.send(milestone_message))

        if message.channel.name.lower() not in self._feedback_channels:
            await self.record_message(message)
            self._recorded_messages = self._recorded_messages+1

        if message.author.name.lower() in self._auth_users and message.content.lower().startswith(tuple(self._available_commands)):
            await self.handle_commands(message)

    async def send_feedback_message(self, ctx, message):
        if ctx.channel.name.lower() in self._feedback_channels:
            await ctx.send(message)

    @commands.command(name="join")
    async def command_join(self, ctx: commands.Context):
        if ctx.author.name.lower() not in self._auth_users:
            return

        join_list = ctx.message.content.lower().split()
        join_list.pop(0)

        for channel in self._current_channels:
            if channel in join_list:
                join_list.remove(channel)

        if not join_list:
            await self.send_feedback_message(ctx, "No channels to join!")
            return

        await self.join_channels(join_list)
        self._current_channels.update(join_list)

        await self.send_feedback_message(ctx, f"Joining channels: {' '.join(join_list)}")

    @commands.command(name="leave")
    async def command_leave(self, ctx: commands.Context):
        if ctx.author.name.lower() not in self._auth_users:
            return
        leave_list = ctx.message.content.lower().split()
        leave_list.pop(0)

        for channel in leave_list:
            if channel not in self._current_channels:
                leave_list.remove(channel)

        await self.part_channels(leave_list)
        self._current_channels.difference_update(leave_list)

        if not leave_list:
            await self.send_feedback_message(ctx, "No channels to leave!")
            return

        await self.send_feedback_message(ctx, f"Leaving channels: {' '.join(leave_list)}")

    @commands.command(name="where")
    async def command_where(self, ctx: commands.Context):
        if not ctx:
            return
        if ctx.author.name.lower() not in self._auth_users:
            return

        await self.send_feedback_message(ctx, f"Currently in: {' '.join(self._current_channels)}")

    @commands.command(name="help")
    async def command_help(self, ctx):
        if ctx.author.name.lower() not in self._auth_users:
            return

        await self.send_feedback_message(ctx, f"Available commands: {' '.join(self._available_commands)}")

    @commands.command(name="ping")
    async def command_ping(self, ctx: commands.Context):
        if ctx.author.name.lower() not in self._auth_users:
            return

        await self.send_feedback_message(ctx, f'pong')

    @commands.command(name="auth")
    async def command_auth(self, ctx: commands.Context):
        if ctx.author.name.lower() not in self._auth_users:
            return

        await self.send_feedback_message(ctx, f"Authorized Users: {' '.join(self._auth_users)}")

    @commands.command(name="count")
    async def command_count(self, ctx:commands.Context):
        if ctx.author.name.lower() not in self._auth_users:
            return

        await self.send_feedback_message(ctx, f"Recorded Messages: {self._recorded_messages}")

    @commands.command(name="silent")
    async def command_silent(self, ctx: commands.Context):
        if ctx.author.name.lower() not in self._auth_users:
            return

        self._silent = not self._silent
        if self._silent:
            await self.send_feedback_message(ctx, f"Now silent! Recorded Messages: {self._recorded_messages}")
        else:
            await self.send_feedback_message(ctx, f"Now verbose! Recorded Messages: {self._recorded_messages}")

    @commands.command(name="state")
    async def command_state(self, ctx:commands.Context):
        if ctx.author.name.lower() not in self._auth_users:
            return

        await self.send_feedback_message(ctx, f"Silent: {self._silent}, Recorded Messages: {self._recorded_messages}, Milestone at {config['MILESTONE']}")


if __name__ == "__main__":
    bot = Bot()
    bot.run()
