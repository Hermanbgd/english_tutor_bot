from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

# Inline keyboard builders for error analysis toggling

ERROR_BTN = "show_analysis"
HIDE_BTN = "hide_analysis"


def error_analysis_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="Разбор ошибок", callback_data=ERROR_BTN)]]
    )


def hide_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="Скрыть", callback_data=HIDE_BTN)]]
    )


def text_button(text: str, callback_data: str) -> InlineKeyboardMarkup:
    button = InlineKeyboardButton(text=text, callback_data=callback_data)
    keyboard = InlineKeyboardMarkup(inline_keyboard=[[button]])
    return keyboard
