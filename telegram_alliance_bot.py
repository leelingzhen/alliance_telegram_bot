import logging
import os
import alliance
import json

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

def restricted(func):
    """Restrict usage of func to allowed users only and replies if necessary"""
    @wraps(func)
    def wrapped(update, context, *args, **kwargs):
        with open(os.path.join(".secrets", "membership.json"), "r") as f:
            member_dict = json.load(f)
        user_id = update.effective_user.id
        if user_id not in member_dict['members']:
            print("WARNING: Unauthorized access denied for {}.".format(user_id))
            update.message.reply_text('you do not have access to this bot, please contact adminstrators')
            return  # quit function
        return func(update, context, *args, **kwargs)
    return wrapped

def send_typing_action(func):
    """Sends typing action while processing func command."""

    @wraps(func)
    def command_func(update, context, *args, **kwargs):
        context.bot.send_chat_action(chat_id=update.effective_message.chat_id, action=ChatAction.TYPING)
        return func(update, context,  *args, **kwargs)

    return command_func

#helper functions
def print_date_buttons(date_list):
    buttons = list()
    date_list = alliance.active_date_list(date_list, target_date=date.today())
    for date_option in date_list:
        date_str = date_option.date().strftime("%d-%b-%y, %A")
        callback_data = date_option.strftime("%d-%m-%Y %H:%M:%S")
        button = InlineKeyboardButton(text=date_str, callback_data=callback_data)
        buttons.append([button])
    reply_markup = InlineKeyboardMarkup(buttons)
    return reply_markup

#telegram functions
@send_typing_action
@restricted
def start(update: Update, context: CallbackContext) -> None:
    """Send a message when the command /start is issued."""
    user = update.effective_user
    logger.info("User %s has talked to the bot!", user.first_name)
    context.bot.send_message(
            chat_id=update.effective_user.id,
            text=f'Please use the commands to talk to me!'
            )


@send_typing_action
@restricted
def choosing_date(update: Update, context: CallbackContext) -> str:
    user = update.effective_user
    logger.info("User %s is filling up his/her attendance...", user.first_name)

    attendance, details, player_profiles = alliance.get_sheet_records()
    context.user_data["attendance"] = attendance
    context.user_data["details"] = details
    context.user_data["player_profiles"] = player_profiles

    reply_markup = print_date_buttons(attendance.columns)
    update.message.reply_text("Choose Training Date:", reply_markup=reply_markup)
    return "indicate_attendance"


def indicate_attendance(update: Update, context: CallbackContext) -> str:
    query = update.callback_query
    query.answer()
    user_id = update.effective_user.id

    #retrieve date query and store
    date_query = datetime.strptime(query.data,"%d-%m-%Y %H:%M:%S")
    context.user_data["target_date"] = date_query
    
    #retrieve data from context.user_data
    attendance_df = context.user_data["attendance"]
    player_profiles = context.user_data["player_profiles"]

    #get cell location of attendance and store
    row, column = alliance.cell_location(user_id, date_query, attendance_df, player_profiles)
    context.user_data["cell_location"] = (row, column)

    button = [
            [InlineKeyboardButton("Yes I ❤️ frisbee", callback_data="Yes")],
            [InlineKeyboardButton("No (lame)", callback_data="No")],
            ]
    reply_markup = InlineKeyboardMarkup(button)
    status = alliance.user_attendance_status(user_id, date_query, attendance_df, player_profiles)
    query.edit_message_text(
            text=f"Your attendance is indicated as \'{status}\'\n"
            "Would you like to go for training?",
            reply_markup=reply_markup
            )
    return "update_attendance"

def update_attendance(update: Update, context: CallbackContext) -> str:
    query = update.callback_query
    query.answer()
    query.edit_message_text(
            text="updating your attendance on gsheets..."
            )
    #get indicated attendance
    indicated_attendance = query.data

    #get stored data
    cell_location = context.user_data["cell_location"]
    target_date = context.user_data["target_date"]
    
    training_date = target_date.strftime("%-d %b, %a")
    training_time = target_date.strftime("%-I:%M%p")
    if indicated_attendance == "Yes":
        comment = "See you at training! 🦾🦾"
    elif indicated_attendance == "No":
        comment = "Hope to see you soon🥲🥲"

    alliance.update_cell(cell_location, indicated_attendance)
    text = f"""
    You have sucessfully updated your attendance! 🤖🤖\n
    Date: {training_date}\n
    Time: {training_time}\n
    Attendance: {indicated_attendance}\n\n""" 

    query.edit_message_text(
            text=text + comment
            )
    logger.info("User %s has filled up his/her attendance...", update.effective_user.first_name)
    return ConversationHandler.END


@send_typing_action
@restricted
def training_dates(update:Update, context: CallbackContext) -> None:
    attendance_df, details, player_profiles = alliance.get_sheet_records()
    user_id = update.effective_user.id
    date_arr = alliance.get_training_dates(attendance_df, player_profiles, user_id)
    date_s = ""
    for date in date_arr:
        date_s += date.strftime("%d %b, %a @ %-I:%M%p") + '\n'
    update.message.reply_text(f'you have registered for training on dates: \n\n{date_s}\n\nSee you then!🦿🦿')
    logger.info("User %s has queried for his/her training schedule...", update.effective_user.first_name)


@send_typing_action
def help_f(update: Update, context: CallbackContext) -> None:
    context.bot.send_message(
            chat_id=update.effective_user.id,
            text=f'I help the lazy bums in alliance fill up their attendance on the google sheets.\n\n'
            'You can use my functions by sending these commands:\n\n'
            '/attendance - to begin filling up your attendance on the google sheet\n'
            '/cancel - cancels whatever process you are doing\n'
            "/trainings - gives you a list of training dates you have signed up for\n"
            )

@send_typing_action
def cancel(update:Update, context: CallbackContext) -> int:
    update.message.reply_text(
            text="process cancelled, see you next time!"
            )
    return ConversationHandler.END

def main():

    with open(os.path.join(".secrets", "bot_credentials.json"), "r") as f:
            bot_tokens = json.load(f)

    if DEVELOPMENT:
        token = bot_tokens['dev_bot']
    else:
        token = bot_tokens['alliance_bot']

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
                },
            fallbacks=[CommandHandler('cancel',cancel)],
            )

    dispatcher.add_handler(conv_handler_attendance)
    dispatcher.add_handler(CommandHandler("start", start))
    dispatcher.add_handler(CommandHandler("trainings", training_dates))
    dispatcher.add_handler(CommandHandler("help", help_f))
    dispatcher.add_handler(CommandHandler("cancel", cancel))

    updater.start_polling()
    updater.idle()

if __name__ == "__main__":
    main()
