from aiogram import Dispatcher, types
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from assets.antispam import antispam, admin_only
from commands.db import conn as conngdb, cursor as cursorgdb

# Состояния FSM для обработки сообщений поддержки
class SupportStates(StatesGroup):
    waiting_for_message = State()
    waiting_for_reply = State()

##### ОСНОВНЫЕ ФУНКЦИИ #####

# Начало диалога с поддержкой
@antispam
async def smsadmin_start(message: types.Message):
    if message.chat.type != 'private':
        await message.answer("❌ Команда доступна только в личных сообщениях с ботом.")
        return
    
    await message.answer("✍️ Напишите ваше сообщение для администрации. Мы ответим в ближайшее время.")
    await SupportStates.waiting_for_message.set()

# Обработка сообщения пользователя
@antispam
async def process_user_message(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    username = message.from_user.username or "Без username"
    first_name = message.from_user.first_name or "Без имени"
    text = message.text

    # Сохраняем сообщение в базу данных
    cursorgdb.execute('''INSERT INTO support_messages 
                        (user_id, username, first_name, message_text, status) 
                        VALUES (?, ?, ?, ?, ?)''',
                     (user_id, username, first_name, text, 'new'))
    conngdb.commit()

    # Отправляем уведомление админам
    admin_msg = (f"🆘 Новое сообщение в поддержку\n"
                f"👤 @{username} | {first_name}\n"
                f"🆔 ID: {user_id}\n"
                f"📝 Текст: {text}\n\n"
                f"Ответить: /reply@{username}")

    from main import bot  # Импортируем бота для отправки сообщений
    admins = get_admins()  # Получаем список админов
    
    for admin in admins:
        try:
            await bot.send_message(admin, admin_msg)
        except:
            continue

    await message.answer("✅ Ваше сообщение отправлено администрации. Ожидайте ответа.")
    await state.finish()

# Команда для ответа админа
@admin_only()
async def reply_start(message: types.Message):
    args = message.get_args()
    if not args:
        await message.answer("❌ Используйте: /reply@username сообщение")
        return
    
    username = args.split()[0].replace('@', '')
    await message.answer(f"✍️ Введите ответ для @{username}:")
    await state.update_data(target_username=username)
    await SupportStates.waiting_for_reply.set()

# Обработка ответа админа
@admin_only()
async def process_admin_reply(message: types.Message, state: FSMContext):
    data = await state.get_data()
    username = data.get('target_username')
    reply_text = message.text

    # Получаем ID пользователя по username
    user_id = cursorgdb.execute('SELECT user_id FROM users WHERE username = ?', (username,)).fetchone()
    
    if not user_id:
        await message.answer("❌ Пользователь не найден!")
        await state.finish()
        return

    user_id = user_id[0]

    # Отправляем ответ пользователю
    from main import bot
    try:
        await bot.send_message(user_id, f"📨 Ответ от поддержки:\n{reply_text}")
        await message.answer(f"✅ Ответ отправлен пользователю @{username}")
        
        # Обновляем статус в БД
        cursorgdb.execute('UPDATE support_messages SET status = ? WHERE user_id = ?', ('answered', user_id))
        conngdb.commit()
    except Exception as e:
        await message.answer(f"❌ Ошибка отправки: {e}")

    await state.finish()

##### ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ #####

def get_admins():
    """Получаем список ID администраторов"""
    cursorgdb.execute('SELECT user_id FROM admins')
    return [row[0] for row in cursorgdb.fetchall()]

##### РЕГИСТРАЦИЯ ХЕНДЛЕРОВ #####
def register_handlers(dp: Dispatcher):
    # Для пользователей
    dp.register_message_handler(smsadmin_start, commands=['smsadmin'])
    dp.register_message_handler(process_user_message, state=SupportStates.waiting_for_message)
    
    # Для админов
    dp.register_message_handler(reply_start, commands=['reply'])
    dp.register_message_handler(process_admin_reply, state=SupportStates.waiting_for_reply)

##### ОПИСАНИЕ МОДУЛЯ #####
MODULE_DESCRIPTION = {
    'name': '🆘 Система поддержки',
    'description': (
        'Позволяет пользователям писать в поддержку (/smsadmin)\n'
        'Админы могут отвечать через /reply@username'
    )
}
