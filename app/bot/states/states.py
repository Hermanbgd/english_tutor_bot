from aiogram.fsm.state import State, StatesGroup


class DialogSG(StatesGroup):
    dialog = State()

class OutDialog(StatesGroup):
    out_dialog = State()