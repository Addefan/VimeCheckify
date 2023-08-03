from abc import ABC, abstractmethod

from src.constants import OS, ICONS_PATH


class BaseNotifier(ABC):
    error_ico_path = ICONS_PATH / "error.ico"
    success_ico_path = ICONS_PATH / "success.ico"

    @abstractmethod
    def show_toast(self, title, message, icon):
        """
        Функция, выводящая всплывающее уведомление
        :param os: Операционная система, на которой вызывается уведомление
        :param title: Заголовок уведомления
        :param message: Текст уведомления
        :param icon: Путь к иконке уведомления
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
    def __init__(self, notification_duration=3):
        self.import_toaster()
        self.notification_duration = notification_duration
        self.notifier = globals().get(f"{OS}Notifier", "ErrorNotifier")(
            notification_duration
        )

    def show_toast(self, title, message, icon):
        self.notifier.show_toast(title, message, icon)


class Windows10Notifier(BaseNotifier):
    def show_toast(self, title, message, icon):
        ToastNotifier().show_toast(title, message, icon, self.notification_duration)


class Windows11Notifier(BaseNotifier):
    def show_toast(self, title, message, icon):
        icon = {"src": icon, "placement": "appLogoOverride"}
        return toast(title, message, icon=icon, duration=self.notification_duration)


class ErrorNotifier(BaseNotifier):
    def show_toast(self, title, message, icon):
        print("Извините, ваша операционная система не поддерживается для оповещений")
