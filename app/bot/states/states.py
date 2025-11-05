from aiogram.fsm.state import State, StatesGroup


class DialogSG(StatesGroup):
    dialog = State()

class NewWords(StatesGroup):
    new_words = State()