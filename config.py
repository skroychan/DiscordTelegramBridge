import json


def read_config():
    with open('config.json') as config_file:
        return json.load(config_file)


config = read_config()

discord_token = config['discord']['token']
discord_chat_id = config['discord']['chatId']

telegram_token = config['telegram']['token']
telegram_chat_id = config['telegram']['chatId']
telegram_message_thread_id = config['telegram'].get('threadId', None)
telegram_bot_id = config['telegram']['botId']
