# A simple python script implementation that manages attendance and send reminders to telegram users by a telegram bot

## Setup

create a `.secrets` directory

create a google service account and save credentials to `credentials.json` and place it in `.secrets`

create a telegram bot with and place bot api token in `bot_token.txt`, place it in `.secrets`

## Usage
create a virtual env and install required dependencies

linux/macOS:

```
python3 -m venv script_venv  
pip install -r requriments.txt  
source script_venv/bin/activate  
```


windows:

```
python -m venv script_venv  
pip install -r requirements.txt  
script_venv\Scripts\activate  
```

run the script:

```
python main_script.py
```

|flags |options |Description
|---|---|---|
|`--choose_date` | `True`, `False`| gives you the option to choose from a list of dates otherwise default would be the earliest training date|
|`--send_training_msg` |`0`, `1`, `2`| 0 will not send any message, 1 will send messages to "attending" and "not indicated" players, 2 will send to everyone|
|`--send_reminders` |`True`, `False`|give you the option to send reminders|


## Custom messages
messages uses html tags to format text, messages used by the bot are found in `messages` directory. You may edit the .txt files but do not rename the files. `{date}` can be used as a place holder for the intended training date. formatted in d/mmm/yyyy, weekday.
