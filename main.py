import re

import discord
from discord import PartialEmoji
from telebot.async_telebot import AsyncTeleBot
from telebot.types import InputMediaPhoto, InputMediaVideo, InputMediaAudio, InputMediaDocument

from config import discord_token, discord_chat_id, telegram_token, telegram_chat_id, telegram_message_thread_id, telegram_bot_id, telegram_max_attachments
from utils import utils, discord_utils, telegram_utils
from utils.utils import Attachment, AttachmentType


telegram_bot = AsyncTeleBot(telegram_token, parse_mode="MarkdownV2")


async def send_to_discord(username, text, attachment=None, quote_username=None, quote_text=None):
    channel = discord_bot.get_channel(discord_chat_id)
    if channel:
        message = discord_utils.format_message(text, username, quote_text, quote_username)

        if attachment:
            data = await utils.download_file(attachment.url)
            file = discord.File(data, attachment.filename, spoiler=attachment.is_spoiler)
            await channel.send(message, file=file)

        else:
            await channel.send(message)


async def send_to_telegram(username, text, attachments=[], quote_username=None, quote_text=None):
    message = telegram_utils.format_message(text, username, quote_text, quote_username)

    if attachments:
        if len(attachments) > 1:
            media_group = []

            for attachment in attachments:
                if attachment.attachment_type == AttachmentType.IMAGE:
                    media_group.append(InputMediaPhoto(attachment.url, show_caption_above_media=True, has_spoiler=attachment.is_spoiler))
                elif attachment.attachment_type == AttachmentType.ANIMATION:
                    media_group.append(InputMediaAnimation(attachment.url, show_caption_above_media=True, has_spoiler=attachment.is_spoiler))
                elif attachment.attachment_type == AttachmentType.VIDEO:
                    media_group.append(InputMediaVideo(attachment.url, show_caption_above_media=True, has_spoiler=attachment.is_spoiler))
                elif attachment.attachment_type == AttachmentType.AUDIO:
                    media_group.append(InputMediaAudio(attachment.url, show_caption_above_media=True))
                else:
                    media_group.append(InputMediaDocument(attachment.url))

            media_group[0].caption = message

            if len(media_group) <= 10:
                await telegram_bot.send_media_group(telegram_chat_id, media_group, message_thread_id=telegram_message_thread_id)
            else:
                for i in range(0, min(len(media_group), telegram_max_attachments), 10):
                    batch = media_group[i:i+10]
                    await telegram_bot.send_media_group(telegram_chat_id, batch, message_thread_id=telegram_message_thread_id)

        else:
            attachment = attachments[0]
            if attachment.attachment_type == AttachmentType.IMAGE:
                await telegram_bot.send_photo(telegram_chat_id, attachment.url, message, show_caption_above_media=True, has_spoiler=attachment.is_spoiler, message_thread_id=telegram_message_thread_id)
            elif attachment.attachment_type == AttachmentType.ANIMATION:
                await telegram_bot.send_animation(telegram_chat_id, attachment.url, caption=message, show_caption_above_media=True, has_spoiler=attachment.is_spoiler, message_thread_id=telegram_message_thread_id)
            elif attachment.attachment_type == AttachmentType.VIDEO:
                await telegram_bot.send_video(telegram_chat_id, attachment.url, caption=message, show_caption_above_media=True, has_spoiler=attachment.is_spoiler, message_thread_id=telegram_message_thread_id)
            elif attachment.attachment_type == AttachmentType.AUDIO:
                await telegram_bot.send_audio(telegram_chat_id, attachment.url, message, show_caption_above_media=True, message_thread_id=telegram_message_thread_id)
            else:
                await telegram_bot.send_document(telegram_chat_id, attachment.url, caption=message, message_thread_id=telegram_message_thread_id)

    else:
        await telegram_bot.send_message(telegram_chat_id, message, message_thread_id=telegram_message_thread_id)


