import sqlite3
import logging
from aiogram import Bot, Dispatcher, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.utils import executor
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, InputMediaPhoto

# Настройка логирования
logging.basicConfig(level=logging.INFO)

# Токен бота
API_TOKEN = '7901399147:AAETUr5bZOtbBscoAsxeVvh5Z_9tMXZY3vE'
CHANNEL_ID = '@BelgorodSell411'  # Замените на имя вашего канала

# Инициализация бота и диспетчера
bot = Bot(token=API_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)

# Создание базы данных
conn = sqlite3.connect('users.db')
cursor = conn.cursor()
cursor.execute('''CREATE TABLE IF NOT EXISTS users
                 (user_id INTEGER PRIMARY KEY, username TEXT, first_name TEXT, 
                 last_name TEXT, is_banned INTEGER DEFAULT 0)''')
cursor.execute('''CREATE TABLE IF NOT EXISTS admins
                 (user_id INTEGER PRIMARY KEY)''')
conn.commit()

# Добавление администратора (замените на ваш ID)
ADMIN_ID = 1152451752 # Telegram
cursor.execute("INSERT OR IGNORE INTO admins (user_id) VALUES (?)", (ADMIN_ID,))
conn.commit()

# Состояния FSM
class PostStates(StatesGroup):
    waiting_for_text = State()
    waiting_for_photos = State()
    waiting_for_confirmation = State()

class AdminStates(StatesGroup):
    ban_user = State()
    unban_user = State()

# Проверка на администратора
def is_admin(user_id):
    cursor.execute("SELECT 1 FROM admins WHERE user_id=?", (user_id,))
    return cursor.fetchone() is not None

# Проверка на заблокированного пользователя
def is_banned(user_id):
    cursor.execute("SELECT is_banned FROM users WHERE user_id=?", (user_id,))
    result = cursor.fetchone()
    return result and result[0] == 1

# Добавление/обновление пользователя в БД
def update_user(user: types.User):
    cursor.execute("INSERT OR REPLACE INTO users (user_id, username, first_name, last_name) VALUES (?, ?, ?, ?)",
                   (user.id, user.username, user.first_name, user.last_name))
    conn.commit()

# Стартовое меню
@dp.message_handler(commands=['start'])
async def send_welcome(message: types.Message):
    update_user(message.from_user)
    
    if is_banned(message.from_user.id):
        await message.answer("🚫 Вы заблокированы и не можете использовать этого бота.")
        return
    
    keyboard = InlineKeyboardMarkup()
    if is_admin(message.from_user.id):
        keyboard.add(InlineKeyboardButton("🛠 Админ панель", callback_data="admin_panel"))
    keyboard.add(InlineKeyboardButton("📢 Создать пост", callback_data="create_post"))
    
    await message.answer("👋 Добро пожаловать в бота для публикации постов! ✨", reply_markup=keyboard)

# Обработка нажатий на кнопки
@dp.callback_query_handler(lambda c: c.data == 'admin_panel')
async def admin_panel(callback_query: types.CallbackQuery):
    if not is_admin(callback_query.from_user.id):
        await callback_query.answer("⛔ У вас нет прав администратора!")
        return
    
    keyboard = InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        InlineKeyboardButton("🔒 Заблокировать пользователя", callback_data="ban_user"),
        InlineKeyboardButton("🔓 Разблокировать пользователя", callback_data="unban_user"),
        InlineKeyboardButton("◀️ Назад", callback_data="back_to_main")
    )
    
    await bot.edit_message_text(chat_id=callback_query.message.chat.id,
                               message_id=callback_query.message.message_id,
                               text="🛠 Административная панель:",
                               reply_markup=keyboard)

@dp.callback_query_handler(lambda c: c.data == 'back_to_main')
async def back_to_main(callback_query: types.CallbackQuery):
    keyboard = InlineKeyboardMarkup()
    if is_admin(callback_query.from_user.id):
        keyboard.add(InlineKeyboardButton("🛠 Админ панель", callback_data="admin_panel"))
    keyboard.add(InlineKeyboardButton("📢 Создать пост", callback_data="create_post"))
    
    await bot.edit_message_text(chat_id=callback_query.message.chat.id,
                               message_id=callback_query.message.message_id,
                               text="👋 Добро пожаловать в бота для публикации постов! ✨",
                               reply_markup=keyboard)

