"""
Приложение для режима Prison сервера VimeWorld со следующим функционалом:
    - Оповещения о боссах
    - Оповещения о службах в церкви
    - Оповещения об обновлении шахт
    - Настройки, возможность их изменять с помощью команд
"""
from time import time as get_time
from time import sleep
from datetime import time, datetime
from os import system
from sys import exit
import re
import gzip
from zoneinfo import ZoneInfo

from win10toast import ToastNotifier
from win11toast import toast
import yaml

from src.constants import LOG_PATH, OS, RAINBOW_NAMES, ICONS_PATH
from src.notifier import Notifier

NOTIFIER = Notifier()


def processing_old_logs(boss_respawn, bosses_cooldown, notification_duration):
    """
    Функция, обрабатывающая старые log-файлы для обновления информации о боссах
    :param boss_respawn: Словарь, ключ - имя босса, значение - время его следующего респавна
    :param bosses_cooldown: Словарь, ключ - имя босса, значение - его кулдаун
    :param notification_duration: Длительность одного оповещения в секундах
    :return: None
    """
    log_gz_names = (
        filename for filename in LOG_PATH.iterdir() if validate_gz(filename)
    )
    for log_gz_name in log_gz_names:
        with gzip.open(LOG_PATH / log_gz_name, "rt", encoding="utf-8") as file:
            processing_log(file, boss_respawn, bosses_cooldown, notification_duration)


def processing_log(
    file, boss_respawn, bosses_cooldown, notification_duration, nickname=""
):
    """
    Функция, обрабатывающая log-файл и обновляет информацию о боссах и изменяет настройки
    :param file: Открытый файл логов
    :param boss_respawn: Словарь, ключ - имя босса, значение - время его следующего респавна
    :param notification_duration: Длительность одного оповещения в секундах
    :param bosses_cooldown: Словарь, ключ - имя босса, значение - его кулдаун
    :param nickname: Никнейм аккаунта в запущенном лаунчере
    :return: bool - были ли изменены настройки
    """
    settings_changed = False
    boss_pattern = re.compile(
        r"\[(\d\d:\d\d:\d\d)\] \[Client thread/INFO\]: "
        r"\[CHAT\] (Все )?([А-Яа-яЁё ]+) был[аи]? повержен[ыа]? за"
    )
    command_pattern = re.compile(
        rf"\[(\d\d:\d\d:\d\d)\] \[Client thread/INFO\]: "
        rf"\[CHAT\] .*{nickname}.*[:>] ~([-a-z+ ]+)([)(А-Яа-яЁё, \d]+)"
    )

    for line in file:
        if "был" in line and (match := boss_pattern.match(line)):
            processing_line_with_boss(
                match,
                boss_respawn,
                bosses_cooldown,
                notification_duration,
            )
        if (
            file.name.rsplit("\\", 1)[1] == "latest.log"
            and nickname in line
            and (match := command_pattern.match(line))
        ):
            command_time = time.fromisoformat(match.group(1))
            command_time = datetime.combine(
                datetime.now().date(), command_time
            ).timestamp()
            command = match.group(2)[:-1]
            params = match.group(3)
            if datetime.now().timestamp() - command_time <= 120:
                match command:
                    case "d":
                        settings_changed = change_duration_notification(
                            params,
                            notification_duration,
                        )
                    case "b add":
                        settings_changed = add_boss(
                            params,
                            notification_duration,
                        )
                    case "b skip":
                        settings_changed = skip_boss(
                            params,
                            boss_respawn,
                            notification_duration,
                        )
                    case "bl add":
                        settings_changed = add_to_blacklist(
                            params, notification_duration
                        )
                    case "bl remove":
                        settings_changed = remove_from_blacklist(
                            params, notification_duration
                        )
                    case "m":
                        settings_changed = set_timer_to_mine(
                            params,
                            notification_duration,
                        )
                    case _:
                        NOTIFIER.show_toast(
                            "Ooops...",
                            "Неправильная команда",
                            NOTIFIER.error_ico_path,
                            notification_duration,
                        )
                        continue
    return settings_changed


