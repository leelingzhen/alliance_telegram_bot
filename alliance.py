import gspread
import pandas as pd
import numpy as np
from datetime import date
import os

def get_dataframe(sheetname):
    service_acc = gspread.service_account(filename=os.path.join(".secrets", "credentials.json"))
    workbook = service_acc.open("Alliance Training Attendance")
    ws = workbook.worksheet(sheetname)
    df = pd.DataFrame(ws.get_all_records())
    return df

def get_attendance_df(excess_rows):
    attendance_df = get_dataframe("Alliance Attendance 2022")
    attendance_df.columns = pd.to_datetime(attendance_df.columns)
    attendance_df = attendance_df[:excess_rows]
    attendance_df = attendance_df.set_index(attendance_df.iloc[:,0])
    attendance_df = attendance_df.iloc[:,1:]
    attendance_df = attendance_df.replace("",np.nan)
    attendance_df = attendance_df.dropna(how='all')
    attendance_df = attendance_df.drop(axis=0, index="Total")
    return attendance_df

def get_player_profiles(excess_rows):
    df = get_dataframe("Player Profiles")
    df = df.set_index("names")
    return df

def get_participants(df, target_date, player_profiles):
    attendance_dict = {}
    date_str = target_date.strftime("%Y-%m-%d")
    inactive_players = player_profiles.index[player_profiles["status"] == "Inactive"]
    if date_str not in df.columns:
        return attendance_dict
    attendance_dict["attending"] = list(df.index[df[date_str]== "Yes"])
    attendance_dict["absent"] = list(df.index[df[date_str] == "No"])
    attendance_dict["not indicated"] = list(df.index[df[date_str].isna()])
    #removing inactive players from "not indicated list"
    for player in inactive_players:
        if player in attendance_dict["not indicated"]:
            attendance_dict["not indicated"].remove(player)
        if player in attendance_dict["absent"]:
            attendance_dict["absent"].remove(player)
    return attendance_dict

def gender_sorter(name_list, player_profiles):
    male_list = list()
    female_list = list()
    for name in name_list:
        if player_profiles.loc[name]["gender"] == "Male":
            male_list.append(name)
        elif player_profiles.loc[name]["gender"] == "Female":
            female_list.append(name)
    return male_list, female_list

def user_attendance_status(user_id: str,date_query):
    df = get_attendance_df(100)
    player_profiles = get_player_profiles(100)
    name = player_profiles.index[player_profiles["telegram_id"] == int(user_id)]
    status = df[date_query.strftime("%Y-%m-%d")][name][0]
    if status == "Yes" or status == "No":
        return status
    else:
        return "Not indicated"


def attendance_stats(attendance_df, player_profiles):
    n_attending = len(attendance_df["attending"])
    attending_m, attending_f = gender_sorter(attendance_df["attending"], player_profiles)
    n_absent = len(attendance_df["absent"])
    n_not_indicated = len(attendance_df["not indicated"])
    not_indicated_m, not_indicated_f = gender_sorter(attendance_df["not indicated"], player_profiles)

    return {"attending" : n_attending,
            "male attending" : attending_m,
            "female attending": attending_f,
            "num absent": n_absent,
            "absent": list(attendance_df["absent"]),
            "not indicated" :n_not_indicated,
            "male not indicated": not_indicated_m,
            "female not indcated": not_indicated_f
            }

def active_date_list(date_list, target_date=date.today()):
    for i, date_element in enumerate(date_list):
        date_element = date_element.date()
        if date_element >= target_date:
            return date_list[i:]
    return []


'''
if __name__ == "__main__":

    player_profiles = get_player_profiles(100)
    sheet_df = get_attendance_df(100)
    date_list = active_date_list (sheet_df.columns)
    attendance_dict = get_participants(sheet_df, date_list[1].date(), player_profiles)
    print(attendance_dict)
#stats = attendance_stats(attendance_dict, player_profiles)
player_profiles = get_player_profiles(100)
'''
sheet_df = get_attendance_df(100)
