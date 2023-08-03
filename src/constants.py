import platform
from os import path
from pathlib import Path

OS = platform.system() + platform.release()
LOG_PATH = path.join(
    Path.home(), "AppData", "Roaming", ".vimeworld", "minigames", "logs"
)

RAINBOW_NAMES = {
    "Королевский зомби": "\033[37mКоролевский зомби\033[0m",
    "Холуй": "\033[37mХолуй\033[0m",
    "Сточный слизень": "\033[32mСточный слизень\033[0m",
    "Фенрир": "\033[31mФенрир\033[0m",
    "Всадники апокалипсиса": "\033[37mВсадники апокалипсиса\033[0m",
    "Матка": "\033[32mМатка\033[0m",
    "Коровка из Коровёнки": "\033[31mК\033[33mор\033[32mо\033[36mв\033[34mк\033[33mа"
    " \033[31mи\033[33mз К\033[32mо\033[36mр\033[34mо\033"
    "[35mв\033[31mё\033[33mнк\033[32mи\033[0m",
    "Левиафан": "\033[33mЛевиафан\033[0m",
    "Йети": "\033[36mЙети\033[0m",
    "Житель края": "\033[35mЖитель края\033[0m",
    "Небесный владыка": "\033[34mНебесный владыка\033[0m",
    "Хранитель подводного мира": "\033[36mХранитель подводного мира\033[0m",
}