def launch_boss_notifications(
    boss_respawn, blacklist, notification_duration, colored, rainbow_names
):
    """
    Функция, создающая и запускающая всплывающие оповещения о боссах
    :param boss_respawn: Словарь, ключ - имя босса, значение - время его следующего респавна
    :param blacklist: Список боссов, о которых не будут присылаться оповещения
    :param notification_duration: Длительность одного оповещения в секундах
    :param colored: Булевое значение, нужно ли использовать цветные названия
    :param rainbow_names: Словарь, ключ - обычное название, значение - цветное название
    :return: None
    """
    for_print = []
    for boss, respawn_time in boss_respawn.items():
        for_print.append([boss, respawn_time])
        if boss not in blacklist and get_time() >= respawn_time:
            NOTIFIER.show_toast(
                "Босс",
                boss,
                ICONS_PATH / f"{boss}.ico",
                notification_duration,
            )
            sleep(0.1)
    for_print.sort(key=lambda pair: pair[1])
    for pair in for_print:
        plural = pair[0] == "Всадники апокалипсиса"
        if colored:
            pair[0] = rainbow_names[pair[0]]
        if plural:
            print(
                pair[0],
                "заспавнятся примерно в",
                datetime.fromtimestamp(pair[1]).strftime("%H:%M:%S"),
            )
        else:
            print(
                pair[0],
                "заспавнится примерно в",
                datetime.fromtimestamp(pair[1]).strftime("%H:%M:%S"),
            )


def validate_gz(filename):
    """
    Функция, проверяющая, что файл является архивным с расширением GZ и создан в сегодняшний день
    :param filename: Название валидируемого файла
    :return: bool - удовлетворяет ли название требованиям
    """
    body, tail = filename.stem, filename.suffix
    if not body.startswith(datetime.now().strftime("%Y-%m-%d")):
        return False
    if not tail == ".gz":
        return False
    return True


def load_settings_variables():
    """
    Функция, загружающая и возвращающая все переменные из файла с настройками
    :return: Кортеж с переменными: словарь босс-кулдаун, чёрный список, длительность оповещения,
    словарь шахта-кулдаун, булевое значение цветные ли названия, список шахт для оповещения
    """
    with open("settings.yaml", encoding="windows-1251") as file:
        settings = yaml.safe_load(file)
    bosses_cooldown = settings["bosses_cooldown"]
    bosses_cooldown = {
        name: cooldown * 60 for name, cooldown in bosses_cooldown.items()
    }
    if "blacklist" in settings:
        blacklist = settings["blacklist"]
    else:
        blacklist = []
    notification_duration = settings["notification_duration"]
    mines_cooldown = settings["mines_cooldown"]
    colored = settings["colored"]
    if "mines_notifications" in settings:
        mines_notifications = settings["mines_notifications"]
        return (
            bosses_cooldown,
            blacklist,
            notification_duration,
            mines_cooldown,
            colored,
            mines_notifications,
        )
    return bosses_cooldown, blacklist, notification_duration, mines_cooldown, colored


def change_duration_notification(params, notification_duration):
    """
    Функция, обрабатывающая команду ~d. Изменяет длительность оповещения
    :param params: Полученные от пользователя параметры команды
    :param notification_duration: Длительность одного оповещения в секундах
    :return: bool - изменены ли параметры
    """
    if not params.isdigit():
        NOTIFIER.show_toast(
            "Ooops...",
            "Длительность оповещения должна быть цифрой (количество секунд)",
            NOTIFIER.error_ico_path,
            notification_duration,
        )
        return False
    params = int(params)
    with open("settings.yaml", encoding="windows-1251") as config:
        settings = yaml.safe_load(config)
    settings["notification_duration"] = params
    with open("settings.yaml", "w", encoding="windows-1251") as config:
        yaml.safe_dump(settings, config, indent=4, allow_unicode=True, sort_keys=False)
    NOTIFIER.show_toast(
        "Успешно!",
        "Длительность оповещения изменена",
        NOTIFIER.success_ico_path,
        notification_duration,
    )
    return True


def add_boss(params, notification_duration):
    """
    Функция, обрабатывающая команду ~b add. Добавляет нового босса
    :param params: Полученные от пользователя параметры команды
    :param notification_duration: Длительность одного оповещения в секундах
    :return: bool - изменены ли параметры
    """
    params = params.rsplit(" ", 1)
    if not params[1].isdigit():
        NOTIFIER.show_toast(
            "Ooops...",
            "Кулдаун респавна босса должен быть цифрой (количество минут)",
            NOTIFIER.error_ico_path,
            notification_duration,
        )
        return False
    with open("settings.yaml", encoding="windows-1251") as config:
        settings = yaml.safe_load(config)
    settings["bosses_cooldown"][params[0]] = int(params[1])
    with open("settings.yaml", "w", encoding="windows-1251") as config:
        yaml.safe_dump(settings, config, indent=4, allow_unicode=True, sort_keys=False)
    NOTIFIER.show_toast(
        "Успешно!", "Босс добавлен", NOTIFIER.success_ico_path, notification_duration
    )
    return True


