from discord import StickerFormatType

from utils.utils import AttachmentType, get_extension, get_filename_from_url, get_url_params


def get_emoji_type(emoji) -> AttachmentType:
    return AttachmentType.ANIMATION if emoji.animated else AttachmentType.IMAGE


def get_sticker_type(sticker) -> AttachmentType:
    if sticker.format == StickerFormatType.apng or sticker.format == StickerFormatType.gif:
        return AttachmentType.ANIMATION
    elif sticker.format == StickerFormatType.png:
        return AttachmentType.IMAGE


def get_attachment_type(attachment) -> AttachmentType:
    if attachment.content_type.startswith("image"):
        if get_extension(get_filename_from_url(attachment.url)) == ".gif":
            return AttachmentType.ANIMATION
        else:
            return AttachmentType.IMAGE
    elif attachment.content_type.startswith("video"):
        return AttachmentType.VIDEO
    elif attachment.content_type.startswith("audio"):
        return AttachmentType.AUDIO
    else:
        return AttachmentType.DOCUMENT


def get_embed_type(embed) -> AttachmentType:
    print(embed.type)
    if embed.type == "video":
        return AttachmentType.VIDEO
    elif embed.type == "gifv":
        return AttachmentType.ANIMATION
    elif embed.type == "image":
        url = embed.image.proxy_url or embed.image.url or embed.url
        if get_extension(get_filename_from_url(url)) == ".gif":
            return AttachmentType.ANIMATION
        else:
            return AttachmentType.IMAGE


def format_message(text, username, quote_text, quote_username):
    result = f"**{username}**: {text}"

    if not quote_text:
        return result

    quote_text = quote_text.replace("\n", "\n> ")
    if quote_username:
        return f"> **{quote_username}**: {quote_text}\n{result}"
    else:
        return f"> {quote_text}\n{result}"
