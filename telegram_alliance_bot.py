import logging
import os
import alliance

from datetime import date, datetime
from functools import wraps

from telegram import (
        Update,
        ForceReply,
        InlineKeyboardButton,
        InlineKeyboardMarkup,
        ChatAction,
        )
from telegram.bot import Bot, BotCommand
from telegram.ext import (
        Updater,
        CommandHandler,
        MessageHandler,
        Filters,
        CallbackContext,
        ConversationHandler,
        CallbackQueryHandler,
        )

DEVELOPMENT = True

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)

logger = logging.getLogger(__name__)

def read_token(filename: str) -> str:
    with open(filename, 'r', encoding='utf-8') as f:
        token = f.read().rstrip()
    return token

def send_typing_action(func):
    """Sends typing action while processing func command."""

    @wraps(func)
    def command_func(update, context, *args, **kwargs):
        context.bot.send_chat_action(chat_id=update.effective_message.chat_id, action=ChatAction.TYPING)
        return func(update, context,  *args, **kwargs)

    return command_func

@send_typing_action
def start(update: Update, context: CallbackContext) -> None:
    """Send a message when the command /start is issued."""
    user = update.effective_user
    user_id = update.message.from_user.id
    logger.info("User %s has talked to the bot!", user.first_name)
    update.message.reply_markdown_v2(
        #fr'Hi {user.mention_markdown_v2()}\!',
        fr'Hi {user.username}, Hi {user_id}, Hi {user.id}, repeating what you said: {update.message.text}',
        #force replies
        #reply_markup=ForceReply(selective=False),
    )
    context.bot.send_message(
            chat_id=update.effective_user.id,
            text=f'Please use the commands to talk to me!'
            )


def print_date_buttons():
    df = alliance.get_attendance_df(100)
    date_ls = alliance.active_date_list(df.columns)
    buttons = list()
    for date_option in date_ls:
        date_str = date_option.date().strftime("%d-%b-%y, %A")
        callback_data = date_option.date().strftime("%d-%m-%Y")
        button = InlineKeyboardButton(text=date_str, callback_data=callback_data)
        buttons.append([button])
    reply_markup = InlineKeyboardMarkup(buttons)
    return reply_markup

@send_typing_action
def choosing_date(update: Update, context: CallbackContext) -> str:
    user = update.effective_user
    logger.info("User %s is filling up his/her attendance...", user.first_name)
    reply_markup = print_date_buttons()
    update.message.reply_text("Choose Training Date:", reply_markup=reply_markup)
    return "indicate_attendance"

@send_typing_action
def choosing_date_again(update: Update, context:CallbackContext) -> str:
    query = update.callback_query
    query.answer()
    user = update.effective_user
    logger.info("User %s is filling up his/her attendance...", user.first_name)
    reply_markup = print_date_buttons()
    query.edit_message_text("Choose Training Date:", reply_markup=reply_markup)
    return "indicate_attendance"


@send_typing_action
def indicate_attendance(update: Update, context: CallbackContext) -> str:
    #buttons should have call back data of "yes" or "no"
    query = update.callback_query
    query.answer()
    query.edit_message_text(
            text="Loading..."
            )
    attendance_df, player_profiles = alliance.get_2_dataframes()
    user_id = update.effective_user.id
    date_query = datetime.strptime(query.data,"%d-%m-%Y")
    row, column = alliance.cell_location(user_id, date_query, attendance_df, player_profiles)
    button = [
            [InlineKeyboardButton("Yes I ❤️ frisbee", callback_data=f"Y,{row},{column},{date_query}")],
            [InlineKeyboardButton("No (lame)", callback_data=f"N,{row},{column},{date_query}")],
            ]
    reply_markup = InlineKeyboardMarkup(button)
    #run script to update attendance here
    status = alliance.user_attendance_status(user_id, date_query, attendance_df, player_profiles)
    query.edit_message_text(
            text=f"Your attendance is indicated as \'{status}\'\n"
            "Would you like to go for training?",
            reply_markup=reply_markup
            )
    return "update_attendance"