def skip_boss(params, boss_respawn, notification_duration):
    """
    Функция, обрабатывающая команду ~b skip. Пропускает босса
    :param params: Полученные от пользователя параметры команды
    :param boss_respawn: Словарь, ключ - имя босса, значение - время его следующего респавна
    :param notification_duration: Длительность одного оповещения в секундах
    :return: bool - изменены ли параметры
    """
    one_boss = [params] == (params := [boss.strip() for boss in params.split(",")])
    for boss in params:
        if boss not in boss_respawn:
            NOTIFIER.show_toast(
                "Ooops...",
                "Указано некорректное имя босса",
                NOTIFIER.error_ico_path,
                notification_duration,
            )
            return False
        del boss_respawn[boss]
    if one_boss:
        NOTIFIER.show_toast(
            "Успешно!",
            "Босс пропущен",
            NOTIFIER.success_ico_path,
            notification_duration,
        )
    else:
        NOTIFIER.show_toast(
            "Успешно!",
            "Боссы пропущены",
            NOTIFIER.success_ico_path,
            notification_duration,
        )
    return False


def add_to_blacklist(params, notification_duration):
    """
    Функция, обрабатывающая команду ~bl add. Добавляет боссов в чёрный список
    :param params: Полученные от пользователя параметры команды
    :param notification_duration: Длительность одного оповещения в секундах
    :return: True - параметры изменены
    """
    params = [boss.strip() for boss in params.split(",")]
    with open("settings.yaml", encoding="windows-1251") as config:
        settings = yaml.safe_load(config)
    if "blacklist" not in settings:
        settings["blacklist"] = params
    else:
        settings["blacklist"] += params
    with open("settings.yaml", "w", encoding="windows-1251") as config:
        yaml.safe_dump(settings, config, indent=4, allow_unicode=True, sort_keys=False)
    NOTIFIER.show_toast(
        "Успешно!",
        "Чёрный список обновлён",
        NOTIFIER.success_ico_path,
        notification_duration,
    )
    return True


def remove_from_blacklist(params, notification_duration):
    """
    Функция, обрабатывающая команду ~bl remove. Удаляет боссов из чёрного списка
    :param params: Полученные от пользователя параметры команды
    :param notification_duration: Длительность одного оповещения в секундах
    :return: True - параметры изменены
    """
    params = [boss.strip() for boss in params.split(",")]
    with open("settings.yaml", encoding="windows-1251") as config:
        settings = yaml.safe_load(config)
    settings["blacklist"] = [
        name for name in settings["blacklist"] if name not in params
    ]
    with open("settings.yaml", "w", encoding="windows-1251") as config:
        yaml.safe_dump(settings, config, indent=4, allow_unicode=True, sort_keys=False)
    NOTIFIER.show_toast(
        "Успешно!",
        "Чёрный список обновлён",
        NOTIFIER.success_ico_path,
        notification_duration,
    )
    return True


def processing_line_with_boss(
    match, boss_respawn, bosses_cooldown, notification_duration
):
    """
    Функция, обрабатывающая строку с информацией об убийстве босса
    :param match: Найденное совпадение в строке с регулярным выражением
    :param boss_respawn: Словарь, ключ - имя босса, значение - время его следующего респавна
    :param bosses_cooldown: Словарь, ключ - имя босса, значение - его кулдаун
    :param notification_duration: Длительность одного оповещения в секундах
    :return: None
    """
    kill_time = time.fromisoformat(match.group(1))
    kill_time = datetime.combine(datetime.now().date(), kill_time).timestamp()
    name = match.group(3)
    if name not in bosses_cooldown:
        NOTIFIER.show_toast(
            "Ooops...",
            f"Босса '{name}' нет в списке. Добавьте его",
            NOTIFIER.error_ico_path,
            notification_duration,
        )
    else:
        boss_respawn[name] = kill_time + bosses_cooldown[name]