class DiscordBot(discord.Client):
    async def on_message(self, message):
        if message.author == self.user or message.channel.id != discord_chat_id:
            return

        if not message.embeds:
            message = await message.fetch() # sometimes helps embeds to appear

        text = message.system_content if message.is_system() else message.clean_content
        username = message.author.display_name or message.author.global_name or message.author.name

        attachments = []

        for match in re.finditer(r'<a?:[a-zA-Z0-9_]{,32}:[0-9]{,32}>', text):
            parsed_emoji = match.group()
            emoji = PartialEmoji.from_str(parsed_emoji)
            text = text.replace(parsed_emoji, f":{emoji.name}:")

            attachments.append(Attachment(emoji.url, discord_utils.get_emoji_type(emoji)))

        for sticker in message.stickers:
            attachments.append(Attachment(sticker.url, discord_utils.get_sticker_type(sticker)))

        for attachment in message.attachments:
            attachments.append(Attachment(attachment.url, discord_utils.get_attachment_type(attachment), attachment.is_spoiler(), attachment.filename))

        for embed in message.embeds:
            url = embed.image.proxy_url or embed.image.url or embed.video.proxy_url or embed.video.url or embed.url
            if text == url or text == embed.url:
                text = ""
            attachments.append(Attachment(url, discord_utils.get_embed_type(embed)))

        if message.type == discord.MessageType.reply:
            replied_to = await message.channel.fetch_message(message.reference.message_id)

            quote = replied_to.system_content if replied_to.is_system() else replied_to.clean_content
            quote_author = None
            if replied_to.author != self.user:
                quote_author = replied_to.author.global_name or replied_to.author.name

            await send_to_telegram(username, text, attachments, quote_author, quote)

        else:
            await send_to_telegram(username, text, attachments)

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
    
    attachment = None

    if message.photo:
        photo = max(message.photo, key=lambda p: p.file_size)
        url = await telegram_bot.get_file_url(photo.file_id)
        attachment = Attachment(url, AttachmentType.IMAGE, message.has_media_spoiler)
    elif message.animation:
        url = await telegram_bot.get_file_url(message.animation.file_id)
        attachment = Attachment(url, AttachmentType.ANIMATION, message.has_media_spoiler, message.animation.file_name)
    elif message.audio:
        url = await telegram_bot.get_file_url(message.audio.file_id)
        attachment = Attachment(url, AttachmentType.AUDIO, message.has_media_spoiler, message.audio.file_name)
    elif message.sticker and not message.sticker.is_animated:
        url = await telegram_bot.get_file_url(message.sticker.file_id)
        attachment_type = AttachmentType.ANIMATION if message.sticker.is_video else AttachmentType.IMAGE
        attachment = Attachment(url, attachment_type, message.has_media_spoiler)
    elif message.video:
        url = await telegram_bot.get_file_url(message.video.file_id)
        attachment = Attachment(url, AttachmentType.VIDEO, message.has_media_spoiler, message.video.file_name)
    elif message.video_note:
        url = await telegram_bot.get_file_url(message.video_note.file_id)
        attachment = Attachment(url, AttachmentType.VIDEO, message.has_media_spoiler)
    elif message.voice:
        url = await telegram_bot.get_file_url(message.voice.file_id)
        attachment = Attachment(url, AttachmentType.AUDIO, message.has_media_spoiler)
    elif message.document:
        url = await telegram_bot.get_file_url(message.document.file_id)
        attachment = Attachment(url, AttachmentType.DOCUMENT, message.has_media_spoiler, message.document.file_name)

    if message.reply_to_message:
        if message.quote:
            quote = message.quote.text
        else:
            quote = message.reply_to_message.text or message.reply_to_message.caption
        quote_author = None
        if message.reply_to_message.from_user.id != telegram_bot_id:
            quote_author = message.reply_to_message.from_user.first_name

        await send_to_discord(username, text, attachment, quote_author, quote)

    else:
        await send_to_discord(username, text, attachment)


intents = discord.Intents.default()
intents.message_content = True
discord_bot = DiscordBot(intents=intents)
discord_bot.run(discord_token)
