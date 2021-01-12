#!/usr/bin/env python3
from datetime import datetime

#do imports after aquiring startup time to be a bit more precise
startup_time = datetime.now().astimezone()

import sys
import os
import time
from datetime import timedelta
import subprocess

# use the submodule for dateparser if it is available
# this fixes relative dates with non integer numbers like "1.5 min"
sys.path.insert(0, os.path.dirname(os.path.realpath(__file__)) + "/dateparser")
import dateparser

def exit_help(code):
    msg = (
        "schedule [OPTIONS] TIME COMMAND...\n" +
        "    detaches a process to execute COMMAND at the specified TIME\n"+
        "    -s:      run synchronuous, don't use a detached process\n" +
        "    -f:      run immediately if time is in the past\n" +
        "    -p:      keep stdout and stderr for executed command\n" +
        "    -h:      print this help and exit\n" +
        "    -v:      announnce the scheduled time. -vv / -vvv for more precision\n" +
        "    -b TIME: relative TIMEs will be relative to this, default is the current time\n"+
        "    TIME:    3min, 17:00, etc...\n"+
        "    COMMAND: any shell command\n"
    )
    if code == 0:
        sys.stdout.write(msg)
    else:
        sys.stderr.write(msg)
    exit(code)

def main():
    global startup_time
    synchronous = False
    force = False
    pipe = False
    verbose = 0
    i = 0
    args = sys.argv
    while True:
        i += 1
        if len(args) < i + 2: exit_help(1)
        arg = args[i]
        if arg[0] == "-" and len(arg) > 2:
            args = args[:i] + ["-" + c for c in arg[1:]] + args[i+1:]
            arg = arg[:2]
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
        if arg in ["-v", "--verbose"]:
            verbose += 1
            if verbose > 3:
                sys.stderr.write("max verbosity level is 3\n")
                exit(1)
            continue
        if arg in ["-b", "--basetime"]:
            bt=args[i+1]
            try:
                startup_time = dateparser.parse(
                    bt,
                    settings={'PREFER_DATES_FROM': 'future', 'RELATIVE_BASE': startup_time}
                ).astimezone()
            except:
                sys.stderr.write("failed to parse basetime from '" + bt + "'\n")
                exit(1)
            i += 1
            continue

        schedule_time_str = arg
        cmds = args[i+1:]
        break

    try:
        schedule_time = dateparser.parse(
            schedule_time_str,
            settings={'PREFER_DATES_FROM': 'future', 'RELATIVE_BASE': startup_time}
        ).astimezone()
    except:
        sys.stderr.write("failed to parse time from '" + schedule_time_str + "'\n")
        exit(1)

    if verbose == 1:
        # only import this if we actually need it
        try:
            import humanize
        except:
            sys.stderr.write("missing python package 'humanize' for -v/--verbose\n")
            exit(1)
        if schedule_time > startup_time:
            print("scheduled time is in " + humanize.naturaldelta(schedule_time - startup_time))
        else:
            print("scheduled time was " + humanize.naturaltime(startup_time - schedule_time))
    elif verbose == 2:
        print("scheduled time is " + schedule_time.replace(microsecond=0).isoformat())
    elif verbose == 3:
        print("scheduled time is " + schedule_time.isoformat())

    if not force and schedule_time + timedelta(seconds=3) < startup_time:
        sys.stderr.write("error: scheduled time is in the past\n")
        exit(1)

    if not synchronous:
        if not pipe:
            devnull = open(os.devnull,"w")
        subprocess.Popen(
            [__file__,  "-sfb", str(startup_time.timestamp()), schedule_time_str] + cmds,
            start_new_session=True,
            stdout=sys.stdout if pipe else devnull,
            stderr=sys.stderr if pipe else devnull
        )
        if not pipe:
            devnull.close()
        exit(0)
    now = datetime.now().astimezone()
    while schedule_time > now:
        diff_secs = (schedule_time - now).total_seconds()
        if diff_secs > 60 * 31:
            time.sleep(60 * 30)
        elif diff_secs > 0.001:
            time.sleep(diff_secs)
        else:
            break
        now = datetime.now().astimezone()
    try:
        try:
            os.execvp(cmds[0], cmds)
        except AttributeError:
            subprocess.call(cmds)
    except FileNotFoundError:
        sys.stderr.write("failed to execute command: file '" + cmds[0] + "' not found on path\n")

if __name__ == "__main__":
    main()
