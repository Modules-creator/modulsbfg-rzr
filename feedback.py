from aiogram import Dispatcher, types
from assets.antispam import antispam, admin_only
from config import admin  # Импортируем ID администратора из config.py

# Словарь для хранения состояний пользователей
user_states = {}

@antispam
async def feedback_start(message: types.Message):
    """
    Начало процесса отправки обратной связи
    """
    # Проверяем, что это личное сообщение
    if message.chat.type != 'private':
        return
        
    await message.answer("📝 Напишите ваше сообщение для администратора (предложения, ошибки и т.д.).\n\n"
                       "Чтобы отменить отправку, напишите /cancel")
    
    # Устанавливаем состояние ожидания feedback
    user_states[message.from_user.id] = 'waiting_feedback'

@antispam
async def feedback_process(message: types.Message):
    """
    Обработка текста обратной связи от пользователя
    """
    # Проверяем, что это личное сообщение
    if message.chat.type != 'private':
        return
        
    user_id = message.from_user.id
    
    # Проверяем, ожидает ли пользователь отправки feedback
    if user_id not in user_states or user_states[user_id] != 'waiting_feedback':
        return
    
    if message.text and message.text.lower() == '/cancel':
        await message.answer("❌ Отправка отменена")
        user_states.pop(user_id, None)
        return
    
    # Формируем сообщение для администратора
    username = message.from_user.username if message.from_user.username else "нет username"
    user_info = f"👤 Пользователь: @{username} (ID: {user_id})"
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

@admin_only()
async def admin_reply(message: types.Message):
    """
    Ответ администратора на обратную связь
    Формат: /reply <user_id> <текст ответа>
    """
    if not message.reply_to_message:
        await message.answer("ℹ️ Используйте команду в ответ на сообщение пользователя")
        return
    
    try:
        # Получаем текст оригинального сообщения
        original_text = message.reply_to_message.text
        
        # Ищем ID пользователя в сообщении
        if "ID:" not in original_text:
            await message.answer("❌ Не удалось найти ID пользователя в сообщении")
            return
            
        user_id = int(original_text.split("ID:")[1].split(")")[0].strip())
        
        # Получаем текст ответа (без команды)
        if len(message.text.split()) < 2:
            await message.answer("ℹ️ Формат: /reply <текст ответа>")
            return
            
        reply_text = message.text.split(' ', 1)[1]
        
        # Отправляем ответ пользователю
        await message.bot.send_message(user_id, f"📩 Ответ от администратора:\n\n{reply_text}")
        await message.answer(f"✅ Ответ отправлен пользователю (ID: {user_id})")
    except Exception as e:
        await message.answer(f"⚠️ Ошибка: {str(e)}")

def register_handlers(dp: Dispatcher):
    """
    Регистрация хэндлеров модуля
    """
    dp.register_message_handler(feedback_start, commands=['feedback'])
    dp.register_message_handler(feedback_process, content_types=types.ContentTypes.ANY)
    dp.register_message_handler(admin_reply, commands=['reply'], is_reply=True)

MODULE_DESCRIPTION = {
    'name': '📨 Обратная связь',
    'description': 'Модуль для отправки сообщений администратору и получения ответов. Работает только в ЛС.'
}
