"""
Приложение для режима Prison сервера VimeWorld со следующим функционалом:
    - Оповещения о боссах
    - Настройки, возможность их изменять с помощью команд
"""
import re
from time import time as get_time
from time import sleep
from datetime import time, datetime
from pathlib import Path
from os import path, listdir
import gzip
from win10toast import ToastNotifier
import yaml

LOG_PATH = path.join(Path.home(), "AppData", "Roaming", ".vimeworld", "minigames", "logs")
COMMAND_LIST = {"d", "b add", "b skip", "bl add", "bl remove"}


def processing_old_logs(boss_respawn, bosses_cooldown):
    """
    Функция, обрабатывающая старые log-файлы для обновления информации о боссах и изменения настроек
    :param boss_respawn: Словарь, ключ - имя босса, значение - время его следующего респавна
    :param bosses_cooldown: Словарь, ключ - имя босса, значение - его кулдаун
    :return:
    """
    log_gz_names = (filename for filename in listdir(LOG_PATH) if validate_gz(filename))
    for log_gz_name in log_gz_names:
        with gzip.open(path.join(LOG_PATH, log_gz_name), 'rt', encoding='utf-8') as file:
            processing_log(file, boss_respawn, bosses_cooldown)


def processing_log(file, boss_respawn, bosses_cooldown, nickname=""):
    """
    Функция, обрабатывающая log-файл и обновляет информацию о боссах и изменяет настройки
    :param file: Открытый файл логов
    :param boss_respawn: Словарь, ключ - имя босса, значение - время его следующего респавна
    :param bosses_cooldown: Словарь, ключ - имя босса, значение - его кулдаун
    :param nickname: Никнейм аккаунта в запущенном лаунчере
    :return: True or False - были ли изменены настройки
    """
    toast = ToastNotifier()
    settings_changed = False
    boss_pattern = re.compile(r"\[(\d\d:\d\d:\d\d)\] \[Client thread/INFO\]: "
                              r"\[CHAT\] ([А-Яа-яЁё ]+) был[аи]? повержен[ыа]?")
    command_pattern = re.compile(fr"\[(\d\d:\d\d:\d\d)\] \[Client thread/INFO\]: "
                                 fr"\[CHAT\] .*{nickname}.*: ~([-a-z+ ]+)([А-Яа-яЁё, \d]+)")
    error_ico_path = path.join("icons", "error.ico")
    success_ico_path = path.join("icons", "success.ico")
    for line in file:
        if "был" in line and (match := boss_pattern.match(line)):
            processing_line_with_boss(match, boss_respawn, bosses_cooldown)
        if file.name.rsplit("\\", 1)[1] == "latest.log" and nickname in line and \
                (match := command_pattern.match(line)):
            command_time = time.fromisoformat(match.group(1))
            command_time = datetime.combine(datetime.now().date(), command_time).timestamp()
            command = match.group(2)[:-1]
            params = match.group(3)
            if datetime.now().timestamp() - command_time <= 120:
                if command not in COMMAND_LIST:
                    toast.show_toast("Ooops...", "Неправильная команда", error_ico_path, 5)
                    continue
                if command == "d":
                    settings_changed = change_duration_notification(params, error_ico_path,
                                                                    success_ico_path)
                elif command == "b add":
                    settings_changed = add_boss(params, error_ico_path, success_ico_path)
                elif command == "b skip":
                    settings_changed = skip_boss(params, error_ico_path, success_ico_path,
                                                 boss_respawn)
                elif command == "bl add":
                    settings_changed = add_to_blacklist(params, success_ico_path)
                elif command == "bl remove":
                    settings_changed = remove_from_blacklist(params, success_ico_path)
    return settings_changed


def launch_boss_notifications(boss_respawn, blacklist, notification_duration):
    """
    Функция, создающая и запускающая всплывающие оповещения о боссах
    :param boss_respawn: Словарь, ключ - имя босса, значение - время его следующего респавна
    :param blacklist: Список боссов, о которых не будут присылаться оповещения
    :param notification_duration: Длительность одного оповещения в секундах
    :return:
    """
    toast = ToastNotifier()
    for boss, respawn_time in boss_respawn.items():
        print(boss, datetime.fromtimestamp(respawn_time).strftime("%H:%M:%S"))
        if boss not in blacklist and get_time() >= respawn_time:
            toast.show_toast("Босс", boss, path.join("icons", f"{boss}.ico"), notification_duration)
            sleep(0.1)


def validate_gz(filename):
    """
    Функция, проверяющая, что файл является архивным с расширением GZ и создан в сегодняшний день
    :param filename: Название файла, который валидируется
    :return: True or False - удовлетворяет ли название требованиям
    """
    body, tail = path.splitext(filename)
    if not body.startswith(datetime.now().strftime("%Y-%m-%d")):
        return False
    if not tail == ".gz":
        return False
    return True


def load_settings_variables():
    """
    Функция, загружающая и возвращающая все переменные из файла с настройками
    :return: Кортеж с переменными: словарь босс-кулдаун, чёрный список и длительность оповещения
    """
    with open("settings.yaml", encoding="windows-1251") as file:
        settings = yaml.safe_load(file)
    bosses_cooldown = settings["bosses_cooldown"]
    bosses_cooldown = {name: cooldown * 60 for name, cooldown in bosses_cooldown.items()}
    blacklist = settings["blacklist"]
    notification_duration = settings["notification_duration"]
    return bosses_cooldown, blacklist, notification_duration


