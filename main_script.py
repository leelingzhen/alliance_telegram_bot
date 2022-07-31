from read_attendance import get_player_profiles, get_attendance_df, active_date_list, get_participants, gender_sorter
from telegram_bot import send_custom_message
import argparse
import pandas as pd
import os

DEVELOPMENT = True

def read_msg_from_file(filename, date_str : str):
    with open(filename, "r") as f:
        msg = f.read().replace("{date}", date_str).rstrip()
    return msg

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--choose_date", type=bool, help="type --choose_date True if you would like to choose a specific training date")
    parser.add_argument("--send_msg", type=bool, help="type --send_msg True if you would like to send telegram messages through alliance bot")
    args = parser.parse_args()
    if DEVELOPMENT:
        print("Development Mode on.")
    print("Parsing player profiles...")
    player_profiles = get_player_profiles(100)
    print("Parsing attendance sheet...")
    sheet_df = get_attendance_df(100)
    date_list = active_date_list(sheet_df.columns)
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
        
    attendance_dict = get_participants(sheet_df, date_list[option].date(), player_profiles)
    attending_male, attending_female = gender_sorter(attendance_dict["attending"], player_profiles)
    
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
    
    if args.send_msg:
        print("sending telegram messages...")
        unsucessful_sends = list()
        training_date = date_list[option].date().strftime('%d-%b-%y, %A')
        training_msg = read_msg_from_file(os.path.join("messages", "training_message.txt"), training_date)
        not_indicated_msg = read_msg_from_file(os.path.join("messages", "not_indicated_message.txt"), training_date)
        for name in attendance_dict["attending"] + attendance_dict["not indicated"]:
            if DEVELOPMENT:
                name_id = player_profiles.loc["Lee Ling Zhen"]["telegram_id"]
            else:
                name_id = player_profiles.loc[name]["telegram_id"]
            send_status = send_custom_message(training_msg, name_id)
            if name in attendance_dict["not indicated"]:
                send_status = send_custom_message(not_indicated_msg, name_id)
            print(f"send status for {name} : {send_status}")
            if not send_status:
                unsucessful_sends.append(name)
        print("\nsending complete. list of uncomplete sends:")
        for name in unsucessful_sends:
            print(name)
            


if __name__ == "__main__":
    main()