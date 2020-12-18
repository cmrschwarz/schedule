#!/usr/bin/env python3

import sys
import os
import time
import dateparser
from datetime import datetime
from datetime import timedelta
import subprocess

def exit_help(code):
    msg = (
        "schedule [-sfph] TIME COMMAND...\n" +
        "    -s:      run synchronuous, don't use a detached process\n" +
        "    -f:      run immediately if time is in the past\n" +
        "    -p:      keep stdout and stderr for detached process\n" +
        "    -h:      print this help and exit\n" +
        "    TIME:    3min, or 17:00, etc...\n"+
        "    COMMAND: any shell command\n"
    )
    if code == 0:
        sys.stdout.write(msg)
    else:
        sys.stderr.write(msg)
    exit(code)

def main():
    startup_time = datetime.now().astimezone()
    synchronous = False
    force = False
    pipe = False
    i = 0
    while True:
        i += 1
        if len(sys.argv) < i + 2: exit_help(1)
        arg = sys.argv[i]
        if arg in ["-h", "--help"]:
            exit_help(0)
            continue
        if arg in ["-s", "--synchronous"]:
            synchronous = True
            continue
        if arg in ["-f", "--force"]:
            force = True
            continue
        if arg in ["-p", "--pipe"]:
            pipe = True
            continue
        schedule_time_str = arg
        cmds = sys.argv[i+1:]
        break

    try:
        schedule_time = dateparser.parse(
            schedule_time_str,
            settings={'PREFER_DATES_FROM': 'future'}
        ).astimezone()
    except Exception:
        sys.stderr.write("failed to parse time from '" + schedule_time_str + "'\n")
        exit(1)

    if not force and schedule_time + timedelta(seconds=3) < startup_time:
        sys.stderr.write("error: scheduled time is in the past\n")
        exit(1)

    if not synchronous:
        if not pipe:
            devnull = open(os.devnull,"w")
        subprocess.Popen(
            [os.path.realpath(__file__)] + ["-s", "-f"] + sys.argv[1:],
            start_new_session=True,
            stdout=sys.stdout if pipe else devnull,
            stderr=sys.stderr if pipe else devnull
        )
        if not pipe:
            devnull.close()
        exit(0)
    
    while schedule_time > datetime.now().astimezone():
        diff = schedule_time - datetime.now().astimezone()
        if diff.seconds > 60 * 31:
            time.sleep(60 * 30)
            continue
        if diff.seconds == 0: break
        time.sleep(diff.seconds - 1)
            
    subprocess.call(cmds)


if __name__ == "__main__":
    main()
