from time import sleep, ctime
from datetime import datetime
import os
from shutil import copy2 as copyfile
import sys


def main(watched_file, backup_dir="./data"):
    assert os.path.isdir(backup_dir)
    try:
        mainloop(watched_file, backup_dir)
    except KeyboardInterrupt:
        return

def mainloop(watched_file, backup_dir):
    last_modified = get_last_modified(watched_file)
    while True: # mainlooop
        while last_modified == get_last_modified(watched_file):
            print(ctime(get_last_modified(watched_file)))
            sleep(5)
        else:
            last_modified = get_last_modified(watched_file)
            backup(watched_file, backup_dir) 


def get_last_modified(path):
    return os.path.getmtime(path)

def backup(filepath, destination_dir):
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S%f")
    destination_path = os.path.join(
        destination_dir,
        f"{os.path.basename(os.path.splitext(filepath)[0])}_{timestamp}.{os.path.splitext(filepath)[-1]}",
    )
    copyfile(filepath, destination_path)


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else sys.argv[0])
