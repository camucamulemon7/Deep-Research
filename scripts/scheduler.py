#!/usr/bin/env python3
import os
import signal
import subprocess
import sys
import threading
import time
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo


def parse_run_times(value):
    times = []
    for raw_item in value.split(","):
        item = raw_item.strip()
        if not item:
            continue
        try:
            hour_text, minute_text = item.split(":", 1)
            hour = int(hour_text)
            minute = int(minute_text)
        except ValueError as error:
            raise SystemExit(f"Invalid RUN_AT value: {item!r}. Use HH:MM or comma-separated HH:MM values.") from error
        if not (0 <= hour <= 23 and 0 <= minute <= 59):
            raise SystemExit(f"Invalid RUN_AT value: {item!r}. Hour must be 0-23 and minute must be 0-59.")
        times.append((hour, minute))
    if not times:
        raise SystemExit("RUN_AT is empty. Set RUN_AT=HH:MM, for example RUN_AT=07:30.")
    return sorted(set(times))


def next_run_at(now, run_times):
    candidates = []
    for day_offset in (0, 1):
        target_day = now.date() + timedelta(days=day_offset)
        for hour, minute in run_times:
            candidate = datetime(
                target_day.year,
                target_day.month,
                target_day.day,
                hour,
                minute,
                tzinfo=now.tzinfo,
            )
            if candidate > now:
                candidates.append(candidate)
    return min(candidates)


def run_once(command):
    started_at = datetime.now().isoformat(timespec="seconds")
    print(f"[scheduler] starting command at {started_at}: {' '.join(command)}", flush=True)
    result = subprocess.run(command, cwd=os.getcwd(), check=False)
    finished_at = datetime.now().isoformat(timespec="seconds")
    print(f"[scheduler] command finished at {finished_at} with exit code {result.returncode}", flush=True)
    return result.returncode


def main():
    timezone_name = os.environ.get("TZ", "Asia/Tokyo")
    timezone = ZoneInfo(timezone_name)
    run_times = parse_run_times(os.environ.get("RUN_AT", "07:30"))
    command = os.environ.get("RUN_COMMAND", "./run.sh").split()
    run_on_start = os.environ.get("RUN_ON_START", "").lower() in {"1", "true", "yes"}

    stop_event = threading.Event()

    def handle_signal(signum, _frame):
        print(f"[scheduler] received signal {signum}; stopping after current sleep/run", flush=True)
        stop_event.set()

    signal.signal(signal.SIGTERM, handle_signal)
    signal.signal(signal.SIGINT, handle_signal)

    print(
        "[scheduler] configured "
        f"TZ={timezone_name} RUN_AT={','.join(f'{h:02d}:{m:02d}' for h, m in run_times)} "
        f"RUN_ON_START={run_on_start}",
        flush=True,
    )

    if run_on_start:
        run_once(command)

    while not stop_event.is_set():
        now = datetime.now(timezone)
        target = next_run_at(now, run_times)
        print(f"[scheduler] next run at {target.isoformat(timespec='minutes')}", flush=True)
        while not stop_event.is_set():
            now = datetime.now(timezone)
            seconds = (target - now).total_seconds()
            if seconds <= 0:
                break
            stop_event.wait(min(seconds, 60))
        if stop_event.is_set():
            break
        run_once(command)

    return 0


if __name__ == "__main__":
    sys.exit(main())
