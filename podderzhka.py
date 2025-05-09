from aiogram import Dispatcher, types
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
import sqlite3
import logging
from config import admin, API_TOKEN

# Подключение к базе данных
connection = sqlite3.connect('data.db')
cursor = connection.cursor()

class SMSAStates(StatesGroup):
    waiting_for_message = State()

async def smsa_command(message: types.Message):
    """Обработчик команды /smsa"""
    cursor.execute(f"SELECT block FROM users WHERE user_id = {message.chat.id}")
    result = cursor.fetchone()
    
    if result and result[0] == 1:
        await message.answer("Вы заблокированы в боте.")
        return
    
    await message.answer(
        "📨 Отправьте сообщение для анонимной рассылки администратору.\n"
        "Сообщение будет переслано без указания вашего имени."
    )
    await SMSAStates.waiting_for_message.set()

async def process_smsa_message(message: types.Message, state: FSMContext):
    """Обработка сообщения для команды /smsa"""
    # Проверяем, что сообщение не команда
    if message.text.startswith('/'):
        await message.answer("Пожалуйста, отправьте текстовое сообщение.")
        return
    
    # Отправляем сообщение администратору
    try:
        await message.bot.send_message(
            admin,
            f"📨 <b>Анонимное сообщение:</b>\n{message.text}",
            parse_mode='HTML'
        )
        await message.answer("✅ Ваше сообщение отправлено администратору.")
    except Exception as e:
        await message.answer("❌ Произошла ошибка при отправке сообщения.")
        logging.error(f"SMSA error: {e}")
    
    await state.finish()

def register_handlers(dp: Dispatcher):
    """Регистрация хэндлеров"""
    dp.register_message_handler(smsa_command, commands=['smsa'])
    dp.register_message_handler(process_smsa_message, state=SMSAStates.waiting_for_message, content_types=['text'])

MODULE_DESCRIPTION = {
    'name': '📨 Анонимные сообщения',
    'description': 'Модуль для отправки анонимных сообщений администратору через команду /smsa'
}
