import re


def escape_markdown(string):
    string = string or str()
    return re.sub(r"([_\*\[\]\(\)~`>#+\-=|\{\}\.!])", r"\\\1", string)


def format_message(text, username, quote_text, quote_username):
    result = f"*{escape_markdown(username)}*: {escape_markdown(text)}"

    if not quote_text:
        return result

    quote_text = escape_markdown(quote_text).replace("\n", "\n>")
    quote_username = escape_markdown(quote_username)
    if quote_username:
        return f">*{quote_username}*: {quote_text}\n{result}"
    else:
        return f">{quote_text}\n{result}"
