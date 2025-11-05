from aiogram.types import BotCommand
from app.bot.enums.roles import UserRole


def get_main_menu_commands(role: UserRole):
    if role == UserRole.USER:
        return [
            BotCommand(command='/start', description='Старт диалога'),
            BotCommand(command='/restart', description='Перезапустить диалог'),
            BotCommand(command='/continue', description='Продолжить диалог'),
            BotCommand(command='/pause', description='Пауза диалога'),
            BotCommand(command='/stop', description='Стоп диалога'),
            BotCommand(command='/newwords', description='5 новых слов по теме'),
            BotCommand(command='/help', description='Помощь'),
        ]
    elif role == UserRole.ADMIN:
        return [
            BotCommand(command='/start', description='Старт диалога'),
            BotCommand(command='/restart', description='Перезапустить диалог'),
            BotCommand(command='/continue', description='Продолжить диалог'),
            BotCommand(command='/pause', description='Пауза диалога'),
            BotCommand(command='/stop', description='Стоп диалога'),
            BotCommand(command='/newwords', description='5 новых слов по теме'),
            BotCommand(command='/help', description='Помощь'),
            BotCommand(command='/ban', description='Забанить пользователя'),
            BotCommand(command='/unban', description='Разбанить пользователя'),
            BotCommand(command='/statistics', description='Статистика'),
        ]