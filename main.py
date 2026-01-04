import re

import discord
from telebot.async_telebot import AsyncTeleBot

from config import discord_token, discord_chat_id, telegram_token, telegram_chat_id, telegram_message_thread_id


telegram_bot = AsyncTeleBot(telegram_token, parse_mode="MarkdownV2")


async def send_to_discord(message, username):
    channel = discord_bot.get_channel(discord_chat_id)
    if channel:
        await channel.send(f"**{username}**: {message}")


def escape_markdown(str):
    return re.sub(r"([_\*\[\]\(\)~`>#+\-=|\{\}\.!])", r"\\\1", str)

async def send_to_telegram(message, username):
    await telegram_bot.send_message(telegram_chat_id, f"*{username}*: {escape_markdown(message)}", message_thread_id=telegram_message_thread_id)



class DiscordBot(discord.Client):

    async def on_message(self, message):
        if message.author == self.user or message.channel.id != discord_chat_id:
            return

        await send_to_telegram(message.content, message.author.global_name or message.author.name)

    async def setup_hook(self):
        self.bg_task = self.loop.create_task(self.telegram_task())

    async def telegram_task(self):
        await self.wait_until_ready()
        await telegram_bot.infinity_polling()


@telegram_bot.message_handler(func=lambda m: True)
async def test(message):
    if message.chat.id != telegram_chat_id or message.message_thread_id != telegram_message_thread_id:
        return

    text = message.text or message.caption
    username = message.from_user.first_name
    if message.from_user.last_name:
        username += " " + message.from_user.last_name

    await send_to_discord(text, username)


intents = discord.Intents.default()
intents.message_content = True
discord_bot = DiscordBot(intents=intents)
discord_bot.run(discord_token)
