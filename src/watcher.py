from time import sleep
from datetime import datetime
import os
from shutil import copy2 as copyfile
import threading


TIMESTAMP_FORMAT = "%Y%m%d-%H%M%S%f"
CHECK_FILE_AFTER = 60 # in seconds


class FileBackupper(threading.Thread):
    def __init__(self, watched_file, backup_dir):
        threading.Thread.__init__(self)
        self.stop_event = threading.Event()
        assert os.path.exists(watched_file)
        self.watched_file = watched_file
        self.last_modified = self.get_last_modified()
        assert os.path.isdir(backup_dir)
        self.backup_dir = backup_dir
        
    def run(self):
        while not self.stop_event.wait(CHECK_FILE_AFTER):
            if self.last_modified != self.get_last_modified():
                self.last_modified = self.get_last_modified()
                self.backup()
    
    def stop(self):
        self.stop_event.set()

    def get_last_modified(self):
        return os.path.getmtime(self.watched_file)

    def backup(self):
        timestamp = datetime.fromtimestamp(self.get_last_modified()).strftime(TIMESTAMP_FORMAT)
        destination_path = os.path.join(
            self.backup_dir,
            f"{os.path.basename(os.path.splitext(self.watched_file)[0])}_{timestamp}{os.path.splitext(self.watched_file)[-1]}",
        )
        copyfile(self.watched_file, destination_path)
        print("Saved", destination_path)


def main(watched_file, backup_dir="./data/raw"):
    thread = FileBackupper(watched_file, backup_dir)
    thread.start()
    print("Recorder active...")
    print("Watching", watched_file)
    try:
        while True:
            sleep(2)
    except KeyboardInterrupt:
        thread.stop()


if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    main(os.getenv("watched_file"))
