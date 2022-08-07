import alliance
from telegram_bot import send_custom_message
import argparse
import pandas as pd
import os
from progress.bar import Bar

DEVELOPMENT = False

def read_msg_from_file(filename, date_str: str) -> str:
    with open(filename, "r", encoding="utf-8") as f:
        msg = f.read().replace("{date}", date_str).rstrip()
    return msg

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--choose_date", type=bool, help="type --choose_date True if you would like to choose a specific training date")
    parser.add_argument("--send_training_msg", type=int, help="0 - do not send training_message, 1-send messages to attending and not indicated only, 2-send to all")
    parser.add_argument("--send_reminders", type=bool, help="set to 1 to send messages to players who have not indicated.")
    args = parser.parse_args()
    if DEVELOPMENT:
        print("Development Mode on.")
    print("Parsing player profiles...")
    player_profiles = alliance.get_player_profiles(100)
    print("Parsing attendance sheet...")
    sheet_df = alliance.get_attendance_df(100)
    date_list = alliance.active_date_list(sheet_df.columns)
    if args.choose_date:
        option = len(date_list)
        while option == len(date_list):
            print("option : date")
            for i, d in enumerate(date_list):
                print(f"{i} : {d}")
            option = input("choose the option with the corresponding date: ")
            try :
                int(option)
            except ValueError:
                print("option must be an integer, please select again: ")
                option = len(date_list)
                continue
            option = int(option)
            if option < 0 or option >= len(date_list):
                print("invalid option")
                option = len(date_list)
    else:
        option = 0
        
    attendance_dict = alliance.get_participants(sheet_df, date_list[option].date(), player_profiles)
    attending_male, attending_female = alliance.gender_sorter(attendance_dict["attending"], player_profiles)
    
    ## writing outfile
    with open(f'sorted_attendance_{date_list[option].date().strftime("%d-%m-%y,%A")}.txt', "w") as f:
        print(f"Writing output text file...")
        f.write(f"Attendance for {date_list[option].date().strftime('%d-%b-%y,%A')}\n\n")
        f.write(f"Attending boys {len(attending_male)}:\n")
        for name in attending_male:
            f.write(name + "\n")
        f.write(f"\n")
        f.write(f"Attending girls {len(attending_female)}:\n")
        for name in attending_female:
            f.write(name + "\n")
        f.write(f"\n")
        f.write(f"Number of abseentees: {len(attendance_dict['absent'])}\n")
        f.write(f"Number not yet indicated: {len(attendance_dict['not indicated'])}\n")
        for name in (attendance_dict["not indicated"]):
            f.write(name + "\n")
        print("Writing completed.")
    
    training_date = date_list[option].date().strftime('%d-%b-%y, %A')

    if args.send_training_msg:
        unsucessful_sends = list()
        training_msg = read_msg_from_file(os.path.join("messages", "training_message.txt"), training_date)
        if args.send_training_msg == 1:
            name_lst_send = attendance_dict["attending"] + attendance_dict["not indicated"]
        elif args.send_training_msg == 2:
            name_lst_send = attendance_dict["attending"] + attendance_dict["not indicated"] + attendance_dict["absent"]
        with Bar("sending telegram messages...", max=len(name_lst_send)) as bar:
            for name in name_lst_send:
                if DEVELOPMENT:
                    name_id = player_profiles.loc["Lee Ling Zhen"]["telegram_id"]
                else:
                    name_id = player_profiles.loc[name]["telegram_id"]
                send_status = send_custom_message(training_msg, name_id)
#               print(f"send status for {name} : {send_status}")
                if not send_status:
                    unsucessful_sends.append(name)
                bar.next()
        print("\nSending training messages complete. list of uncomplete sends:")
        for name in unsucessful_sends:
            print(name)

    if args.send_reminders:
        not_indicated_msg = read_msg_from_file(os.path.join("messages", "not_indicated_message.txt"), training_date)
        name_lst_send = attendance_dict["not indicated"]
        with Bar("sending reminders who havent indicated attendance...", max=len(name_lst_send)) as bar:
            for name in name_lst_send:
                if DEVELOPMENT:
                    name_id = player_profiles.loc["Lee Ling Zhen"]["telegram_id"]
                else:
                    name_id = player_profiles.loc[name]["telegram_id"]
                send_status = send_custom_message(not_indicated_msg, name_id)
#               print(f"send status for {name} : {send_status}")
                bar.next()
        print("Sending reminders complete.")

            


if __name__ == "__main__":
    main()
