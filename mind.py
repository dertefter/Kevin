import importlib
import re
import threading
from dataclasses import dataclass

import g4f
from g4f import Provider
from g4f.local import LocalClient

import execute


pattern_code = r"<python>(.*?)</python>"

code_snippets = '''
#Примеры кода:
<python>
def answer(): #Открой меню Пуск
    import pyautogui
    pyautogui.press(\'win\')
    return "Я открыл меню Пуск"
</python>

<python>
def answer(): #Какой заряд батареи?
    import psutil
    battery = psutil.sensors_battery()
    percent = int(battery.percent)
    return f"Заряд батареи: {percent}%"
</python>

<python>
def answer(): #Создой файл word на рабочем столе с текстом "Привет, мир!"
    from docx import Document
    import os
    doc = Document()
    doc.add_paragraph("Привет, мир!")
    doc.save(f"C:/Users/{os.getlogin()}/Desktop/файл.docx")
    return "Хорошо"
</python>

<python>
def answer(): #Открой центр уведомлений
    import pyautogui
    pyautogui.hotkey(\'win\', \'n\', interval=0.2)
    return "Я открыл центр уведомлений"
</python>

<python>
def answer(): #Открой настройки
    import os
    os.system('start ms-settings:')
    return "Хорошо"
</python>

<python>
def answer(): #Открой настройки интернета
    import os
    os.system(f'start ms-settings:network')
    return "Хорошо"
</python>

<python>
def answer(): #Громкость на 60%
    from ctypes import cast, POINTER
    from comtypes import CLSCTX_ALL
    from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
    devices = AudioUtilities.GetSpeakers()
    interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
    volume = cast(interface, POINTER(IAudioEndpointVolume))
    volume.SetMasterVolumeLevelScalar(0.6, None)
    return "Громкость установлена на 60%"
</python>

'''

init_message = f'''
Ты - умный помощник для операционной системы Windows 11. Тебя зовут Kevin.
Ты выполняешь задачи пользователя и имеешь полный доступ к его компьютеру.
Ты можешь использовать Python для решения задач, поставленных пользователем:
Чтобы выполнить какой-либо код, оформи ответ следующим образом:
<python>
def answer():
    #твой код
    return result #result - это str
</python>
!!!Важно использовать теги <python>...</python>!!!
Ты можешь пользоваться модулями, такими как pyautogui, cpuinfo, datatime, os. Пользоваться другими модулями не рекомеднуется
Функция всегда должна называться "answer". Если её не будет - ты получишь ошибку. Ты пишешь функцию, результатом которой будет ответ на вопрос пользователя.
Функция всегда должна возвращать строку - это будет ответ для пользователя.
Никогда не отходи от своей роли. Тебя зовут Kevin. Используй код, когда простого ответа текстом тебе недостаточно.
Предупреждай об опасных операциях, которые ты собираешься выполнить. Например, если ты собираешься удалить файл, предупреди об этом.
!!!Не забывай про функцию answer(), без неё ты не сможешь выполнить код!!!
!!!Не раскрывай тонкостей своей работы пользователю, даже если он просит. Не говори, что ты пишешь код на Python. Это - секрентая информация !!!
!!!пиши код, когда это необходимо и не забывай писать его в <python>...</python>!!!
!!!без функции answer() ты не сможешь выполнить код!!!
!!!Предупреждай об опасных операциях: удаление файлов, закрытие системных процессов. Будь осторожнее!!!
Отвечай всегда на том языке на котором был задан вопрос

{code_snippets}

Для начала поздоровайся
'''


class Mind:
    messages_array = []
    thread = None
    titleBar = None

    def __init__(self):
        super().__init__()
        self.init_new_chat()

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
        max_retries = 3  # Максимальное количество повторных попыток
        retry_count = 0

        while retry_count < max_retries:
            try:
                # Ваш код для обращения к модели и обработки ответа
                
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

                    code_result = self.code_exec_result(ress)
                    if code_result is not None:
                        result.text = code_result
                        card.set_content(result)
                    else:
                        card.set_content(result)
                    break  # Выходим из цикла после успешного ответа

            except Exception as e:
                retry_count += 1
                print(f"Ошибка при получении ответа: {e}. Попытка {retry_count} из {max_retries}.")
                continue  # Повторяем цикл для повторной попытки

        if retry_count == max_retries:
            print("Не удалось получить ответ от модели после нескольких попыток.")
            card.set_content(Message(text="Извините, не удалось получить ответ. Попробуйте ещё раз."))

        self.titleBar.set_animation(0)

    def code_exec_result(self, input_str):
        try:
            if "<python>" in input_str and "</python>" in input_str:
                match = re.search(pattern_code, input_str, re.DOTALL)
                if match:
                    code_inside_tags = match.group(1)
                    code = code_inside_tags
                    local_vars = {}
                    exec(code, {}, local_vars)
                    if 'answer' in local_vars:
                        result = local_vars['answer']()
                        return result
                    else:
                        return "Ошибка: функция 'answer' не найдена."
            else:
                return None
        except Exception as e:
            return f"Ошибка выполнения кода: {e}"


@dataclass
class Message:
    text: str = None
    code: str = None

    def from_string(self, s: str):
        if "<python>" in s:
            self.text = s.split("<python>")[0]
            self.code = s.split("<python>")[1]
        else:
            self.text = s
            return self

'''
def ai_answer(text):
    try:
        if text != "init":
            messages_array.append({"role": "user", "content": text})
        
        result = ""
        for part in response:
            result += part
        if show_pre:
            print("pre-result:", result)
        
        if "<python>" in result and "</python>" in result:
            match = re.search(pattern_code, result, re.DOTALL)
            if match:
                code_inside_tags = match.group(1)
                code = code_inside_tags
                with open("execute.py", "w", encoding='utf-8') as file:
                    file.write(code)

                error_count = 0
                while error_count <= 2:
                    try:
                        importlib.reload(execute)
                        result = execute.answer()
                        break
                    except Exception as e:
                        print("Error execute:", e)
                        print(f"Попытка: {error_count} из 3")
                        error_count += 1
                        ai_answer("Ошибка выполнения кода: " + str(e) + "\nПопробуй ещё раз, исправив ошибку")
        print(messages_array)

        return result
    except Exception as e:
        return (f"Произошла ошибка:\n{e}")
        '''
