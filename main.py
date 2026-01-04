import re
import io, aiohttp

import discord
from telebot.async_telebot import AsyncTeleBot
from telebot.types import InputMediaPhoto, InputMediaVideo, InputMediaAudio, InputMediaDocument

from config import discord_token, discord_chat_id, telegram_token, telegram_chat_id, telegram_message_thread_id, telegram_bot_id


telegram_bot = AsyncTeleBot(telegram_token, parse_mode="MarkdownV2")


async def download_file(url):
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            if resp.status == 200:
                return io.BytesIO(await resp.read())

async def send_to_discord(username, text, attachment_url=None, has_spoiler=False, quote_username=None, quote_text=None):
    channel = discord_bot.get_channel(discord_chat_id)
    if channel:
        result = f"**{username}**: {text}"

        if quote_text:
            quote_text = quote_text.replace("\n", "\n> ")
            if quote_username:
                result = f"> **{quote_username}**: {quote_text}\n{result}"
            else:
                result = f"> {quote_text}\n{result}"

        if attachment_url:    
            data = await download_file(attachment_url)
            file = discord.File(data, attachment_url.split("/")[-1], spoiler=has_spoiler)
            await channel.send(result, file=file)

        else:
            await channel.send(result)


def escape_markdown(str):
    return re.sub(r"([_\*\[\]\(\)~`>#+\-=|\{\}\.!])", r"\\\1", str)

async def send_to_telegram(username, text, attachments=[], embeds=[], quote_username=None, quote_text=None):
    result = f"*{escape_markdown(username)}*: {escape_markdown(text)}"

    if quote_text:
        quote_text = escape_markdown(quote_text).replace("\n", "\n>")
        quote_username = escape_markdown(quote_username)
        if quote_username:
            result = f">*{quote_username}*: {quote_text}\n{result}"
        else:
            result = f">{quote_text}\n{result}"

    if attachments or embeds:
        if len(attachments) + len(embeds) > 1:
            media_group = []
            for attachment in attachments:
                if attachment.content_type.startswith("image"):
                    media_group.append(InputMediaPhoto(attachment.url, show_caption_above_media=True, has_spoiler=attachment.is_spoiler()))
                elif attachment.content_type.startswith("video"):
                    media_group.append(InputMediaVideo(attachment.url, show_caption_above_media=True, has_spoiler=attachment.is_spoiler()))
                elif attachment.content_type.startswith("audio"):
                    media_group.append(InputMediaPhoto(attachment.url, show_caption_above_media=True))
                else:
                    media_group.append(InputMediaDocument(attachment.url, show_caption_above_media=True))
            
            for embed in embeds:
                result = result.replace(escape_markdown(embed.url), "", 1)
                if embed.type == "image":
                    media_group.append(InputMediaPhoto(embed.image.proxy_url or embed.image.url or embed.url, show_caption_above_media=True))
                elif embed.type == "video" or embed.type == "gifv":
                    media_group.append(InputMediaVideo(embed.video.proxy_url or embed.video.url or embed.url, show_caption_above_media=True))
                    
            media_group[0].caption = result
            
            await telegram_bot.send_media_group(telegram_chat_id, media_group, message_thread_id=telegram_message_thread_id)

        else:
            if attachments:
                attachment = attachments[0]
                if attachment.content_type.startswith("image"):
                    await telegram_bot.send_photo(telegram_chat_id, attachment.url, result, show_caption_above_media=True, has_spoiler=attachment.is_spoiler(), message_thread_id=telegram_message_thread_id)
                elif attachment.content_type.startswith("video"):
                    await telegram_bot.send_video(telegram_chat_id, attachment.url, caption=result, show_caption_above_media=True, has_spoiler=attachment.is_spoiler(), message_thread_id=telegram_message_thread_id)
                elif attachment.content_type.startswith("audio"):
                    await telegram_bot.send_audio(telegram_chat_id, attachment.url, result, show_caption_above_media=True, message_thread_id=telegram_message_thread_id)
                else:
                    await telegram_bot.send_document(telegram_chat_id, attachment.url, caption=result, show_caption_above_media=True, message_thread_id=telegram_message_thread_id)
            if embeds:
                embed = embeds[0]
                result = result.replace(escape_markdown(embed.url), "", 1)
                if embed.type == "image":
                    await telegram_bot.send_photo(telegram_chat_id, embed.image.proxy_url or embed.image.url or embed.url, result, show_caption_above_media=True, message_thread_id=telegram_message_thread_id)
                elif embed.type == "video" or embed.type == "gifv":
                    await telegram_bot.send_video(telegram_chat_id, embed.video.proxy_url or embed.video.url or embed.url, caption=result, show_caption_above_media=True, message_thread_id=telegram_message_thread_id)

    else:
        await telegram_bot.send_message(telegram_chat_id, result, message_thread_id=telegram_message_thread_id)


