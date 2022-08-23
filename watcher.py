from time import sleep
from datetime import datetime
import os
from shutil import copy2 as copyfile
import sys
from dotenv import load_dotenv

load_dotenv()

TIMESTAMP_FORMAT = "%Y%m%d-%H%M%S%f"


def main(watched_file, backup_dir="./data/raw"):
    assert os.path.isdir(backup_dir)
    try:
        mainloop(watched_file, backup_dir)
    except KeyboardInterrupt:
        return

def mainloop(watched_file, backup_dir):
    last_modified = get_last_modified(watched_file)
    while True: # mainlooop
        while last_modified == get_last_modified(watched_file):
            sleep(15)
        else:
            last_modified = get_last_modified(watched_file)
            backup(watched_file, backup_dir) 


def get_last_modified(path):
    return os.path.getmtime(path)

def backup(filepath, destination_dir):
    timestamp = datetime.fromtimestamp(get_last_modified(filepath)).strftime(TIMESTAMP_FORMAT)
    print(timestamp)
    destination_path = os.path.join(
        destination_dir,
        f"{os.path.basename(os.path.splitext(filepath)[0])}_{timestamp}{os.path.splitext(filepath)[-1]}",
    )
    copyfile(filepath, destination_path)


if __name__ == "__main__":
    main(os.getenv("watched_file"))
