from better_profanity import profanity
import os

# Путь к файлу относительно корня проекта
BAD_WORDS_FILE = 'ru_bad_words.txt'

if os.path.exists(BAD_WORDS_FILE):
    profanity.load_censor_words_from_file(BAD_WORDS_FILE)
    print(f"[Censor] Загружено {len(profanity.CENSOR_WORDSET)} слов из {BAD_WORDS_FILE}")
else:
    print(f"[Censor] Файл {BAD_WORDS_FILE} не найден! Используется встроенный словарь.")
    # Если файла нет, можно добавить базовые русские слова вручную:
    profanity.add_censor_words(['хуй', 'пизда', 'блядь', 'ебать', 'мудак', 'говно'])

def censor_text(text: str) -> str:
    if not text:
        return text
    return profanity.censor(text)

def is_text_safe(text: str) -> bool:
    if not text:
        return True
    return not profanity.contains_profanity(text)