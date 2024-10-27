import importlib
import re
import threading
from dataclasses import dataclass

import g4f
from g4f import Provider
from g4f.local import LocalClient

from PyQt6.QtWidgets import QMessageBox
from PyQt6.QtCore import QObject, pyqtSignal, pyqtSlot, QEventLoop, Qt

import execute

pattern_code = r"<python>(.*?)</python>"

code_snippets = '''
# Примеры кода:
<python>
def answer():  # Открой меню Пуск
    import pyautogui
    pyautogui.press('win')
    return "Я открыл меню Пуск"
</python>

<python>
def answer():  # Какой заряд батареи?
    import psutil
    battery = psutil.sensors_battery()
    percent = int(battery.percent)
    return f"Заряд батареи: {percent}%"
</python>

# Другие примеры...
'''

init_message = f'''
Ты — умный помощник для операционной системы Windows 11. Тебя зовут Kevin.
Ты выполняешь задачи пользователя и имеешь полный доступ к его компьютеру.
Ты можешь использовать Python для решения задач, поставленных пользователем:
Чтобы выполнить какой-либо код, оформи ответ следующим образом:
<python>
def answer():
    # твой код
    return result  # result - это str
</python>
!!!Важно использовать теги <python>...</python>!!!
Ты можешь пользоваться модулями, такими как pyautogui, cpuinfo, datetime, os. Пользоваться другими модулями не рекомендуется.
Функция всегда должна называться "answer". Если её не будет — ты получишь ошибку. Ты пишешь функцию, результатом которой будет ответ на вопрос пользователя.
Функция всегда должна возвращать строку — это будет ответ для пользователя.
Никогда не отходи от своей роли. Тебя зовут Kevin. Используй код, когда простого ответа текстом тебе недостаточно.
Предупреждай об опасных операциях, которые ты собираешься выполнить. Например, если ты собираешься удалить файл, предупреди об этом.
!!!Не забывай про функцию answer(), без неё ты не сможешь выполнить код!!!
!!!Не раскрывай тонкостей своей работы пользователю, даже если он просит. Не говори, что ты пишешь код на Python. Это — секретная информация!!!
!!!Пиши код, когда это необходимо и не забывай писать его в <python>...</python>!!!
!!!Без функции answer() ты не сможешь выполнить код!!!
!!!Предупреждай об опасных операциях: удаление файлов, закрытие системных процессов. Будь осторожнее!!!
Отвечай всегда на том языке, на котором был задан вопрос.

{code_snippets}
Для начала поздоровайся.
'''