# Создание поста
@dp.callback_query_handler(lambda c: c.data == 'create_post')
async def create_post(callback_query: types.CallbackQuery):
    if is_banned(callback_query.from_user.id):
        await callback_query.answer("🚫 Вы заблокированы и не можете создавать посты.")
        return
    
    await PostStates.waiting_for_text.set()
    await bot.edit_message_text(chat_id=callback_query.message.chat.id,
                               message_id=callback_query.message.message_id,
                               text="📝 Напишите текст для поста (можно с эмодзи 😊):")

@dp.message_handler(state=PostStates.waiting_for_text)
async def process_post_text(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data['text'] = message.text
    
    keyboard = InlineKeyboardMarkup()
    keyboard.add(InlineKeyboardButton("📷 Добавить фото", callback_data="add_photos"))
    keyboard.add(InlineKeyboardButton("🚀 Опубликовать без фото", callback_data="publish_no_photos"))
    keyboard.add(InlineKeyboardButton("❌ Отменить", callback_data="cancel_post"))
    
    await message.answer(f"📄 Текст поста:\n\n{message.text}\n\nЧто дальше? ✨", reply_markup=keyboard)
    await PostStates.next()

@dp.callback_query_handler(lambda c: c.data == 'add_photos', state=PostStates.waiting_for_photos)
async def add_photos(callback_query: types.CallbackQuery, state: FSMContext):
    await bot.edit_message_text(chat_id=callback_query.message.chat.id,
                               message_id=callback_query.message.message_id,
                               text="🖼 Пришлите фото для поста (можно несколько за раз). После отправки всех фото нажмите 'Готово' ✅")
    
    async with state.proxy() as data:
        data['photos'] = []

@dp.message_handler(content_types=types.ContentType.PHOTO, state=PostStates.waiting_for_photos)
async def process_photos(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        if 'photos' not in data:
            data['photos'] = []
        data['photos'].append(message.photo[-1].file_id)
    
    keyboard = InlineKeyboardMarkup()
    keyboard.add(InlineKeyboardButton("✅ Готово", callback_data="photos_done"))
    keyboard.add(InlineKeyboardButton("❌ Отменить", callback_data="cancel_post"))
    
    await message.answer(f"📸 Добавлено {len(data['photos'])} фото. Продолжайте отправлять или нажмите 'Готово' ✅", reply_markup=keyboard)

@dp.callback_query_handler(lambda c: c.data == 'photos_done', state=PostStates.waiting_for_photos)
async def photos_done(callback_query: types.CallbackQuery, state: FSMContext):
    async with state.proxy() as data:
        if 'photos' not in data or len(data['photos']) == 0:
            await bot.answer_callback_query(callback_query.id, "Вы не добавили ни одного фото! ❌")
            return
    
    await show_post_preview(callback_query, state)

@dp.callback_query_handler(lambda c: c.data == 'publish_no_photos', state=PostStates.waiting_for_photos)
async def publish_no_photos(callback_query: types.CallbackQuery, state: FSMContext):
    await show_post_preview(callback_query, state)

async def show_post_preview(callback_query: types.CallbackQuery, state: FSMContext):
    async with state.proxy() as data:
        text = data['text']
        photos = data.get('photos', [])
    
    preview_text = f"📋 Предварительный просмотр поста:\n\n{text}"
    
    if photos:
        preview_text += f"\n\n📸 Будет прикреплено {len(photos)} фото"
    
    keyboard = InlineKeyboardMarkup()
    keyboard.add(InlineKeyboardButton("🚀 Опубликовать", callback_data="confirm_post"))
    keyboard.add(InlineKeyboardButton("✏️ Редактировать", callback_data="edit_post"))
    keyboard.add(InlineKeyboardButton("❌ Отменить", callback_data="cancel_post"))
    
    await bot.edit_message_text(chat_id=callback_query.message.chat.id,
                               message_id=callback_query.message.message_id,
                               text=preview_text,
                               reply_markup=keyboard)
    await PostStates.next()

@dp.callback_query_handler(lambda c: c.data == 'confirm_post', state=PostStates.waiting_for_confirmation)
async def confirm_post(callback_query: types.CallbackQuery, state: FSMContext):
    async with state.proxy() as data:
        text = data['text']
        photos = data.get('photos', [])
    
    if photos:
        # Создаем медиагруппу
        media = [InputMediaPhoto(photos[0], caption=text)]
        for photo in photos[1:]:
            media.append(InputMediaPhoto(photo))
        
        await bot.send_media_group(CHANNEL_ID, media)
    else:
        await bot.send_message(CHANNEL_ID, text)
    
    await bot.edit_message_text(chat_id=callback_query.message.chat.id,
                               message_id=callback_query.message.message_id,
                               text="✅ Пост успешно опубликован в канале! 🎉")
    await state.finish()

@dp.callback_query_handler(lambda c: c.data == 'edit_post', state=PostStates.waiting_for_confirmation)
async def edit_post(callback_query: types.CallbackQuery, state: FSMContext):
    await PostStates.waiting_for_text.set()
    await bot.edit_message_text(chat_id=callback_query.message.chat.id,
                               message_id=callback_query.message.message_id,
                               text="📝 Отредактируйте текст поста:")

@dp.callback_query_handler(lambda c: c.data == 'cancel_post', state='*')
async def cancel_post(callback_query: types.CallbackQuery, state: FSMContext):
    await state.finish()
    await bot.edit_message_text(chat_id=callback_query.message.chat.id,
                               message_id=callback_query.message.message_id,
                               text="❌ Создание поста отменено.")

# Административные функции
@dp.callback_query_handler(lambda c: c.data == 'ban_user')
async def ban_user_start(callback_query: types.CallbackQuery):
    if not is_admin(callback_query.from_user.id):
        await callback_query.answer("⛔ У вас нет прав администратора!")
        return
    
    await AdminStates.ban_user.set()
    await bot.edit_message_text(chat_id=callback_query.message.chat.id,
                               message_id=callback_query.message.message_id,
                               text="🔒 Введите ID пользователя для блокировки:")

@dp.message_handler(state=AdminStates.ban_user)
async def ban_user_process(message: types.Message, state: FSMContext):
    try:
        user_id = int(message.text)
    except ValueError:
        await message.answer("❌ Неверный формат ID. Пожалуйста, введите числовой ID.")
        return
    
    cursor.execute("UPDATE users SET is_banned=1 WHERE user_id=?", (user_id,))
    conn.commit()
    
    if cursor.rowcount > 0:
        await message.answer(f"✅ Пользователь {user_id} успешно заблокирован. 🚫")
    else:
        await message.answer(f"⚠️ Пользователь {user_id} не найден в базе данных.")
    
    await state.finish()

@dp.callback_query_handler(lambda c: c.data == 'unban_user')
async def unban_user_start(callback_query: types.CallbackQuery):
    if not is_admin(callback_query.from_user.id):
        await callback_query.answer("⛔ У вас нет прав администратора!")
        return
    
    await AdminStates.unban_user.set()
    await bot.edit_message_text(chat_id=callback_query.message.chat.id,
                               message_id=callback_query.message.message_id,
                               text="🔓 Введите ID пользователя для разблокировки:")

@dp.message_handler(state=AdminStates.unban_user)
async def unban_user_process(message: types.Message, state: FSMContext):
    try:
        user_id = int(message.text)
    except ValueError:
        await message.answer("❌ Неверный формат ID. Пожалуйста, введите числовой ID.")
        return
    
    cursor.execute("UPDATE users SET is_banned=0 WHERE user_id=?", (user_id,))
    conn.commit()
    
    if cursor.rowcount > 0:
        await message.answer(f"✅ Пользователь {user_id} успешно разблокирован. 🎉")
    else:
        await message.answer(f"⚠️ Пользователь {user_id} не найден в базе данных или не был заблокирован.")
    
    await state.finish()

# Запуск бота
if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
