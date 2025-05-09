from aiogram import Dispatcher, types
from assets.antispam import antispam, admin_only
from commands.db import conn as conngdb, cursor as cursorgdb
from config import admin  # Импортируем ID администратора из config.py

# Словарь для хранения состояний пользователей
user_states = {}

@antispam
@admin_only(private=True)  # Ограничиваем только для личных сообщений
async def feedback_start(message: types.Message):
    """
    Начало процесса отправки обратной связи
    """
    await message.answer("📝 Напишите ваше сообщение для администратора (предложения, ошибки и т.д.).\n\n"
                       "Чтобы отменить отправку, напишите /cancel")
    
    # Устанавливаем состояние ожидания feedback
    user_states[message.from_user.id] = 'waiting_feedback'

@antispam
@admin_only(private=True)
async def feedback_process(message: types.Message):
    """
    Обработка текста обратной связи от пользователя
    """
    user_id = message.from_user.id
    
    # Проверяем, ожидает ли пользователь отправки feedback
    if user_id not in user_states or user_states[user_id] != 'waiting_feedback':
        return
    
    if message.text.lower() == '/cancel':
        await message.answer("❌ Отправка отменена")
        user_states.pop(user_id, None)
        return
    
    # Формируем сообщение для администратора
    user_info = f"👤 Пользователь: @{message.from_user.username} (ID: {user_id})"
    feedback_text = f"📨 Новое сообщение от пользователя:\n\n{user_info}\n\n{message.text}"
    
    try:
        # Отправляем администратору
        await message.bot.send_message(admin, feedback_text)
        await message.answer("✅ Ваше сообщение отправлено администратору. Спасибо за обратную связь!")
    except Exception as e:
        await message.answer("⚠️ Произошла ошибка при отправке сообщения. Попробуйте позже.")
        print(f"Feedback error: {e}")
    
    # Сбрасываем состояние пользователя
    user_states.pop(user_id, None)

@admin_only()  # Только для администратора
async def admin_reply(message: types.Message):
    """
    Ответ администратора на обратную связь
    Формат: /reply <user_id> <текст ответа>
    """
    if not message.reply_to_message:
        await message.answer("ℹ️ Используйте команду в ответ на сообщение пользователя")
        return
    
    try:
        # Парсим текст сообщения пользователя
        original_text = message.reply_to_message.text
        user_id = int(original_text.split("ID: ")[1].split(")")[0])
        
        # Отправляем ответ пользователю
        reply_text = f"📩 Ответ от администратора:\n\n{message.text.split(' ', 1)[1]}"
        await message.bot.send_message(user_id, reply_text)
        await message.answer("✅ Ответ отправлен пользователю")
    except Exception as e:
        await message.answer(f"⚠️ Ошибка: {e}\n\nПроверьте формат сообщения")

def register_handlers(dp: Dispatcher):
    """
    Регистрация хэндлеров модуля
    """
    dp.register_message_handler(feedback_start, commands=['feedback'])
    dp.register_message_handler(feedback_process, content_types=types.ContentTypes.TEXT)
    dp.register_message_handler(admin_reply, commands=['reply'])

MODULE_DESCRIPTION = {
    'name': '📨 Обратная связь',
    'description': 'Модуль для отправки сообщений администратору и получения ответов. Работает только в ЛС.'
}
