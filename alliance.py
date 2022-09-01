import gspread
import json
import pandas as pd
import numpy as np
from datetime import date, datetime
import os


#new code implementations
def clean_attendance_df(df, excess_rows=100):
    df.columns = pd.to_datetime(df.columns, errors='coerce', format='%a, %d-%m-%y @ %H:%M')
    df = df[:excess_rows]
    df = df.set_index(df.iloc[:,0])
    df = df.iloc[:,1:]
    df = df.replace("",np.nan)
    df = df.dropna(how='all')
    df = df.drop(axis=0, index="Total")
    return df

def clean_player_profiles(df, excess_rows=100):
    df = df.set_index("names")
    return df

def clean_details_df(df, excess_rows=100):
    df.columns = pd.to_datetime(df.columns, errors='coerce', format='%a, %d-%m-%y @ %H:%M')
    df = df.set_index(df.iloc[:,0])
    df = df.iloc[:,1:]
    return df

def get_sheet_records(
        workbook_name="Alliance Training Attendance",
        player_profiles="Player Profiles",
        attendance="Alliance Attendance (Beta)",
        details="Training Details (Beta)"):
    service_acc = gspread.service_account(filename=os.path.join(".secrets", "credentials.json"))
    workbook = service_acc.open(workbook_name)

    #cleaning attendance df
    if attendance:
        attendance_ws = workbook.worksheet(attendance)
        attendance_df = pd.DataFrame(attendance_ws.get_all_records())
        attendance_df = clean_attendance_df(attendance_df)
    else :
        attendance_df = None

    #cleaning player_profiles
    if player_profiles:
        pp_ws = workbook.worksheet(player_profiles)
        player_profiles_df = pd.DataFrame(pp_ws.get_all_records())
        player_profiles_df = clean_player_profiles(player_profiles_df)
    else:
        player_profiles_df = None

    #cleaning details
    if details:
        training_ws = workbook.worksheet(details)
        details_df = pd.DataFrame(training_ws.get_all_records())
        details_df = clean_details_df(details_df)
    else:
        details_df = None

    return attendance_df, details_df, player_profiles_df

def update_cell(
        cell_location : tuple,
        indicated_attendance : str,
        sheetname="Alliance Attendance (Beta)",
        workbook_name="Alliance Training Attendance"):

    row, column = cell_location[0], cell_location[1]
    service_acc = gspread.service_account(filename=os.path.join(".secrets", "credentials.json"))
    workbook = service_acc.open(workbook_name)
    ws = workbook.worksheet(sheetname)
    ws.update_cell(row, column, indicated_attendance)



def get_training_dates(attendance_df, player_profiles, user_id) -> list:
    name = player_profiles.index[player_profiles["telegram_id"] == int(user_id)][0]
    df = attendance_df.loc[name].where(attendance_df.loc[name] == "Yes")
    df = df.dropna()
    date_arr = df.index.where(df.index.date >= date.today()).dropna()
    return date_arr

def get_participants(df, date_query, player_profiles):
    attendance_dict = {}
    target_date = pd.Timestamp(date_query)
    inactive_players = player_profiles.index[player_profiles["status"] == "Inactive"]
    if target_date not in df.columns:
        return attendance_dict
    attendance_dict["attending"] = list(df.index[df[target_date]== "Yes"])
    attendance_dict["absent"] = list(df.index[df[target_date] == "No"])
    attendance_dict["not indicated"] = list(df.index[df[target_date].isna()])
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

def user_attendance_status(user_id: str,date_query, attendance_df, player_profiles):
    target_date = pd.Timestamp(date_query)
    name = player_profiles.index[player_profiles["telegram_id"] == int(user_id)]
    status = attendance_df[target_date][name][0]
    if status == "Yes" or status == "No":
        return status
    else:
        return "Not indicated"

def cell_location(user_id, date_query, attendance_df, player_profiles):
    name = player_profiles.index[player_profiles["telegram_id"] == int(user_id)][0]
    row = attendance_df.index.get_loc(name) + 2
    target_date = pd.Timestamp(date_query)
    column = attendance_df.columns.get_loc(date_query) + 2
    return row, column

def read_msg_from_file(filename, date_str: str) -> str:
    with open(filename, "r", encoding="utf-8") as text_f:
        msg = text_f.read().replace("{date}", date_str).rstrip()
    return msg

def active_date_list(date_list, target_date=date.today()):
    for i, date_element in enumerate(date_list):
        date_element = date_element.date()
        if date_element >= target_date:
            return date_list[i:]
    return []

