from abc import ABC, abstractmethod

from src.constants import OS, ICONS_PATH


class BaseNotifier(ABC):
    error_ico_path = ICONS_PATH / "error.ico"
    success_ico_path = ICONS_PATH / "success.ico"

    @abstractmethod
    def show_toast(self, title="", message="", icon="", duration=3):
        """
        Функция, выводящая всплывающее уведомление
        :param os: Операционная система, на которой вызывается уведомление
        :param title: Заголовок уведомления
        :param message: Текст уведомления
        :param icon: Путь к иконке уведомления
        :param duration: Длительность уведомления
        :return: None
        """
        ...

    @staticmethod
    def import_toaster():
        if OS == "Windows10":
            pass
        elif OS == "Windows11":
            pass


class Notifier(BaseNotifier):
    def __init__(self):
        self.import_toaster()
        self.notifier = globals().get(f"{OS}Notifier", "ErrorNotifier")()

    def show_toast(self, title="", message="", icon="", duration=3):
        return self.notifier.show_toast(title, message, icon, duration)


class Windows10Notifier(BaseNotifier):
    def show_toast(self, title="", message="", icon="", duration=3):
        return ToastNotifier().show_toast(title, message, icon, duration)


class Windows11Notifier(BaseNotifier):
    def show_toast(self, title="", message="", icon="", duration=3):
        icon = {"src": icon, "placement": "appLogoOverride"}
        return toast(title, message, icon=icon, duration=duration)


class ErrorNotifier(BaseNotifier):
    def show_toast(self, title="", message="", icon="", duration=3):
        print("Извините, ваша операционная система не поддерживается для оповещений")
