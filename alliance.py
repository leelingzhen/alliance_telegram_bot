import gspread
import json
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

def get_2_dataframes(sheetname1="Alliance Attendance 2022", sheetname2="Player Profiles", excess_rows=100):
    service_acc = gspread.service_account(filename=os.path.join(".secrets", "credentials.json"))
    workbook = service_acc.open("Alliance Training Attendance")
    ws_1 = workbook.worksheet(sheetname1)
    ws_2 = workbook.worksheet(sheetname2)
    df_1 = pd.DataFrame(ws_1.get_all_records())
    df_2 = pd.DataFrame(ws_2.get_all_records())
    df_1.columns = pd.to_datetime(df_1.columns)
    df_1 = df_1[:excess_rows]
    df_1 = df_1.set_index(df_1.iloc[:,0])
    df_1= df_1.iloc[:,1:]
    df_1= df_1.replace("",np.nan)
    df_1 = df_1.dropna(how='all')
    df_1 = df_1.drop(axis=0, index="Total")
    df_2 = df_2.set_index("names")

    return df_1, df_2

def get_training_dates(attendance_df, player_profiles, user_id) -> list:
    name = player_profiles.index[player_profiles["telegram_id"] == int(user_id)][0]
    df = attendance_df.loc[name].where(attendance_df.loc[name] == "Yes")
    df = df.dropna()
    date_arr = df.index.where(df.index.date >= date.today()).dropna().date
    return date_arr


def update_cell(data: str, sheetname="Alliance Attendance 2022"):
    value, row, column, date = data.split(",")
    value = "Yes" if value == "Y" else "No"
    service_acc = gspread.service_account(filename=os.path.join(".secrets", "credentials.json"))
    workbook = service_acc.open("Alliance Training Attendance")
    ws = workbook.worksheet(sheetname)
    ws.update_cell(row, column, value)


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

def user_attendance_status(user_id: str,date_query, attendance_df, player_profiles):
    name = player_profiles.index[player_profiles["telegram_id"] == int(user_id)]
    status = attendance_df[date_query.strftime("%Y-%m-%d")][name][0]
    if status == "Yes" or status == "No":
        return status
    else:
        return "Not indicated"

def cell_location(user_id, date_query, attendance_df, player_profiles):
    name = player_profiles.index[player_profiles["telegram_id"] == int(user_id)][0]
    row = attendance_df.index.get_loc(name) + 2
    date_query = date_query.strftime("%Y-%m-%d")
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

