from PronoteBot import PronoteBot
from dotenv import load_dotenv
import os
from config import session, Config
import time

if __name__ == "__main__":
    if os.path.exists('.env'):
        load_dotenv()

    while session.query(Config).count() == 0:
        print('Please configure your app with "python config.py" More information on https://github.com/Bapt5/PronoteBot#readme')
        time.sleep(60)

    bot = PronoteBot(
        os.environ.get('URL_PRONOTE'),
        os.environ.get('USERNAME_PRONOTE'),
        os.environ.get('PASSWORD_PRONOTE'),
        os.environ.get('ENT'),
        os.environ.get('TOKEN_PUSHBULLET'),
        os.environ.get('CALENDAR_ID'),
        os.environ.get('NAME_MICROSOFT_TODO_LIST')
    )
    bot.run()