def change_duration_notification(params, error_ico_path, success_ico_path):
    """
    Функция, обрабатывающая команду ~d. Изменяет длительность оповещения
    :param params: Полученные от пользователя параметры команды
    :param error_ico_path: Путь к иконке ошибки
    :param success_ico_path: Путь к иконке успеха
    :return: True - параметры изменены
    """
    toast = ToastNotifier()
    if not params.isdigit():
        toast.show_toast("Ooops...", "Длительность оповещения должна быть цифрой "
                                     "(количество секунд)", error_ico_path, 5)
        return False
    params = int(params)
    with open("settings.yaml", encoding="windows-1251") as config:
        settings = yaml.safe_load(config)
    settings["notification_duration"] = params
    with open("settings.yaml", "w", encoding="windows-1251") as config:
        yaml.safe_dump(settings, config, indent=4, allow_unicode=True, sort_keys=False)
    toast.show_toast("Успешно!", "Длительность оповещения изменена", success_ico_path, 3)
    return True


def add_boss(params, error_ico_path, success_ico_path):
    """
    Функция, обрабатывающая команду ~b add. Добавляет нового босса
    :param params: Полученные от пользователя параметры команды
    :param error_ico_path: Путь к иконке ошибки
    :param success_ico_path: Путь к иконке успеха
    :return: True - параметры изменены
    """
    toast = ToastNotifier()
    params = params.rsplit(" ", 1)
    if not params[1].isdigit():
        toast.show_toast("Ooops...", "Кулдаун респавна босса должен быть цифрой "
                                     "(количество минут)", error_ico_path, 5)
        return False
    with open("settings.yaml", encoding="windows-1251") as config:
        settings = yaml.safe_load(config)
    settings["bosses_cooldown"][params[0]] = int(params[1])
    with open("settings.yaml", "w", encoding="windows-1251") as config:
        yaml.safe_dump(settings, config, indent=4, allow_unicode=True, sort_keys=False)
    toast.show_toast("Успешно!", "Босс добавлен", success_ico_path, 3)
    return True


def skip_boss(params, error_ico_path, success_ico_path, boss_respawn):
    """
    Функция, обрабатывающая команду ~b skip. Пропускает босса
    :param params: Полученные от пользователя параметры команды
    :param error_ico_path: Путь к иконке ошибки
    :param success_ico_path: Путь к иконке успеха
    :param boss_respawn: Словарь, ключ - имя босса, значение - время его следующего респавна
    :return: True - параметры изменены
    """
    toast = ToastNotifier()
    if params not in boss_respawn:
        toast.show_toast("Ooops...", "Указано некорректное имя босса", error_ico_path, 5)
        return False
    del boss_respawn[params]
    toast.show_toast("Успешно!", "Босс пропущен", success_ico_path, 3)
    return True


def add_to_blacklist(params, success_ico_path):
    """
    Функция, обрабатывающая команду ~bl add. Добавляет боссов в чёрный список
    :param params: Полученные от пользователя параметры команды
    :param success_ico_path: Путь к иконке успеха
    :return: True - параметры изменены
    """
    toast = ToastNotifier()
    params = params.split(",")
    with open("settings.yaml", encoding="windows-1251") as config:
        settings = yaml.safe_load(config)
    settings["blacklist"] += params
    with open("settings.yaml", "w", encoding="windows-1251") as config:
        yaml.safe_dump(settings, config, indent=4, allow_unicode=True, sort_keys=False)
    toast.show_toast("Успешно!", "Чёрный список обновлён", success_ico_path, 3)
    return True


def remove_from_blacklist(params, success_ico_path):
    """
    Функция, обрабатывающая команду ~bl remove. Удаляет боссов из чёрного списка
    :param params: Полученные от пользователя параметры команды
    :param success_ico_path: Путь к иконке успеха
    :return: True - параметры изменены
    """
    toast = ToastNotifier()
    params = params.split(",")
    with open("settings.yaml", encoding="windows-1251") as config:
        settings = yaml.safe_load(config)
    settings["blacklist"] = [name for name in settings["blacklist"] if name not in params]
    with open("settings.yaml", "w", encoding="windows-1251") as config:
        yaml.safe_dump(settings, config, indent=4, allow_unicode=True, sort_keys=False)
    toast.show_toast("Успешно!", "Чёрный список обновлён", success_ico_path, 3)
    return True


def processing_line_with_boss(match, boss_respawn, bosses_cooldown):
    """
    Функция, обрабатывающая строку с информацией о убийстве босса
    :param match: Найденное совпадение в строке с регулярным выражением
    :param boss_respawn: Словарь, ключ - имя босса, значение - время его следующего респавна
    :param bosses_cooldown: Словарь, ключ - имя босса, значение - его кулдаун
    :return:
    """
    kill_time = time.fromisoformat(match.group(1))
    kill_time = datetime.combine(datetime.now().date(), kill_time).timestamp()
    name = match.group(2)
    boss_respawn[name] = kill_time + bosses_cooldown[name]


def main():
    """
    Главная функция, связывающая весь функционал реализованных функций
    :return:
    """
    boss_respawn = {}
    bosses_cooldown, blacklist, notification_duration = load_settings_variables()
    processing_old_logs(boss_respawn, bosses_cooldown)
    with open(path.join(LOG_PATH, "latest.log"), encoding='utf-8') as file:
        line = file.readline()
        nickname = line[line.find("Setting user: ") + 14:].rstrip()
        while True:
            if processing_log(file, boss_respawn, bosses_cooldown, nickname):
                bosses_cooldown, blacklist, notification_duration = load_settings_variables()
            print("-" * 60)
            launch_boss_notifications(boss_respawn, blacklist, notification_duration)
            sleep(60)


if __name__ == "__main__":
    main()
