from time import time as get_time
from time import sleep
from collections import defaultdict
from datetime import time, datetime
from pathlib import Path
from os import path, listdir
import gzip
from win10toast import ToastNotifier

LOG_PATH = path.join(Path.home(), "AppData", "Roaming", ".vimeworld", "minigames", "logs")
BOSS_COOLDOWN = {"Королевский зомби": 1200, "Холуй": 2700, "Сточный слизень": 3600,
                 "Фенрир": 5400, "Матка": 5400, "Все Всадники апокалипсиса": 9000,
                 "Левиафан": 9000, "Коровка из Коровёнки": 9000, "Йети": 10800, "Житель края": 10800}
BLACKLIST = ("Левиафан", "Коровка из Коровёнки", "Йети", "Житель края")


def checker(log_path):
    toast = ToastNotifier()
    boss_respawn = defaultdict(lambda: 0)
    processing_old_logs(log_path, boss_respawn)
    while True:
        with open(path.join(LOG_PATH, "latest.log"), encoding='utf-8') as file:
            processing_log(file, boss_respawn)
        print("-" * 60)
        toaster(toast, boss_respawn)
        sleep(60)


def processing_old_logs(log_path, boss_respawn):
    log_gz_names = [filename for filename in listdir(log_path) if validate_gz(filename)]
    for log_gz_name in log_gz_names:
        with gzip.open(path.join(log_path, log_gz_name), 'rt', encoding='utf-8') as file:
            processing_log(file, boss_respawn)


def processing_log(file, boss_respawn):
    kills = filter(lambda string: "повержен" in string, file.readlines())
    for kill in kills:
        kill_time = time.fromisoformat(kill[1:9])
        kill_time = datetime.combine(datetime.now().date(), kill_time).timestamp()
        kill = kill[40:]
        name = kill[:kill.find("был") - 1]
        boss_respawn[name] = kill_time + BOSS_COOLDOWN[name]


def toaster(toast, boss_respawn):
    for boss in boss_respawn:
        print(boss, datetime.fromtimestamp(boss_respawn[boss]).strftime("%H:%M:%S"))
        if get_time() >= boss_respawn[boss]:
            if boss not in BLACKLIST:
                toast.show_toast('Босс', boss, duration=3)


def validate_gz(filename):
    body, tail = path.splitext(filename)
    if not tail == ".gz":
        return False
    if not body.startswith(datetime.now().strftime("%Y-%m-%d")):
        return False
    return True


def main():
    checker(LOG_PATH)


if __name__ == "__main__":
    main()
