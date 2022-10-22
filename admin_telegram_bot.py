import logging
import os
import alliance
import pandas as pd
import json

from datetime import date, datetime, timedelta
from functools import wraps
from telegram_training_bot import (
        print_date_buttons,
        page_change
        )

from telegram import (
        Update,
        ForceReply,
        InlineKeyboardButton,
        ReplyKeyboardMarkup,
        ReplyKeyboardRemove,
        InlineKeyboardMarkup,
        ChatAction,
        CallbackQuery, #for type checking
        MessageEntity

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
from telegram.error import Unauthorized, BadRequest

DEVELOPMENT = alliance.environment_var()

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)

logger = logging.getLogger(__name__)

def get_membership(filename=os.path.join('.secrets', 'membership.json')) -> dict:
    with open(filename, 'r') as membership_f:
        membership = json.load(membership_f)
    return membership

def update_membership(membership: dict, filename=os.path.join('.secrets', 'membership.json')) -> None:
    with open(filename, 'w') as membership_f:
        json.dump(membership, membership_f, indent=4)
    return None

def get_tokens(filename=os.path.join('.secrets', 'bot_credentials.json')) -> dict:
    with open(filename, 'r') as bot_token_file:
        bot_tokens=json.load(bot_token_file)
    return bot_tokens

def send_custom_msg(msg: str, chat_id: str, bot_messenger: Bot, parse_mode=None, entities=None):
    try:
        bot_messenger.send_message(chat_id, text=msg, parse_mode=parse_mode, entities=entities)
    except Unauthorized:
        return False
    except BadRequest:
        return False
    return True

def get_usernames(player_profiles: pd.DataFrame, name_list: list, token_key="alliance_bot") -> str:
    bot_token = get_tokens()[token_key]
    bot = Bot(token=bot_token)

    for name in name_list:
        chat_id = player_profiles.loc[name]["telegram_id"]
        try:
            user = bot.get_chat(chat_id)
        except (BadRequest, Unauthorized):
            text = f"{name}, "
            continue
        if user.username:
            text = f"@{user.username}, "
        else:
            text = f"{user.first_name}, "

        yield text

def mass_send(msg: str, df_send: pd.DataFrame, parse_mode=None, entities=None) -> str:
    #getting tokens
    bot_tokens = get_tokens()
    alliance_bot = Bot(token=bot_tokens['alliance_bot'])

    #getting checking dev
    if DEVELOPMENT:
        bot_messenger = Bot(token=bot_tokens['dev_bot'])
    else:
        bot_messenger = Bot(token=bot_tokens['alliance_bot'])

    for name, row in df_send.iterrows():
        try:
            bot_messenger.send_message(
                    chat_id=row['telegram_id'],
                    text=msg,
                    parse_mode=parse_mode,
                    entities=entities
                    )
        except (Unauthorized, BadRequest):
            yield name
        else:
            yield ""

def send_typing_action(func):
    """Sends typing action while processing func command."""

    @wraps(func)
    def command_func(update, context, *args, **kwargs):
        context.bot.send_chat_action(chat_id=update.effective_message.chat_id, action=ChatAction.TYPING)
        return func(update, context,  *args, **kwargs)

    return command_func

def restricted_admin(func):
    """Restrict usage of func to allowed users only and replies if necessary"""
    @wraps(func)
    def wrapped(update, context, *args, **kwargs):
        with open(os.path.join(".secrets", "membership.json"), "r") as f:
            member_dict = json.load(f)
        user_id = update.effective_user.id
        if user_id not in member_dict['admins']:
            print("WARNING: Unauthorized access denied for {}.".format(user_id))
            update.message.reply_text('you do not have access to this bot, please contact adminstrators')
            return  # quit function
        return func(update, context, *args, **kwargs)
    return wrapped