class DiscordBot(discord.Client):
    async def on_message(self, message):
        if message.author == self.user or message.channel.id != discord_chat_id:
            return

        text = message.system_content if message.is_system() else message.clean_content
        username = message.author.global_name or message.author.name

        if message.type == discord.MessageType.reply:
            replied_to = await message.channel.fetch_message(message.reference.message_id)

            quote = replied_to.system_content if replied_to.is_system() else replied_to.clean_content
            quote_author = None
            if replied_to.author != self.user:
                quote_author = replied_to.author.global_name or replied_to.author.name

            await send_to_telegram(username, text, message.attachments, message.embeds, quote_author, quote)

        else:
            await send_to_telegram(username, text, message.attachments, message.embeds)

    async def setup_hook(self):
        self.bg_task = self.loop.create_task(self.telegram_task())

    async def telegram_task(self):
        await self.wait_until_ready()
        await telegram_bot.infinity_polling()


@telegram_bot.message_handler(func=lambda m: True, content_types=['text', 'audio', 'document', 'animation', 'photo', 'sticker', 'video', 'video_note', 'voice'])
async def on_message(message):
    if message.chat.id != telegram_chat_id or (message.chat.is_forum and message.message_thread_id != telegram_message_thread_id):
        return

    text = message.text or message.caption or ""
    username = message.from_user.first_name
    if message.from_user.last_name:
        username += " " + message.from_user.last_name

    attachment_url = None
    attachment_filename = None
    if message.photo:
        photo = max(message.photo, key=lambda p: p.file_size)
        attachment_url = await telegram_bot.get_file_url(photo.file_id)
    elif message.animation:
        attachment_url = await telegram_bot.get_file_url(message.animation.file_id)
        attachment_filename = message.animation.file_name
    elif message.audio:
        attachment_url = await telegram_bot.get_file_url(message.audio.file_id)
        attachment_filename = message.audio.file_name
    elif message.sticker:
        attachment_url = await telegram_bot.get_file_url(message.sticker.file_id)
    elif message.video:
        attachment_url = await telegram_bot.get_file_url(message.video.file_id)
        attachment_filename = message.video.file_name
    elif message.video_note:
        attachment_url = await telegram_bot.get_file_url(message.video_note.file_id)
    elif message.voice:
        attachment_url = await telegram_bot.get_file_url(message.voice.file_id)
    elif message.document:
        attachment_url = await telegram_bot.get_file_url(message.document.file_id)
        attachment_filename = message.document.file_name

    if message.reply_to_message:
        if message.quote:
            quote = message.quote.text
        else:
            quote = message.reply_to_message.text or message.reply_to_message.caption
        quote_author = None
        if message.reply_to_message.from_user.id != telegram_bot_id:
            quote_author = message.reply_to_message.from_user.first_name

        await send_to_discord(username, text, attachment_url, message.has_media_spoiler, quote_author, quote)

    else:
        await send_to_discord(username, text, attachment_url, message.has_media_spoiler)


intents = discord.Intents.default()
intents.message_content = True
discord_bot = DiscordBot(intents=intents)
discord_bot.run(discord_token)