@send_typing_action
def update_attendance(update: Update, context: CallbackContext) -> str:
    #run script to update the persons attendance on the sheet
    #buttons should have call back data of "update another date", "done"
    query = update.callback_query
    query.answer()
    alliance.update_cell(query.data)
    button = [
            [InlineKeyboardButton("update attendance again!", callback_data="choose_date")],
            [InlineKeyboardButton("Bye", callback_data="done")],
            ]
    reply_markup = InlineKeyboardMarkup(button)
    if query.data[0] == "Y":
        text = "See you at training! 🦾🦾"
    elif query.data[0] == "N":
        text = "Hope to see you 🥲🥲"
    query.edit_message_text(
            text=text, reply_markup=reply_markup
            )
    logger.info("User %s has filled up his/her attendance...", update.effective_user.first_name)
    return "finish"

def end_update_attendance(update:Update, context: CallbackContext) -> int:
    query = update.callback_query
    query.answer()
    query.edit_message_text(
            text="meep morp🤖🤖"
            )
    return ConversationHandler.END

@send_typing_action
def training_dates(update:Update, context: CallbackContext) -> None:
    attendance_df, player_profiles = alliance.get_2_dataframes()
    user_id = update.effective_user.id
    date_arr = alliance.get_training_dates(attendance_df, player_profiles, user_id)
    date_s = ""
    for date in date_arr:
        date_s += date.strftime("%d-%b-%y, %a") + '\n'
    update.message.reply_text(f'your training dates are: \n{date_s}')


@send_typing_action
def help_f(update: Update, context: CallbackContext) -> None:
    context.bot.send_message(
            chat_id=update.effective_user.id,
            text=f'I help the lazy bums in alliance fill up their attendance on the google sheets.\n\n'
            'You can use my functions by sending these commands:\n\n'
            '/attendance - to begin filling up your attendance on the google sheet\n'
            '/cancel - cancels whatever process you are doing\n'
            )

@send_typing_action
def cancel(update:Update, context: CallbackContext) -> int:
    context.bot.send_message(chat_id=update.effective_chat.id,
            text="process cancelled, see you next time!"
            )
    return ConversationHandler.END

def main():
    if DEVELOPMENT:
        token = read_token(os.path.join(".secrets", "development_bot_token.txt"))
    else:
        token = read_token(os.path.join(".secrets", "bot_token.txt"))

    #setting command list
    commands = [
            BotCommand("start", "to start a the bot"),
            BotCommand("attendance", "to update attendance on alliance gsheets"),
            BotCommand("trainings", "to give you a list of training dates you are attending"),
            BotCommand("cancel", "cancel any existing operation"),
            BotCommand("help", "help"),
            ]
    Bot(token).set_my_commands(commands)

    updater = Updater(token)

    #dispatcher to register handlers
    dispatcher = updater.dispatcher

    conv_handler_attendance = ConversationHandler(
            entry_points=[CommandHandler("attendance", choosing_date)],
            states={
                "indicate_attendance": [
                    CallbackQueryHandler(indicate_attendance)
                    ],
                "update_attendance" : [
                    CallbackQueryHandler(update_attendance)
                    ],
                "finish" : [
                    CallbackQueryHandler(choosing_date_again, pattern="choose_date"),
                    CallbackQueryHandler(end_update_attendance, pattern="done"),
                    ],

                },
            fallbacks=[CommandHandler('cancel',cancel)],
            )

    dispatcher.add_handler(conv_handler_attendance)
    dispatcher.add_handler(CommandHandler("start", start))
    dispatcher.add_handler(CommandHandler("trainings", training_dates))
    dispatcher.add_handler(CommandHandler("help", help_f))

    updater.start_polling()
    updater.idle()

if __name__ == "__main__":
    main()
