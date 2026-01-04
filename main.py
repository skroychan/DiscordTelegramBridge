import re

import discord
from telebot.async_telebot import AsyncTeleBot

from config import discord_token, discord_chat_id, telegram_token, telegram_chat_id, telegram_message_thread_id


telegram_bot = AsyncTeleBot(telegram_token, parse_mode="MarkdownV2")


async def send_to_discord(username, text, quote_username=None, quote_text=None):
    channel = discord_bot.get_channel(discord_chat_id)
    if channel:
        result = f"**{username}**: {text}"

        if quote_text:
            quote_text = quote_text.replace("\n", "\n> ")
            if quote_username:
                result = f"> **{quote_username}**: {quote_text}\n{result}"
            else:
                result = f"> {quote_text}\n{result}"

        await channel.send(result)


def escape_markdown(str):
    return re.sub(r"([_\*\[\]\(\)~`>#+\-=|\{\}\.!])", r"\\\1", str)

async def send_to_telegram(username, text, quote_username=None, quote_text=None):
    result = f"*{username}*: {escape_markdown(text)}"

    if quote_text:
        quote_text = escape_markdown(quote_text).replace("\n", "\n>")
        if quote_username:
            result = f">*{quote_username}*: {quote_text}\n{result}"
        else:
            result = f">{quote_text}\n{result}"

    await telegram_bot.send_message(telegram_chat_id, result, message_thread_id=telegram_message_thread_id)


class DiscordBot(discord.Client):

    async def on_message(self, message):
        if message.author == self.user or message.channel.id != discord_chat_id:
            return

        text = message.content
        username = message.author.global_name or message.author.name

        if message.type == discord.MessageType.reply:
            replied_to = await message.channel.fetch_message(message.reference.message_id)

            quote = replied_to.content
            quote_author = None
            if replied_to.author != self.user:
                quote_author = replied_to.author.global_name or replied_to.author.name

            await send_to_telegram(username, text, quote_author, quote)

        else:
            await send_to_telegram(username, text)

    async def setup_hook(self):
        self.bg_task = self.loop.create_task(self.telegram_task())

    async def telegram_task(self):
        await self.wait_until_ready()
        await telegram_bot.infinity_polling()


@telegram_bot.message_handler(func=lambda m: True)
async def on_message(message):
    if message.chat.id != telegram_chat_id or (message.chat.is_forum and message.message_thread_id != telegram_message_thread_id):
        return

    text = message.text or message.caption
    username = message.from_user.first_name
    if message.from_user.last_name:
        username += " " + message.from_user.last_name

    if message.reply_to_message:
        if message.quote:
            quote = message.quote.text
        else:
            quote = message.reply_to_message.text or message.reply_to_message.caption
        quote_author = None
        if not message.reply_to_message.from_user.is_bot:
            quote_author = message.reply_to_message.from_user.first_name

        await send_to_discord(username, text, quote_author, quote)

    else:
        await send_to_discord(username, text)


intents = discord.Intents.default()
intents.message_content = True
discord_bot = DiscordBot(intents=intents)
discord_bot.run(discord_token)
