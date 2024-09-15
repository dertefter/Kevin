import sys

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import QApplication, QWidget, QHBoxLayout, QVBoxLayout, QLabel, QFrame
from qfluentwidgets import *
from qframelesswindow.utils import getSystemAccentColor

from app_config import AppConfig
from mind import Mind, Message


class Widget(QFrame):

    def __init__(self, text: str, parent=None):
        super().__init__(parent=parent)
        self.label = SubtitleLabel(text, self)
        self.hBoxLayout = QHBoxLayout(self)

        setFont(self.label, 24)
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.hBoxLayout.addWidget(self.label, 1, Qt.AlignmentFlag.AlignCenter)

        # Must set a globally unique object name for the sub-interface
        self.setObjectName(text.replace(' ', '-'))


class UI(MSFluentWindow):

    def __init__(self, parent=None):
        super().__init__(parent)
        cfg = AppConfig()
        qconfig.load('config/config.json', cfg)
        self.mind = Mind()
        self.tb = TitleBar(self)
        self.setTitleBar(self.tb)
        self.mind.titleBar = self.tb
        chat = Chat(parent=self)
        settings = Settings(parent=self, cfg=cfg)
        chat.set_mind(self.mind)
        self.resize(800, 600)
        self.setWindowTitle('Kevin AI')
        self.setWindowIcon(QIcon('res/anim/idle.gif'))
        setTheme(theme=Theme.AUTO)
        if sys.platform in ["win32", "darwin"] and False:
            setThemeColor(getSystemAccentColor(), save=False)
        else:
            setThemeColor("#cb4483", save=False)
        # self.addSubInterface(chat, FluentIcon.CHAT,'Чат', selectedIcon=FluentIcon.CHAT)
        # self.navigationInterface.addItem(settings, FluentIcon.SETTING, 'settingsInterface', position=NavigationItemPosition.BOTTOM)

        self.addSubInterface(chat, FluentIcon.CHAT, 'Чат')
        self.addSubInterface(settings, FluentIcon.SETTING, 'Настройки')

        self.stackedWidget.setStyleSheet('QWidget{background: transparent}')


class Chat(QWidget):
    mind: Mind = None

    def set_mind(self, mind):
        self.mind = mind

    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.setObjectName('chatInterface')
        # Основной вертикальный лейаут
        self.layout = QVBoxLayout(self)

        # Полоса прокрутки для сообщений
        self.scroll_area = SmoothScrollArea(self)
        self.scroll_area.setWidgetResizable(True)

        # Виджет для сообщений
        self.messages_widget = SimpleCardWidget()
        self.messages_layout = QVBoxLayout(self.messages_widget)
        self.messages_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        self.scroll_area.setWidget(self.messages_widget)
        self.layout.addWidget(self.scroll_area)

        # Горизонтальный лейаут для поля ввода и кнопки
        self.input_layout = QHBoxLayout()

        # Поле ввода текста
        self.text_input = LineEdit(self)
        self.input_layout.addWidget(self.text_input)

        # Кнопка отправки
        self.send_button = PrimaryToolButton(self)
        self.send_button.setIcon(FluentIcon.SEND_FILL)
        self.send_button.clicked.connect(self.send_message)
        self.input_layout.addWidget(self.send_button)

        # Добавляем горизонтальный лейаут в основной вертикальный
        self.layout.addLayout(self.input_layout)

    def send_message(self):
        text = self.text_input.text()
        if text:
            card = MessageCard(title="Вы")
            card2 = MessageCard(title="Kevin")
            self.messages_layout.addWidget(card)
            card.set_content(Message(text))
            card2.set_content(Message(""))
            resp = self.mind.get_ai_response(text, card2)
            self.messages_layout.addWidget(card2)
            self.scroll_area.verticalScrollBar().setValue(-1000)
            # Очищаем поле ввода
            self.text_input.clear()

            # Прокручиваем вниз к последнему сообщению
            self.scroll_area.verticalScrollBar().setValue(
                self.scroll_area.verticalScrollBar().maximum()
            )


class Settings(QFrame):
    def __init__(self, parent=None, cfg=None):
        super().__init__(parent=parent)
        self.setObjectName('settingsInterface')
        # Основной вертикальный лейаут
        self.layout = QVBoxLayout(self)

        # Полоса прокрутки для сообщений
        self.scroll_area = SmoothScrollArea(self)
        self.scroll_area.setWidgetResizable(True)
        self.card = ComboBoxSettingCard(
            configItem=cfg.onlineMvQuality,
            icon=FluentIcon.ZOOM,
            title="Провайдер",
            content="Провайдер отвечает за доступ к AI-моделям",
            texts=["100"]
        )
        self.scroll_area.setWidget(self.card)
        self.layout.addWidget(self.scroll_area)


class MessageCard(CardWidget):

    def __init__(self, title, parent=None):
        super().__init__(parent)
        self.titleLabel = StrongBodyLabel(title, self)
        self.contentLabel = BodyLabel("", self)
        self.contentLabel.setWordWrap(True)
        self.contentLabel.setAcceptDrops(False)
        self.progressbar = IndeterminateProgressBar(start=True)
        self.vBoxLayout = QVBoxLayout(self)
        self.code_viewer = QLabel(self)
        self.code_viewer.setStyleSheet("QLabel { background-color : black; color : white; }")
        self.vBoxLayout.setContentsMargins(10, 10, 10, 10)
        self.vBoxLayout.addWidget(self.titleLabel, 0, Qt.AlignmentFlag.AlignVCenter)
        self.vBoxLayout.addWidget(self.contentLabel, 0, Qt.AlignmentFlag.AlignVCenter)
        self.vBoxLayout.addWidget(self.progressbar, 0, Qt.AlignmentFlag.AlignVCenter)
        self.vBoxLayout.addWidget(self.code_viewer, 0, Qt.AlignmentFlag.AlignVCenter)

    def set_content(self, content: Message):
        if content.code:
            self.code_viewer.setVisible(True)
            self.code_viewer.setText(content.code)
        else:
            self.code_viewer.setVisible(False)
        if content.text:
            self.contentLabel.setText(content.text)
            self.progressbar.setVisible(False)
        else:
            self.progressbar.setVisible(True)


class TitleBar(MSFluentTitleBar):
    """ Custom title bar """

    anim_signal = pyqtSignal(int)

    def __init__(self, parent):
        super().__init__(parent)
        self.b = ImageLabel(parent=self)
        self.anim_signal.connect(self.update_animation)
        self.set_animation(0)

        self.b.setAlignment(Qt.AlignmentFlag.AlignCenter)

    def update_animation(self, value):
        s = "res/anim/idle.gif"
        if (value == 0):
            s = "res/anim/idle.gif"
        else:
            s = "res/anim/work.gif"
        self.b.setImage(s)
        self.b.scaledToHeight(self.height())

    def set_animation(self, n):
        self.anim_signal.emit(n)

    def resizeEvent(self, e):
        w, h = self.width(), self.height()
        self.b.move(w // 2 - self.b.width() // 2, h // 2 - self.b.height() // 2)
        self.b.setScaledContents(True)


if __name__ == '__main__':
    app = QApplication(sys.argv)
    w = UI()
    w.show()
    app.exec()