@send_typing_action
@restricted_admin
def start(update: Update, context: CallbackContext) -> None:
    """Send a message when the command /start is issued."""
    user = update.effective_user
    user_id = update.message.from_user.id
    logger.info("User %s has talked to the bot!", user.first_name)
    context.bot.send_message(
            chat_id=update.effective_user.id,
            text=f'Please use the commands to talk to me!'
            )

@send_typing_action
@restricted_admin
def choosing_date(update: Update, context: CallbackContext) -> int:
    user = update.effective_user
    logger.info("User %s has started a process.", user.first_name)

    ##get sheet records and store
    attendance, details, player_profiles = alliance.get_sheet_records()
    context.user_data["attendance"] = attendance
    context.user_data["details"] = details
    context.user_data["player_profiles"] = player_profiles
    context.user_data["page"] = 0

    reply_markup = print_date_buttons(attendance.columns, 0)
    if reply_markup["inline_keyboard"] == []:
        update.message.reply_text("There seems to be no further events planned, please add a new date column to the google sheets!")
        logger.info("process ended as there were no training dates")
        return ConversationHandler.END
    update.message.reply_text("Choose Training Date:", reply_markup=reply_markup)
    return 1


def generate_attendance(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    query.answer()

    #retrieving player profiles 
    attendance_df = context.user_data["attendance"]
    player_profiles = context.user_data["player_profiles"]

    #retrieving date from date query 
    date_query = datetime.strptime(query.data,"%d-%m-%Y %H:%M:%S")

    #sorting attendance 
    output_text = "Sorting attendance...\n"
    query.edit_message_text(text=output_text)
    attendance_dict = alliance.get_participants(attendance_df, date_query, player_profiles)
    attending_male, attending_female = alliance.gender_sorter(attendance_dict["attending"], player_profiles)

    #generating print out
    text = f"Attendance for {date_query.strftime('%d-%b-%y, %a')}\n\n"
    text += f"Attending boys: {len(attending_male)}\n"
    for name in attending_male:
        text += name + "\n"
    text += f"\nAttending girls: {len(attending_female)}\n"
    for name in attending_female:
        text += name + "\n"
    text += f"\nAbsentees: {len(attendance_dict['absent'])}\n"
    for name in attendance_dict["absent"]:
        text += name + "\n"
    text += f"\nNot yet indicated: {len(attendance_dict['not indicated'])}\n"
    for name in attendance_dict["not indicated"]:
        text += name + "\n"
        
    '''
    query.edit_message_text(
            text=f"Sorting attendance...\nGetting usernames... 0/{len(attendance_dict['not indicated'])}\n"
            )

    username_generator = get_usernames(player_profiles, attendance_dict["not indicated"])
    for i, name in enumerate(attendance_dict["not indicated"]):
        username = next(username_generator)
        text += username
        query.edit_message_text(
                text=f"Sorting attendance...\nGetting usernames... {i+1}/{len(attendance_dict['not indicated'])}"
                )
    '''

    query.edit_message_text(
            text=text
            )

    logger.info("Attendance summary request completed successfuly by User %s", update.effective_user.first_name)

    return ConversationHandler.END




def send_reminders(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    query.answer()
    query.edit_message_text(
            text="Parsing gsheets..."
            )
    target_date = datetime.strptime(query.data, "%d-%m-%Y %H:%M:%S")

    #getting sheet data
    attendance, details, player_profiles = alliance.get_sheet_records()
    attendance_dict = alliance.get_participants(attendance, target_date, player_profiles)

    #getting not indicated df
    name_list = attendance_dict["not indicated"]
    not_indicated_df = player_profiles.loc[player_profiles.index.isin(name_list)]

    #parsing message from file
    query.edit_message_text(
            text="Parsing gsheets... done.\nCrafting reminder message...\n"
            )
    date_query = target_date.strftime('%d-%b-%y, %A')
    remind_msg = alliance.read_msg_from_file(os.path.join('messages', 'not_indicated_message.txt'), date_query)

    query.edit_message_text(
            text=f"Parsing gsheets... done.\nCrafting reminder message... done.\nSending messages... 0/{len(name_list)}\n"
            )
    send_message_generator = mass_send(
            msg=remind_msg,
            df_send=not_indicated_df,
            parse_mode='HTML'
            )
    unsent_names = list()
    for i, _ in enumerate(name_list):
        unsent_name = next(send_message_generator)
        if unsent_name != "":
            unsent_names.append(unsent_name)
        query.edit_message_text(
                text=f"Parsing gsheets... done.\nCrafting reminder message... done.\nSending messages... {i + 1}/{len(name_list)}\n"
                )

    query.edit_message_text(
            text=f"Sending messages... done.\nGetting unsent usernames 0/{len(unsent_names)}"
            )
    username_generator = get_usernames(
            player_profiles, 
            unsent_names)
    unsucessful_sends= ''
    for i, _ in enumerate(unsent_names):
        unsucessful_sends += next(username_generator)
        query.edit_message_text(
        text=f"Sending messages... done.\nGetting unsent usernames {i+1}/{len(unsent_names)}"
        )
        
    query.edit_message_text(
            text=f"Reminders have been sent sucessfully for {date_query}\n\nUnsucessful sends: \n{unsucessful_sends}"
            )    

    logger.info("reminders sent successfuly by User %s", update.effective_user.first_name)
    return ConversationHandler.END

@restricted_admin
@send_typing_action
def announce_all(update:Update, context: CallbackContext) -> int:
    logger.info("User %s initiated process: announce all", update.effective_user.first_name)
    #conversation state
    conv_state = 0
    context.user_data['conv_state'] = conv_state

    update.message.reply_text(
            'You will be sending an annoucement to all active players in alliance through @alliance_training_bot. '
            'Send /cancel to cancel the process\n\n'
            'Please send me your message here!'
            )

    context.user_data['conv_state'] += 1
    return context.user_data['conv_state']

@send_typing_action
def confirm_message(update:Update, context: CallbackContext) -> int:
    buttons = [
            [InlineKeyboardButton(text="Confirm", callback_data="forward")],
            [InlineKeyboardButton(text="Edit Message", callback_data="back")]
            ]

    #getting announcement message and entities, then storing 
    announcement = update.message.text
    announcement_entities = update.message.entities
    context.user_data['announcement'] = announcement
    context.user_data['announcement_entities'] = announcement_entities
    bot_message = update.message.reply_text(
            'You have sent me: \n\n',
            )
    update.message.reply_text(
            text=announcement ,
            entities=announcement_entities
            )
    update.message.reply_text(
            text="Confirm message?",
            reply_markup=InlineKeyboardMarkup(buttons)
            )

    context.user_data['conv_state'] += 1
    return context.user_data['conv_state']

@send_typing_action
def edit_msg(update:Update, context:CallbackContext) -> int:
    query = update.callback_query
    query.answer()
    query.edit_message_text(
            'Please send me your message here again!'
            )

    context.user_data['conv_state'] -= 1
    return context.user_data['conv_state']

@send_typing_action
def send_message(update:Update, context:CallbackContext) -> None:
    query = update.callback_query
    query.answer()
    user = update.effective_user
    msg = context.user_data['announcement'] + f"\n\n\n\n- @{update.effective_user.username}"
    msg_entities= context.user_data['announcement_entities']

    #get gsheets
    admin_msg_text = "Parsing gsheets..."
    admin_msg = query.edit_message_text(text=admin_msg_text)
    _, _, player_profiles = alliance.get_sheet_records(attendance=False, details=False)

    #filter active players
    admin_msg_text += "done.\ngetting names..."
    admin_msg.edit_text(admin_msg_text)
    active_players = player_profiles[player_profiles['status'] == 'Active']

    admin_msg_text +="done.\nSending announcements... 0/{active_players.shape[0]}"
    send_message_generator = mass_send(
            msg=msg,
            df_send=active_players,
            entities=msg_entities
            )
    unsent_names = list()
    for i in range(active_players.shape[0]):
        unsent_name = next(send_message_generator)
        if unsent_name != "":
            unsent_names.append(unsent_name)
        admin_msg.edit_text(f"Sending announcements... {i+1}/{active_players.shape[0]}")

    admin_msg.edit_text(f"Sending announcements... done.\nGetting unsent usernames... 0/{len(unsent_names)}")
    username_generator = get_usernames(
            player_profiles,
            unsent_names)
    unsucessful_sends= ''
    for i, _ in enumerate(unsent_names):
        unsucessful_sends += next(username_generator)
        admin_msg.edit_text(
        text=f"Sending announcements... done.\nGetting unsent usernames {i+1}/{len(unsent_names)}"
        )

    admin_msg.edit_text(
            "Sending announcements complete. list of uncompleted sends: \n\n" + unsucessful_sends,
            )

    logger.info("User %s sucessfully sent announcements", user.first_name)
    return ConversationHandler.END


@send_typing_action
def write_message(update:Update, context:CallbackContext) -> int:
    query = update.callback_query
    query.answer()
    target_date = datetime.strptime(query.data, '%d-%m-%Y %H:%M:%S')
    context.user_data['target_date'] = target_date
    query.edit_message_text(
            f"You have choosen training on <u>{target_date.strftime('%d-%b, %a @ %-I:%M%p')}</u>.\n\n"
            "Write your message to players who are <u>attending</u> and <u>active players who have not indicated</u> attendance here. "
            "If you have choosen an earlier date, you can send <b>training summaries</b> to players who attended too!",
            parse_mode="HTML"
            )
    context.user_data['conv_state'] = 2
    return context.user_data['conv_state']


@send_typing_action
def send_training_message(update:Update, context: CallbackContext) -> int:
    query = update.callback_query
    query.answer()
    #getting relevant data
    target_date = context.user_data['target_date']
    comment = f"Message for training on {target_date.strftime('%d-%b, %a @ %-I:%M%p')}"
    msg = f"{context.user_data['announcement']}\n\n{comment}\n\n- @{update.effective_user.username}"
    msg_entities = context.user_data['announcement_entities']

    msg_entities.append(
            MessageEntity(
                type="italic",
                offset=len(context.user_data['announcement']) + 2,
                length=len(comment)
                )
            )

    attendance = context.user_data['attendance']
    player_profiles = context.user_data['player_profiles']

    #sorting attendance and getting df
    admin_msg=query.edit_message_text(
            "Sorting attendance...\n"
            )
    attendance_dict = alliance.get_participants(attendance, target_date, player_profiles)
    active_players = attendance_dict['attending'] + attendance_dict['not indicated']
    active_players_df = player_profiles.loc[player_profiles.index.isin(active_players)]

    admin_msg.edit_text(
            "Sorting attendance...\n done."
            f"Sending training messages... 0/{len(active_players)}"
            )
    send_message_generator=mass_send(
            msg=msg,
            df_send=active_players_df,
            entities=msg_entities
            )

    unsent_names = list()
    for i, _ in enumerate(active_players):
        unsent_name = next(send_message_generator)
        if unsent_name != "":
            unsent_names.append(unsent_name)
        admin_msg.edit_text(f"Sending training messages... {i+1}/{len(active_players)}")

    admin_msg.edit_text(f"Sending training messages... done.\nGetting unsent usernames... 0/{len(unsent_names)}")
    username_generator = get_usernames(
            player_profiles,
            unsent_names)
    unsucessful_sends= ''
    for i, _ in enumerate(unsent_names):
        unsucessful_sends += next(username_generator)
        admin_msg.edit_text(
        text=f"Sending training messages... done.\nGetting unsent usernames {i+1}/{len(unsent_names)}"
        )

    admin_msg.edit_text(
            "Sending training messages complete. list of uncompleted sends: \n\n" + unsucessful_sends,
            )

    logger.info("User %s sucessfully sent training messages", update.effective_user.first_name)
    return ConversationHandler.END

@send_typing_action
@restricted_admin
def get_id(update:Update, context: CallbackContext) -> int:
    user = update.effective_user
    logger.info("User %s is adding a member to alliance bot", user.first_name)
    update.message.reply_text(
            "<b>WARNING</b> you are entering <b>DANGER ZONE</b> please read the following carefully.\n\n"
            "You are planning to give a user access to @alliance_training_bot\n"
            "Please ensure you have fulfilled the following before you continue:\n\n"
            "1. Add user to the google attendance sheets, to both <b><u>attendance sheet</u></b> and <b><u>'Player Profiles'</u></b> sheets.\n"
            "2. Ensure the the names are <b><u>exactly the same</u></b> in the attendance sheet and 'Player Profiles sheets'\n"
            "3. Ensure that all fields of 'Player Profiles have been filled, especially 'telegram_id'\n"
            "4. Ensure that the user has already initiated conversation with @alliance_training_bot\n\n"
            "Send me the telegram id of the user you would like to add! user can get his/her telegram id from @userinfobot\n",
            parse_mode='HTML'
            )
    return 1

@send_typing_action
def add_member(update:Update, context:CallbackContext) -> int:
    add_id = int(update.message.text)
    text = f"You have submitted '{add_id}' to be added to @alliance_training_bot\n"
    text += "Parsing gsheets...\n"
    message = update.message.reply_text(text)
    attendance_df, _, player_profiles = alliance.get_sheet_records(details=False)
    if add_id not in player_profiles['telegram_id'].values:
        text += f"{add_id} not found in Player Profiles, nothing added."
        message.edit_text(text)
        logging.info("error in adding %s process terminated", add_id)
        return ConversationHandler.END
    text += f"{add_id} found in player profiles\n"
    message = message.edit_text(text)
    add_name = player_profiles.index[player_profiles['telegram_id'] == add_id][0]
    if add_name not in attendance_df.index:
        text += f"{add_name} not found in attendance sheets, nothing added."
        message.edit_text(text)
        logging.info("error in adding %s process terminated", add_id)
        return ConversationHandler.END
    text += f"{add_id} of {add_name} found in attendance sheets.\n"
    if (player_profiles.loc[add_name] == "").sum():
        text += "missing fields in player profiles, nothing added."
        message.edit_text(text)
        logging.info("error in adding %s process terminated", add_id)
        return ConversationHandler.END
    text += f"all fields of {add_id} has been completed.\n"
    text += "Checking conversation with alliance training bot...\n" 
    message.edit_text(text)
    alliance_token = get_tokens()["alliance_bot"]
    bot = Bot(token=alliance_token)
    try:
        user = bot.get_chat(add_id)
    except (BadRequest, Unauthorized):
        text += "user has not started a conversation with the bot"
        message.edit_text(text)
        logging.info("error in adding %s process terminated", add_id)
        return ConversationHandler.END
    text += f"alliance training bot has found chat of chat_id : {add_id}, user : {user.username}\n"
    text += f"Registering @{user.username}...\n"
    message.edit_text(text)
    membership = get_membership()
    add_id = int(add_id)
    if add_id in membership['members']:
        text += f"@{user.username} is already registered"
        message.edit_text(text)
        return ConversationHandler.END
    membership['members'].append(add_id)
    update_membership(membership)
    text += f"@{user.username} registered sucessfully"
    message.edit_text(text)
    logger.info("User %s is has registered user %s to alliance bot", update.effective_user.first_name, user.first_name)
    return ConversationHandler.END

    return 1

@send_typing_action
@restricted_admin
def get_id_add_admin(update:Update, context: CallbackContext) -> int:
    user = update.effective_user
    logger.info("User %s is adding admin access of a member to admin bot", user.first_name)
    update.message.reply_text(
            "<b>WARNING</b> you are entering <b>DANGER ZONE</b> please read the following carefully.\n\n"
            "You are planning to give users <u>adminstrative access</u> to @alliance_admin_bot\n"
            "Send me the telegram id of the user you would like to add! user can get his/her telegram id from @userinfobot\n",
            parse_mode='HTML'
            )
    return 1

@send_typing_action
def add_admin(update: Update, context: CallbackContext) -> int:
    add_admin_id = int(update.message.text)
    membership = get_membership()
    if add_admin_id in membership["admins"]:
        update.message.reply_text(f"{add_admin_id} is already an admin. nothing added")
        logger.info("%s is already an admin, nothing added, process cancelled", add_admin_id)
        return ConversationHandler.END
    membership["admins"].append(add_admin_id)
    update_membership(membership)
    logger.info("User %s has given %s administrative access to admin_bot", update.effective_user, add_admin_id)
    update.message.reply_text(f"Administrative access granted for {add_admin_id}, {add_admin_id} can use adminstrative comands.")
    return ConversationHandler.END

@send_typing_action
@restricted_admin
def get_id_remove_admin(update:Update, context: CallbackContext) -> int:
    user = update.effective_user
    logger.info("User %s is revoking admin access to admin bot", user.first_name)
    update.message.reply_text(
            "<b>WARNING</b> you are entering <b>DANGER ZONE</b> please read the following carefully.\n\n"
            "You are planning to revoke users' <u>adminstrative access</u> to @alliance_admin_bot\n"
            "Send me the telegram id of the user you would like to remove. user can get his/her telegram id from @userinfobot\n",
            parse_mode='HTML'
            )
    return 1

@send_typing_action
def remove_admin(update:Update, context: CallbackContext) -> int:
    remove_id = int(update.message.text)
    membership = get_membership()
    if remove_id not in membership["admins"]:
        update.message.reply_text(f"{remove_id} does not exist. removed nothing")
        logger.info("error in removing %s, process terminated", remove_id)
        return ConversationHandler.END
    membership["admins"].remove(remove_id)
    update_membership(membership)
    update.message.reply_text(f"sucessfully removed {remove_id}.")
    logger.info('user %s has revoked access of %s from admin bot', update.effective_user.first_name, remove_id)
    return ConversationHandler.END

@send_typing_action
@restricted_admin
def get_id_remove_member(update:Update, context: CallbackContext) -> int:
    user = update.effective_user
    logger.info("User %s is revoking access of a member to alliance bot", user.first_name)
    update.message.reply_text(
            "<b>WARNING</b> you are entering <b>DANGER ZONE</b> please read the following carefully.\n\n"
            "You are planning to revoke user access to @alliance_training_bot\n"
            "Send me the telegram id of the user you would like to remove! user can get his/her telegram id from @userinfobot\n",
            parse_mode='HTML'
            )
    return 1

@send_typing_action
def remove_member(update:Update, context: CallbackContext) -> int:
    remove_id = int(update.message.text)
    membership = get_membership()
    if remove_id not in membership["members"]:
        update.message.reply_text(f"{remove_id} does not exist. removed nothing")
        logger.info("error in removing %s, process terminated", remove_id)
        return ConversationHandler.END
    membership["members"].remove(remove_id)
    update_membership(membership)
    update.message.reply_text(f"sucessfully removed {remove_id}.")
    logger.info('user %s has revoked access of %s from alliannce bot', update.effective_user.first_name, remove_id)
    return ConversationHandler.END

@send_typing_action
@restricted_admin
def show_members(update:Update, context: CallbackContext) -> None:
    token = get_tokens()["alliance_bot"]
    bot = Bot(token=token)
    members = get_membership()["members"]
    members_lst = list()
    output_msg = update.message.reply_text(f"getting members... 0/{len(members)}")
    
    for i, member_id in enumerate(members):
        try:
            user = bot.get_chat(member_id)
        except (BadRequest, Unauthorized):
            members_lst.append(str(member_id))
            continue
        if not user.username:
            members_lst.append("Hidden " + str(member_id))
            continue
        members_lst.append(f"@{user.username}")
        output_msg.edit_text(f"getting members... {i+1}/{len(members)}")
    text = f"Members: ({len(members_lst)})\n\n"
    for member in members_lst:
        text += member + "\n"
    output_msg.edit_text(text)
    return None

@send_typing_action
@restricted_admin
def show_admins(update:Update, context: CallbackContext) -> None:
    token = get_tokens()["admin_bot"]
    bot = Bot(token=token)
    admins = get_membership()["admins"]
    admin_lst = list()
    text = f'Loading admins 0/{len(admins)}'
    txt_msg = update.message.reply_text(text)
    for i, admin_id in enumerate(admins):
        try:
            user = bot.get_chat(admin_id)
        except (BadRequest, Unauthorized):
            admin_lst.append(str(admin_id))
            continue
        if not user.username:
            admin_lst.append("Hidden " + str(admin_id))
            continue
        admin_lst.append(f"@{user.username}")
        text = f'Loading admins {i+1}/{len(admins)}'
        txt_msg.edit_text(text)
    text = f"Admins: ({len(admin_lst)})\n\n"
    for admin in admin_lst:
        text += admin + "\n"
    txt_msg.edit_text(text)
    return None



@send_typing_action
def cancel(update:Update, context: CallbackContext) -> int:
    update.message.reply_text(
            text="process cancelled, see you next time!",
            reply_markup=ReplyKeyboardRemove()
            )
    logger.info("User %s has cancelled a process", update.effective_user.first_name)
    return ConversationHandler.END

def main():
    bot_tokens = get_tokens()
    if DEVELOPMENT:
        admin_token = bot_tokens["admin_dev_bot"]
    else:
        admin_token = bot_tokens["admin_bot"]

    #setting command list
    commands = [
            BotCommand("start", "to start a the bot"),
            BotCommand("attendance_list", "give attendance of players coming to training on specfied date"),
            BotCommand("announce_all", "give announcement to all active players"),
            BotCommand("announce_training", "send announcement to active players on specified training date, only absent players will not get message"),
            BotCommand("remind", "send reminders to unindicated players on specified date"),
            BotCommand("add_member", "give member access control to telegram bot, user id must be given"),
            BotCommand("add_admin", "give admin access control to admin bot, user id must be given"),
            BotCommand("remove_member", "remove member access control to telegram bot"),
            BotCommand("remove_admin", "remove admin access control to admin bot"),
            BotCommand("show_members", "show members with access to training bot"),
            BotCommand("show_admins", "show admins with admin access"),
            BotCommand("cancel", "cancel any existing operation"),
            BotCommand("help", "help"),
            ]
    Bot(admin_token).set_my_commands(commands)

    updater = Updater(admin_token)

    #dispatcher to register handlers
    dispatcher = updater.dispatcher
    #attendance_list conversation handler
    conv_handler_attendance_list = ConversationHandler(
            entry_points=[CommandHandler("attendance_list", choosing_date)],
            states={
                1 : [
                    CallbackQueryHandler(page_change, pattern='^-?[0-9]{0,10}$' ),
                    CallbackQueryHandler(generate_attendance,pattern='^([1-9]|([012][0-9])|(3[01]))-([0]{0,1}[1-9]|1[012])-\d\d\d\d (20|21|22|23|[0-1]?\d):[0-5]?\d:[0-5]?\d$')
                    ],

                },
            fallbacks=[CommandHandler('cancel',cancel)],
            )
    #reminder conversation handler
    conv_handler_remind = ConversationHandler(
            entry_points=[CommandHandler("remind", choosing_date)],
            states={
                1 : [
                    CallbackQueryHandler(page_change, pattern='^-?[0-9]{0,10}$' ),
                    CallbackQueryHandler(send_reminders, pattern='^([1-9]|([012][0-9])|(3[01]))-([0]{0,1}[1-9]|1[012])-\d\d\d\d (20|21|22|23|[0-1]?\d):[0-5]?\d:[0-5]?\d$')
                    ],
                },
            fallbacks=[CommandHandler('cancel', cancel)],
            )
    conv_handler_announce = ConversationHandler(
            entry_points=[CommandHandler('announce_all', announce_all)],
            states={
                1 : [MessageHandler(Filters.text & ~Filters.command ,confirm_message)],
                2 : [
                    CallbackQueryHandler(send_message, pattern=f'^forward$'),
                    CallbackQueryHandler(edit_msg, pattern=f'^back$')
                    ],
                },
            fallbacks=[CommandHandler('cancel', cancel)]
            )
    conv_handler_announce_trng = ConversationHandler(
            entry_points=[CommandHandler('announce_training', choosing_date)],
            states={
                1 : [
                    CallbackQueryHandler(page_change, pattern='^-?[0-9]{0,10}$' ),
                    CallbackQueryHandler(write_message, pattern='^([1-9]|([012][0-9])|(3[01]))-([0]{0,1}[1-9]|1[012])-\d\d\d\d (20|21|22|23|[0-1]?\d):[0-5]?\d:[0-5]?\d$'),
                    ], 
                2 : [MessageHandler(Filters.text & ~Filters.command ,confirm_message)],
                3 : [
                    CallbackQueryHandler(send_training_message, pattern=f'^forward$'),
                    CallbackQueryHandler(edit_msg, pattern=f'^back$')
                    ],

                },
            fallbacks=[CommandHandler('cancel', cancel)]
            )

    conv_handler_add_member = ConversationHandler(
            entry_points=[CommandHandler('add_member', get_id)],
            states={
                1:[MessageHandler(Filters.text & ~Filters.command, add_member)],
                },
            fallbacks=[CommandHandler('cancel', cancel)]
            )

    conv_handler_remove_member = ConversationHandler(
            entry_points=[CommandHandler('remove_member', get_id_remove_member)],
            states={
                1:[MessageHandler(Filters.text & ~Filters.command, remove_member)],
                },
            fallbacks=[CommandHandler('cancel', cancel)]
            )
    conv_handler_add_admin = ConversationHandler(
            entry_points=[CommandHandler('add_admin', get_id_add_admin)],
            states={
                1:[MessageHandler(Filters.text & ~Filters.command, add_admin)],
                },
            fallbacks=[CommandHandler('cancel', cancel)],
            )
    conv_handler_remove_admin = ConversationHandler(
            entry_points=[CommandHandler('remove_admin', get_id_remove_admin)],
            states={
                1:[MessageHandler(Filters.text & ~Filters.command, remove_admin)],
                },
            fallbacks=[CommandHandler('cancel', cancel)],
            )
    

    dispatcher.add_handler(conv_handler_attendance_list)
    dispatcher.add_handler(conv_handler_remind)
    dispatcher.add_handler(conv_handler_announce)
    dispatcher.add_handler(conv_handler_announce_trng)
    dispatcher.add_handler(conv_handler_add_member)
    dispatcher.add_handler(conv_handler_remove_member)
    dispatcher.add_handler(conv_handler_add_admin)
    dispatcher.add_handler(conv_handler_remove_admin)
    dispatcher.add_handler(CommandHandler("start", start))
    dispatcher.add_handler(CommandHandler("show_members", show_members))
    dispatcher.add_handler(CommandHandler("show_admins", show_admins))
    dispatcher.add_handler(CommandHandler("cancel", cancel))

    updater.start_polling()
    updater.idle()

if __name__ == "__main__":
    main()
