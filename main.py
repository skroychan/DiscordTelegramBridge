import re
import io, aiohttp
import os
from urllib.parse import urlparse, unquote

import discord
from discord import PartialEmoji, StickerFormatType
from telebot.async_telebot import AsyncTeleBot
from telebot.types import InputMediaPhoto, InputMediaVideo, InputMediaAudio, InputMediaDocument

from config import discord_token, discord_chat_id, telegram_token, telegram_chat_id, telegram_message_thread_id, telegram_bot_id


telegram_bot = AsyncTeleBot(telegram_token, parse_mode="MarkdownV2")


def get_filename_from_url(url):
    parsed_url = urlparse(url)
    return os.path.basename(unquote(parsed_url.path))

def get_extension(filename):
    return os.path.splitext(filename)[1]

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
            file = discord.File(data, get_filename_from_url(attachment_url), spoiler=has_spoiler)
            await channel.send(result, file=file)

        else:
            await channel.send(result)


def escape_markdown(str):
    return re.sub(r"([_\*\[\]\(\)~`>#+\-=|\{\}\.!])", r"\\\1", str)

async def send_to_telegram(username, text, attachments=[], embeds=[], emojis=[], stickers=[], quote_username=None, quote_text=None):
    result = f"*{escape_markdown(username)}*: {escape_markdown(text)}"

    if quote_text:
        quote_text = escape_markdown(quote_text).replace("\n", "\n>")
        quote_username = escape_markdown(quote_username)
        if quote_username:
            result = f">*{quote_username}*: {quote_text}\n{result}"
        else:
            result = f">{quote_text}\n{result}"

    if attachments or embeds or emojis or stickers:
        if len(attachments) + len(embeds) + len(emojis) + len(stickers) > 1:
            media_group = []

            for emoji in emojis:
                if emoji.animated:
                    media_group.append(InputMediaAnimation(emoji.url, show_caption_above_media=True))
                else:
                    media_group.append(InputMediaPhoto(emoji.url, show_caption_above_media=True))
            
            for sticker in stickers:
                if sticker.format == StickerFormatType.apng or sticker.format == StickerFormatType.gif:
                    media_group.append(InputMediaAnimation(sticker.url, show_caption_above_media=True))
                elif sticker.format == StickerFormatType.png:
                    media_group.append(InputMediaPhoto(sticker.url, show_caption_above_media=True))

            for attachment in attachments:
                if attachment.content_type.startswith("image"):
                    media_group.append(InputMediaPhoto(attachment.url, show_caption_above_media=True, has_spoiler=attachment.is_spoiler()))
                elif attachment.content_type.startswith("video"):
                    media_group.append(InputMediaVideo(attachment.url, show_caption_above_media=True, has_spoiler=attachment.is_spoiler()))
                elif attachment.content_type.startswith("audio"):
                    media_group.append(InputMediaAudio(attachment.url, show_caption_above_media=True))
                else:
                    media_group.append(InputMediaDocument(attachment.url, show_caption_above_media=True))

            for embed in embeds:
                if embed.type == "image":
                    media_group.append(InputMediaPhoto(embed.image.proxy_url or embed.image.url or embed.url, show_caption_above_media=True))
                elif embed.type == "video":
                    media_group.append(InputMediaVideo(embed.video.proxy_url or embed.video.url or embed.url, show_caption_above_media=True))
                elif embed.type == "gifv":
                    media_group.append(InputMediaAnimation(embed.video.proxy_url or embed.video.url or embed.url, show_caption_above_media=True))

            media_group[0].caption = result

            if len(media_group) <= 10:
                await telegram_bot.send_media_group(telegram_chat_id, media_group, message_thread_id=telegram_message_thread_id)
            else:
                for i in range(0, min(len(media_group), 50), 10):
                    batch = media_group[i:i+10]
                    await telegram_bot.send_media_group(telegram_chat_id, batch, message_thread_id=telegram_message_thread_id)

        else:
            if emojis:
                emoji = emojis[0]
                if emoji.animated:
                    await telegram_bot.send_animation(telegram_chat_id, emoji.url, caption=result, show_caption_above_media=True, message_thread_id=telegram_message_thread_id)
                else:
                    await telegram_bot.send_photo(telegram_chat_id, emoji.url, result, show_caption_above_media=True, message_thread_id=telegram_message_thread_id)

            elif stickers:
                sticker = stickers[0]
                if sticker.format == StickerFormatType.apng or sticker.format == StickerFormatType.gif:
                    await telegram_bot.send_animation(telegram_chat_id, sticker.url, caption=result, show_caption_above_media=True, message_thread_id=telegram_message_thread_id)
                elif sticker.format == StickerFormatType.png:
                    await telegram_bot.send_photo(telegram_chat_id, sticker.url, result, show_caption_above_media=True, message_thread_id=telegram_message_thread_id)

            elif attachments:
                attachment = attachments[0]
                if attachment.content_type.startswith("image"):
                    if get_extension(get_filename_from_url(attachment.url)) == ".gif":
                        await telegram_bot.send_animation(telegram_chat_id, attachment.url, caption=result, show_caption_above_media=True, has_spoiler=attachment.is_spoiler(), message_thread_id=telegram_message_thread_id)
                    else:
                        await telegram_bot.send_photo(telegram_chat_id, attachment.url, result, show_caption_above_media=True, has_spoiler=attachment.is_spoiler(), message_thread_id=telegram_message_thread_id)
                elif attachment.content_type.startswith("video"):
                    await telegram_bot.send_video(telegram_chat_id, attachment.url, caption=result, show_caption_above_media=True, has_spoiler=attachment.is_spoiler(), message_thread_id=telegram_message_thread_id)
                elif attachment.content_type.startswith("audio"):
                    await telegram_bot.send_audio(telegram_chat_id, attachment.url, result, show_caption_above_media=True, message_thread_id=telegram_message_thread_id)
                else:
                    await telegram_bot.send_document(telegram_chat_id, attachment.url, caption=result, show_caption_above_media=True, message_thread_id=telegram_message_thread_id)

            elif embeds:
                embed = embeds[0]
                if embed.type == "video" or embed.type == "gifv":
                    await telegram_bot.send_video(telegram_chat_id, embed.video.proxy_url or embed.video.url or embed.url, caption=result, show_caption_above_media=True, message_thread_id=telegram_message_thread_id)
                elif embed.type == "image":
                    if get_extension(get_filename_from_url(embed.image.proxy_url or embed.image.url or embed.url)) == ".gif":
                        await telegram_bot.send_animation(telegram_chat_id, embed.video.proxy_url or embed.video.url or embed.url, caption=result, show_caption_above_media=True, message_thread_id=telegram_message_thread_id)
                    else:
                        await telegram_bot.send_photo(telegram_chat_id, embed.image.proxy_url or embed.image.url or embed.url, result, show_caption_above_media=True, message_thread_id=telegram_message_thread_id)

    else:
        await telegram_bot.send_message(telegram_chat_id, result, message_thread_id=telegram_message_thread_id)


class DiscordBot(discord.Client):
    async def on_message(self, message):
        if message.author == self.user or message.channel.id != discord_chat_id:
            return

        text = message.system_content if message.is_system() else message.clean_content
        username = message.author.display_name or message.author.global_name or message.author.name

        emojis = []
        for match in re.finditer(r'<a?:[a-zA-Z0-9_]{,32}:[0-9]{,32}>', text):
            parsed_emoji = match.group()
            emoji = PartialEmoji.from_str(parsed_emoji)
            text = text.replace(parsed_emoji, f":{emoji.name}:")
            emojis.append(emoji)

        if message.type == discord.MessageType.reply:
            replied_to = await message.channel.fetch_message(message.reference.message_id)

            quote = replied_to.system_content if replied_to.is_system() else replied_to.clean_content
            quote_author = None
            if replied_to.author != self.user:
                quote_author = replied_to.author.global_name or replied_to.author.name

            await send_to_telegram(username, text, message.attachments, message.embeds, emojis, message.stickers, quote_author, quote)

        else:
            await send_to_telegram(username, text, message.attachments, message.embeds, emojis, message.stickers)

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
    elif message.sticker and not message.sticker.is_animated:
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
