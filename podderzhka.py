from aiogram import Bot, Dispatcher, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
import sqlite3
import logging
from config import admin, API_TOKEN

# Инициализация бота и хранилища
storage = MemoryStorage()
bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot, storage=storage)
connection = sqlite3.connect('data.db')
q = connection.cursor()

# Класс для состояний FSM
class States(StatesGroup):
    item = State()  # Для рассылки
    item2 = State()  # Для ответа пользователю
    item3 = State()  # Для добавления в ЧС
    item4 = State()  # Для удаления из ЧС
    smsa_state = State()  # Для приватных сообщений администратору

# Инициализация клавиатур
def get_keyboards():
    menu = types.ReplyKeyboardMarkup(resize_keyboard=True)
    menu.add(types.KeyboardButton('👑 Админка'))

    adm = types.ReplyKeyboardMarkup(resize_keyboard=True)
    adm.add(
        types.KeyboardButton('👿 ЧС'),
        types.KeyboardButton('✅ Добавить в ЧС'),
        types.KeyboardButton('❎ Убрать из ЧС')
    )
    adm.add(types.KeyboardButton('💬 Рассылка'))
    adm.add(types.KeyboardButton('⏪ Назад'))

    back = types.ReplyKeyboardMarkup(resize_keyboard=True)
    back.add(types.KeyboardButton('⏪ Отмена'))

    return {'menu': menu, 'adm': adm, 'back': back}

kb = get_keyboards()

def get_inline_keyboard(user_id):
    quest = types.InlineKeyboardMarkup(row_width=3)
    quest.add(
        types.InlineKeyboardButton(text='💬 Ответить', callback_data=f'{user_id}-ans'),
        types.InlineKeyboardButton(text='❎ Удалить', callback_data='ignor')
    )
    return quest

# Функции для работы с БД
def join_user(chat_id):
    q.execute(f"SELECT * FROM users WHERE user_id = {chat_id}")
    result = q.fetchall()
    if len(result) == 0:
        q.execute(f'INSERT INTO users (user_id, block) VALUES ({chat_id}, 0)')
        connection.commit()

async def antiflood(*args, **kwargs):
    m = args[0]
    if m.chat.id != admin:
        await m.answer("Сработал антифлуд! Прекрати флудить и жди 3 секунды. Наш канал - @slivmenss")

# Хэндлер для команды /smsa
@dp.message_handler(commands=['smsa'])
async def smsa_command(message: types.Message):
    join_user(message.chat.id)
    q.execute(f"SELECT block FROM users WHERE user_id = {message.chat.id}")
    result = q.fetchone()
    
    if result[0] == 0:
        await message.answer("Введите сообщение, которое будет доступно только администратору:", reply_markup=kb['back'])
        await States.smsa_state.set()

# Обработчик сообщений для /smsa
@dp.message_handler(state=States.smsa_state)
async def process_smsa(message: types.Message, state: FSMContext):
    if message.text == '⏪ Отмена':
        await message.answer("Отправка отменена.", reply_markup=kb['menu'])
        await state.finish()
    else:
        await bot.send_message(
            admin,
            f"🔒 Приватное сообщение от пользователя {message.from_user.mention} (ID: {message.chat.id}):\n\n{message.text}",
            reply_markup=get_inline_keyboard(message.chat.id)
        )
        await message.answer("Ваше сообщение было отправлено администратору.", reply_markup=kb['menu'])
        await state.finish()

# Регистрация остальных хэндлеров (из вашего исходного кода)
@dp.message_handler(content_types=['text'], text='👑 Админка')
async def admin_panel(message: types.Message, state: FSMContext):
    # ... (ваш существующий код)

@dp.message_handler(content_types=['text'], text='⏪ Назад')
async def back_handler(message: types.Message, state: FSMContext):
    # ... (ваш существующий код)

# ... (остальные хэндлеры из вашего исходного кода)

def register_handlers(dp: Dispatcher):
    dp.register_message_handler(smsa_command, commands=['smsa'])
    # Регистрация остальных хэндлеров
    dp.register_message_handler(admin_panel, content_types=['text'], text='👑 Админка')
    dp.register_message_handler(back_handler, content_types=['text'], text='⏪ Назад')
    # ... (регистрация других хэндлеров)

MODULE_DESCRIPTION = {
    'name': '🔒 Приватные сообщения',
    'description': 'Модуль для отправки приватных сообщений администратору через команду /smsa'
}

if __name__ == '__main__':
    register_handlers(dp)
    executor.start_polling(dp, skip_updates=True)
