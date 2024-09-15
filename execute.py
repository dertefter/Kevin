
def answer():
    import os

    desktop_path = os.path.join(os.path.expanduser('~'), 'Desktop')
    project_2_folder_path = os.path.join(desktop_path, 'Проекты', 'Проект 2')
    file_path = os.path.join(project_2_folder_path, 'Новый документ.txt')

    poem = """На холмах Грузии лежит ночная мгла;
Шумит Арагва предо мною.
Мне грустно и легко; печаль моя светла;
Печаль моя полна тобою,

Тобой, одной тобой… Унынью моего
Ничто не мучит, не тревожит,
И сердце вновь горит и любит — оттого,
Что не любить оно не может."""

    if os.path.exists(file_path):
        with open(file_path, 'w', encoding='utf-8') as file:
            file.write(poem)
        return "Я написал стихотворение в текстовом документе в папке 'Проект 2'."
    else:
        return "Документ не найден в папке 'Проект 2'."

