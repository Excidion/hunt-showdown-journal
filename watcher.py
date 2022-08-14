from time import sleep
from datetime import datetime
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import os
from shutil import copytree as copydir
from shutil import copy2 as copyfile
import sys


class BackUpOnChange(FileSystemEventHandler):    
    def __init__(self, *args, backup_path, **kwargs):
        assert os.path.isdir(backup_path)
        self.backup_path = backup_path
        return super().__init__(*args, **kwargs)

    def on_modified(self, event):
        self.backup(event)
        return super().on_modified(event)

    def backup(self, event):
        origin_path = event._src_path
        destination_path = self.backup_path
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S%f")
        if os.path.isfile(origin_path):
            destination_path = os.path.join(
                destination_path,
                f"{os.path.basename(os.path.splitext(origin_path)[0])}_{timestamp}.{os.path.splitext(origin_path)[-1]}",
            )
            copyfile(origin_path, destination_path)
        elif os.path.isdir(origin_path):
            destination_path = os.path.join(
                os.path.dirname(destination_path),
                os.path.basename(f"{destination_path}_{timestamp}"),
            )
            copydir(origin_path, destination_path)
        else:
            ValueError(f"{origin_path} is neither file nor dir.")


def main(path):
    event_handler = BackUpOnChange(backup_path="./data")
    observer = Observer()
    observer.schedule(event_handler, path, recursive=True)
    observer.start()
    try:
        while True:
            sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else sys.argv[0])
