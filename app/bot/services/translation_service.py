from googletrans import Translator


async def translate_en_to_ru(text):
    """
    Переводит текст с английского на русский.
    """
    translator = Translator()
    translated = await translator.translate(text, src='en', dest='ru', timeout=20)
    return translated.text