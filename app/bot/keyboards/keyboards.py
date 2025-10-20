from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def text_button(text: str, callback_data: str) -> InlineKeyboardMarkup:
    button = InlineKeyboardButton(text=text, callback_data=callback_data)
    keyboard = InlineKeyboardMarkup(inline_keyboard=[[button]])
    return keyboard


# def get_lang_settings_kb(i18n: dict, locales: list[str], checked: str) -> InlineKeyboardMarkup:
#     buttons = []
#     for locale in sorted(locales):
#         if locale == "default":
#             continue
#         if locale == checked:
#             buttons.append(
#                 [
#                     InlineKeyboardButton(
#                         text=f"🔘 {i18n.get(locale)}", callback_data=locale
#                     )
#                 ]
#             )
#         else:
#             buttons.append(
#                 [
#                     InlineKeyboardButton(
#                         text=f"⚪️ {i18n.get(locale)}", callback_data=locale
#                     )
#                 ]
#             )
#     buttons.append(
#         [
#             InlineKeyboardButton(
#                 text=i18n.get("cancel_lang_button_text"),
#                 callback_data="cancel_lang_button_data"
#             ),
#             InlineKeyboardButton(
#                 text=i18n.get("save_lang_button_text"),
#                 callback_data="save_lang_button_data"
#             ),
#         ]
#     )
#     return InlineKeyboardMarkup(inline_keyboard=buttons)
