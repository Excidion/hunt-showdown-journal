# Hunt Journal
This app will help you track your progress in the game Hunt: Showdown.
## Setup
+ Install [Python 3.10.6](https://www.python.org/ftp/python/3.10.6/python-3.10.6-amd64.exe).
**Important:** Make sure to set the option **Add Python to PATH** in the installation process.
+ Download the source code:
    + **Option A**: By cloning this repository. (If you don't know how to do this, simply take Option B.)
    + **Option B**: Click on *Code* -> *Download ZIP* and unpack the downloaded files.
+ Go into the new directory.
+ Right click on `setup.ps1` an choose *Run with Powershell*.
+ Right click into the directory and create a new text file and name it `.env`.
+ Open the newly created file with a text editor (eg. notepad) and add a line like the following.
**Make sure to change this path according to where you have installed the game.**
```
watched_file=C:\Programs\steamapps\common\Hunt Showdown\user\profiles\default\attributes.xml
```

## Usage
### Recording Matches
Before starting the game, so your matches are recorded:
+ Go to the installation directory.
+ Right click on `recorder.ps1` an choose *Run with Powershell*.

Alternatively you can also start the Match Recorder via the app.
This functionality is experimantal and not yet tested.

### App for Analyze Matches
When you want to analyze your recorded matches.
+ Go to the installation directory.
+ Right click on `app.ps1` an choose *Run with Powershell*.
