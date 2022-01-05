#!/usr/bin/env python3
from datetime import datetime

#do imports after aquiring startup time to be a bit more precise
script_startup_time = datetime.now().astimezone()

import sys
import os
import time
from datetime import timedelta
import subprocess
import psutil
from pathlib import Path
import humanize
import warnings

# use the submodule for dateparser if it is available
# this fixes relative dates with non integer numbers like "1.5 min"
sys.path.insert(0, os.path.dirname(os.path.realpath(__file__)) + "/dateparser")
import dateparser
from dateparser_data.settings import default_parsers
def print_help(stderr=False):
    msg = (
        "schedule [OPTIONS] TIME COMMAND...\n" +
        "    detaches a process to execute COMMAND at the specified TIME\n"+
        "    -s:      run synchronuous, don't use a detached process\n" +
        "    -f:      run immediately if time is in the past\n" +
        "    -p:      keep stdout and stderr for executed command\n" +
        "    -h:      print this help\n" +
        "    -l:      list running instances of schedule\n" +
        "    -v:      announnce the scheduled time. -vv / -vvv for more precision\n" +
        "    -b TIME: relative TIMEs will be relative to this, default is the current time\n"+
        "    TIME:    3min, 17:00, etc...\n"+
        "    COMMAND: any shell command\n"
    )
    if stderr:
        sys.stderr.write(msg)
    else:
        sys.stdout.write(msg)

def list_schedules(verbosity, base_time):
    base_name = Path(sys.argv[0]).stem
    python_name = Path(sys.executable).stem
    schedules = []
    for proc in psutil.process_iter():
        proc_base_name = Path(proc.name()).stem
        proc_cli = None
        if proc_base_name == python_name:
            proc_cli = proc.cmdline()
            if len(proc_cli) < 2: continue
            proc_cli = proc_cli[1:]
            proc_base_name = Path(proc_cli[0]).stem

        if proc_base_name == base_name:
            if not proc_cli:
                proc_cli = proc.cmdline()
            if len(proc_cli) < 2: continue
            startup_time = None
            fire_time = None
            i = 1 
            while i < len(proc_cli):
                c = proc_cli[i]
                if (c[0] == "-" and c[-1] == "b") or c == "--basetime":
                    try:
                        startup_time = timeparse(proc_cli[i+1], None)
                        i += 2
                        continue
                    except:
                        break
                if c[0] != "-":
                    try:
                        fire_time = timeparse(c, startup_time)
                        schedules.append((fire_time, " ".join(proc_cli[i+1:])))
                        break
                    except:
                        break
                i += 1
    if not schedules:
        print("no running schedules")
        return

    schedules.sort()
    max_time_len = 0
    for i in range(len(schedules)):
        s = schedules[i]
        tf = timeformat(s[0], base_time, verbosity)
        max_time_len = max(max_time_len, len(tf))
        schedules[i] = (tf, s[1])
    for s in schedules:
        print(s[0] + ":" + " " * (max_time_len - len(s[0]) + 1) + s[1])

def timeparse(time_str, base_time):
    # prevent flat integers from being interpreted weirdly (e.g. day of moth)
    # since it's a common mistake to forget the unit (e.g minutes)
    try:
        i = int(time_str)
    except:
        i = None

    if i is not None and i < 20000:
        raise ValueError("invalid date")
    settings =  {}
    if base_time is None:
        parsers = [parser for parser in default_parsers if parser != 'relative-time']
        settings['PARSERS'] = parsers
    else:
        settings['PREFER_DATES_FROM'] = 'future'
        settings['RELATIVE_BASE'] = base_time
    # Ignore dateparser warnings regarding pytz
    warnings.filterwarnings(
        "ignore",
        message="The localize method is no longer necessary, as this time zone supports the fold attribute",
    )

    return dateparser.parse(
        time_str,  settings=settings
    ).astimezone()

def timeformat(time, base_time, verbosity):
    if verbosity == 0:
        if time > base_time:
            return "in " + humanize.naturaldelta(time - base_time)
        else:
            return humanize.naturaltime(time) + "ago"
            
    if verbosity == 1:
        if time > base_time:
            return "in " + humanize.precisedelta(time - base_time, minimum_unit="seconds", format="%0.0f")
        else:
            return humanize.precisedelta(base_time - time, minimum_unit="seconds", format="%0.0f") + "ago"
    if verbosity == 2:
        return time.replace(microsecond=0).isoformat(sep=' ')
    if verbosity >= 3: 
        return time.isoformat(sep=' ')

def main():
    base_time = script_startup_time
    error_if_no_time = True
    synchronous = False
    force = False
    pipe = False
    got_schedule = False
    verbose = 0
    sched_list = False
    i = 0
    
    #debug
    args = sys.argv
    #args = ["schedule", "10min", "alarm", "test"]
    #args = ["schedule", "-l"]
    while i + 1 < len(args):
        i += 1
        arg = args[i]
        if arg[0] == "-" and len(arg) > 2:
            args = args[:i] + ["-" + c for c in arg[1:]] + args[i+1:]
            arg = arg[:2]
        if arg in ["-l", "--list"]:
            sched_list = True
            error_if_no_time = False
            continue
        if arg in ["-h", "--help"]:
            print_help()
            error_if_no_time = False
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
                return 1
            continue
        if arg in ["-b", "--basetime"]:
            bt=args[i+1]
            try:
                base_time = timeparse(bt, None)
            except:
                sys.stderr.write("failed to parse (absolute) basetime from '" + bt + "'\n")
                return 1
            i += 1
            continue
        got_schedule = True
        schedule_time_str = arg
        cmds = args[i+1:]
        break
    
    if sched_list:
        list_schedules(verbose, base_time)


    if not got_schedule:
        if error_if_no_time:
            print_help(True)
            return 1
        else:
            return 0
 
    try:
        schedule_time = timeparse(schedule_time_str, base_time)
    except:
        sys.stderr.write("failed to parse time from '" + schedule_time_str + "'\n")
        return 1
    if verbose != 0:
        print("scheduled time is " + timeformat(schedule_time, base_time, verbose))

    if not force and schedule_time + timedelta(seconds=3) < base_time:
        sys.stderr.write("error: scheduled time is in the past\n")
        return 1

    if not synchronous:
        if not pipe:
            devnull = open(os.devnull,"w")
        subprocess.Popen(
            [__file__,  "-sfb", str(base_time.replace(tzinfo=None).isoformat(sep=' ')), schedule_time_str] + cmds,
            start_new_session=True,
            stdout=sys.stdout if pipe else devnull,
            stderr=sys.stderr if pipe else devnull
        )
        if not pipe:
            devnull.close()
        return 0
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
        return 1

    return 0

if __name__ == "__main__":
    exit(main())