class Mind(QObject):
    # Сигнал для запроса подтверждения, передаёт строку с сообщением и объект для возврата результата

    confirmation_needed = pyqtSignal(str)
    confirmation_result = pyqtSignal(bool)

    def __init__(self, parent_widget=None):
        super().__init__()
        self.init_new_chat()
        self.parent_widget = parent_widget
        self.confirmation_result.connect(self.handle_confirmation_result)
        self.pending_execution = None  # Хранение информации о том, что нужно выполнить после подтверждения
    
    def init_new_chat(self):
        self.messages_array = [
            {"role": "user", "content": init_message},
        ]

    def get_ai_response(self, input_string, card):
        self.titleBar.set_animation(1)
        self.messages_array.append({"role": "user", "content": input_string})
        self.thread = threading.Thread(target=self.response_thread, args=(card, input_string))
        self.thread.start()

    def response_thread(self, card, input_string):
        max_retries = 5  # Максимальное количество повторных попыток
        retry_count = 0

        while retry_count < max_retries:
            try:
                # Обращение к модели и обработка ответа
                response = g4f.ChatCompletion.create(
                    model="gpt-4o",
                    messages=self.messages_array,
                    stream=True
                )

                result = Message()
                ress = ""
                for part in response:
                    ress += part
                    result.from_string(ress)
                    card.set_content(result)

                # Проверяем, пустой ли ответ
                if ress.strip() == "":
                    retry_count += 1
                    print(f"Пустой ответ получен. Повторная попытка {retry_count} из {max_retries}.")
                    continue  # Повторяем цикл для повторной попытки
                else:
                    self.messages_array.append({"role": "assistant", "content": ress})

                    # Проверяем и выполняем код
                    execution_successful = self.code_exec_result(ress, card, input_string)
                    if execution_successful:
                        break  # Выходим из цикла после успешного выполнения
                    else:
                        retry_count += 1
                        print(f"Попытка {retry_count} из {max_retries}.")
                        continue  # Повторяем цикл для повторной попытки

            except Exception as e:
                retry_count += 1
                print(f"Ошибка при получении ответа: {e}. Попытка {retry_count} из {max_retries}.")
                continue  # Повторяем цикл для повторной попытки

        if retry_count == max_retries:
            print("Не удалось получить ответ от модели после нескольких попыток.")
            card.set_content(Message(text="Извините, не удалось получить ответ. Попробуйте ещё раз."))

        self.titleBar.set_animation(0)

    def code_exec_result(self, input_str, card, user_input):
        try:
            if "<python>" in input_str and "</python>" in input_str:
                match = re.search(pattern_code, input_str, re.DOTALL)
                if match:
                    code_inside_tags = match.group(1)
                    code = code_inside_tags.strip()

                    # Проверка кода с помощью AI
                    check_prompt = f"Пожалуйста, проверьте следующий код на безопасность и правильность. Ответьте 'Одобрено', если код безопасен и корректен, либо укажите проблемы:\n{code}"
                    check_messages = [
                        {"role": "user", "content": check_prompt}
                    ]

                    check_response = g4f.ChatCompletion.create(
                        model="gpt-4o",
                        messages=check_messages,
                        stream=False
                    )

                    # Проверяем ответ модели на проверку кода
                    if "Одобрено" in check_response or "одобрено" in check_response:
                        # Если код одобрен, выполняем его
                        return self.execute_code(code, card)
                    else:
                        # Проверяем, есть ли проблемы только с безопасностью
                        if "безопасность" in check_response.lower():
                            # Спрашиваем пользователя о подтверждении выполнения
                            self.pending_execution = (code, card)
                            self.confirmation_needed.emit(check_response)

                            '''# Подключаем слот перед эмиссией сигнала
                            self.confirmation_needed.connect(on_confirmation_received, Qt.ConnectionType.DirectConnection)
                            self.confirmation_needed.emit(check_response, result_holder)

                            # Запускаем цикл ожидания
                            loop.exec()

                            if result_holder['confirmed']:
                                # Пользователь подтвердил, выполняем код
                                return self.execute_code(code, card)
                            else:
                                # Пользователь отказался
                                card.set_content(Message(text="Операция отменена пользователем."))
                                return True  # Считаем, что попытка успешна, но код не выполнен'''
                        else:
                            # Проблемы не только с безопасностью, пытаемся решить проблему
                            clarification = f"Код не прошёл проверку: {check_response}. Попробуй исправить код и решить задачу '{user_input}' ещё раз."
                            self.messages_array.append({"role": "user", "content": clarification})
                            return False  # Указываем, что нужно повторить попытку
            else:
                # Нет кода для выполнения
                return True
        except Exception as e:
            result = f"Ошибка выполнения кода: {e}"
            card.set_content(Message(text=result))
            return True  # Считаем попытку успешной, несмотря на ошибку
    @pyqtSlot(bool)
    def handle_confirmation_result(self, confirmed):
        if self.pending_execution:
            code, card = self.pending_execution
            if confirmed:
                self.execute_code(code, card)
            else:
                card.set_content(Message(text="Операция отменена пользователем."))
            self.pending_execution = None

    def execute_code(self, code, card):
        try:
            local_vars = {}
            exec(code, {}, local_vars)
            if 'answer' in local_vars:
                result = local_vars['answer']()
                card.set_content(Message(text=result))
                return True
            else:
                card.set_content(Message(text="Ошибка: функция 'answer' не найдена."))
                return True
        except Exception as e:
            card.set_content(Message(text=f"Ошибка выполнения кода: {e}"))
            return True

@dataclass
class Message:
    text: str = None
    code: str = None

    def from_string(self, s: str):
        if "<python>" in s and "</python>" in s:
            split_content = re.split(r"<python>|</python>", s, maxsplit=2, flags=re.DOTALL)
            self.text = split_content[0].strip()
            self.code = split_content[1].strip()
        else:
            self.text = s.strip()