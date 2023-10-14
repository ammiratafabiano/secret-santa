import logging
from datetime import datetime


def format_name(username, first_name, last_name):
    name = "NO_NAME"
    if username and username != "":
        name = username
    elif first_name and first_name != "" and last_name and last_name != "":
        name = f"{first_name} {last_name}"
    elif first_name and first_name != "":
        name = f"{first_name}"
    elif last_name and last_name != "":
        name = f"{last_name}"
    return name


def write_log(title: str, text: str):
    try:
        if not text:
            return
        now = datetime.now().strftime("%Y%m%d%H%M%S")
        with open(f"logs/{title}_{now}.txt", "w") as file:
            file.write(text)
    except (ValueError, Exception):
        logging.error(ValueError)
        logging.error(f'Problem writing file.')