def remind_about_service(notification_duration):
    """
    Функция, выводящая всплывающие уведомления о службах в церкви
    :param notification_duration: Длительность уведомления
    :return: None
    """
    if datetime.now(ZoneInfo("Europe/Moscow")).strftime("%H:%M:%S") in {
        "06:56:00",
        "12:56:00",
        "18:56:00",
        "00:56:00",
    }:
        NOTIFIER.show_toast(
            "Служба",
            "Открылась запись на служение!",
            ICONS_PATH / "Служба.ico",
            notification_duration,
        )


def remind_about_mine(cooldown, stopwatch, name, notification_duration):
    """
    Функция, оповещающая об обновлении шахты за 3 секунды до этого
    :param cooldown: Кулдаун шахты в секундах
    :param stopwatch: Секундомер, считающий до кулдауна
    :param name: Название шахты
    :param notification_duration: Длительность уведомления
    :return: Количество секунд на секундомере
    """
    if stopwatch == (cooldown - 3):
        NOTIFIER.show_toast(
            "Шахта",
            f'Шахта "{name}" обновилась',
            ICONS_PATH / f"{name}.ico",
            notification_duration,
        )
        return stopwatch + 1
    if stopwatch == cooldown:
        return 0
    return stopwatch + 1


def set_timer_to_mine(params, notification_duration):
    """
    Функция, обрабатывающая команду ~m. Добавляет шахту в список для оповещения
    :param params: Полученные от пользователя параметры команды
    :param notification_duration: Длительность одного оповещения в секундах
    :return: bool - изменены ли параметры
    """
    with open("settings.yaml", encoding="windows-1251") as config:
        settings = yaml.safe_load(config)
    if params not in settings["mines_cooldown"]:
        NOTIFIER.show_toast(
            "Ooops...",
            "Неправильное название шахты",
            NOTIFIER.error_ico_path,
            notification_duration,
        )
        return False
    if "mines_notifications" not in settings:
        settings["mines_notifications"] = [params]
    else:
        settings["mines_notifications"] += [params]
    with open("settings.yaml", "w", encoding="windows-1251") as config:
        yaml.safe_dump(settings, config, indent=4, allow_unicode=True, sort_keys=False)
    NOTIFIER.show_toast(
        "Успешно!", "Шахта добавлена", NOTIFIER.success_ico_path, notification_duration
    )
    return True


def main():
    """
    Главная функция, связывающая весь функционал реализованных функций
    :return: None
    """
    system("color")
    with open("settings.yaml", encoding="windows-1251") as config:
        settings = yaml.safe_load(config)
    if "mines_notifications" in settings:
        del settings["mines_notifications"]
    with open("settings.yaml", "w", encoding="windows-1251") as config:
        yaml.safe_dump(settings, config, indent=4, allow_unicode=True, sort_keys=False)
    boss_respawn = {}
    boss_notifications = 59
    (
        bosses_cooldown,
        blacklist,
        notification_duration,
        mines_cooldown,
        colored,
        *mines_notifications,
    ) = load_settings_variables()
    mines_stopwatches = {mine: 0 for mine in mines_cooldown}
    processing_old_logs(boss_respawn, bosses_cooldown, notification_duration)
    with open(LOG_PATH / "latest.log", encoding="utf-8") as file:
        line = file.readline()
        nickname = line[line.find("Setting user: ") + 14 :].rstrip()
        while True:
            boss_notifications += 1
            remind_about_service(notification_duration)
            if processing_log(
                file, boss_respawn, bosses_cooldown, notification_duration, nickname
            ):
                (
                    bosses_cooldown,
                    blacklist,
                    notification_duration,
                    mines_cooldown,
                    colored,
                    *mines_notifications,
                ) = load_settings_variables()
            if mines_notifications:
                for mine in mines_notifications[0]:
                    mines_stopwatches[mine] = remind_about_mine(
                        mines_cooldown[mine],
                        mines_stopwatches[mine],
                        mine,
                        notification_duration,
                    )
            if boss_notifications == 60:
                print("-" * 57)
                launch_boss_notifications(
                    boss_respawn,
                    blacklist,
                    notification_duration,
                    colored,
                    RAINBOW_NAMES,
                )
                boss_notifications = 0
            sleep(1)


if __name__ == "__main__":
    main()
