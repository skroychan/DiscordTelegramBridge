from enum import Enum
import io, aiohttp
import os
from urllib.parse import urlparse, unquote


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


class AttachmentType(Enum):
    IMAGE = "image"
    ANIMATION = "animation"
    VIDEO = "video"
    AUDIO = "audio"
    DOCUMENT = "document"


class Attachment:
    def __init__(self, url, attachment_type=AttachmentType.DOCUMENT, is_spoiler=False, filename=None):
        self.url = url
        self.attachment_type = attachment_type
        self.is_spoiler = is_spoiler
        self.filename = filename or get_filename_from_url(url)
