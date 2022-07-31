import logging

from telegram.ext import Updater
from telegram import Update
from telegram.ext import CallbackContext
from telegram.ext import CommandHandler
import telegram
import os

#enable basic logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                     level=logging.INFO)

def get_bot_token(filename):
    with open(filename) as f:
        bot_token = f.read().rstrip()
    return bot_token

def start(update: Update, context: CallbackContext):
    context.bot.send_message(chat_id=update.effective_chat.id, text = "I am a bot, please talk to me")

def send_custom_message(msg: str, chat_id, parse_mode="HTML"):
    bot_token = get_bot_token(os.path.join(".secrets", "bot_token.txt"))
    bot = telegram.Bot(token=bot_token)
    try:
        bot.send_message(chat_id=chat_id, text=msg, parse_mode=parse_mode)
    except telegram.error.Unauthorized:
        return False
    except telegram.error.BadRequest:
        return False
    return True

"""
start_handler = CommandHandler("start", start)

updater = Updater(token=bot_token, use_context=True)
dispatcher = updater.dispatcher
dispatcher.add_handler(start_handler)
"""
