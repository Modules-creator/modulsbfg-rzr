from aiogram import types, Dispatcher
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from assets.antispam import antispam, admin_only
from commands.db import conn as conngdb, cursor as cursorgdb


# Создаём таблицу при первом запуске
cursorgdb.execute('''CREATE TABLE IF NOT EXISTS nick_warn (
                    user_id INTEGER PRIMARY KEY,
                    nickname TEXT,
                    warns INTEGER DEFAULT 0)''')
conngdb.commit()


class NickWarnStates(StatesGroup):
    waiting_for_nickname = State()


@admin_only()
@antispam
async def set_nick_start(message: types.Message):
    if not message.reply_to_message:
        await message.answer("ℹ Используйте команду через reply на сообщение пользователя.")
        return

    target_user = message.reply_to_message.from_user
    await message.answer(f"✏ Введите новый никнейм для пользователя (ID: {target_user.id}):")
    await NickWarnStates.waiting_for_nickname.set()
    
    async with state.proxy() as data:
        data['target_id'] = target_user.id
        data['chat_id'] = message.chat.id


@antispam
async def set_nick_finish(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        target_id = data['target_id']
        chat_id = data['chat_id']
    
    nickname = message.text.strip()
    
    if len(nickname) > 20:
        await message.answer("❌ Никнейм не может быть длиннее 20 символов.")
        await state.finish()
        return
    
    # Проверяем, есть ли уже запись о пользователе
    cursorgdb.execute('SELECT 1 FROM nick_warn WHERE user_id = ?', (target_id,))
    exists = cursorgdb.fetchone()
    
    if exists:
        cursorgdb.execute('UPDATE nick_warn SET nickname = ? WHERE user_id = ?', (nickname, target_id))
    else:
        cursorgdb.execute('INSERT INTO nick_warn (user_id, nickname) VALUES (?, ?)', (target_id, nickname))
    
    conngdb.commit()
    await message.answer(f"✅ Никнейм успешно установлен: {nickname}")
    await state.finish()


@antispam
async def nick_list(message: types.Message):
    cursorgdb.execute('SELECT user_id, nickname, warns FROM nick_warn ORDER BY nickname')
    users = cursorgdb.fetchall()
    
    if not users:
        await message.answer("ℹ В этом чате никнеймы еще не установлены.")
        return
    
    response = "📜 Список пользователей с никнеймами:\n\n"
    for user in users:
        user_id, nickname, warns = user
        response += f"👤 {nickname} (ID: {user_id}) - ⚠️ Варны: {warns}/3\n"
    
    await message.answer(response)


@admin_only()
@antispam
async def warn_user(message: types.Message):
    if not message.reply_to_message:
        await message.answer("ℹ Используйте команду через reply на сообщение пользователя.")
        return

    target_user = message.reply_to_message.from_user
    target_id = target_user.id
    
    # Получаем текущее количество варнов
    cursorgdb.execute('SELECT warns FROM nick_warn WHERE user_id = ?', (target_id,))
    result = cursorgdb.fetchone()
    
    if result:
        current_warns = result[0]
    else:
        # Создаём запись, если пользователя нет в базе
        current_warns = 0
        cursorgdb.execute('INSERT INTO nick_warn (user_id, nickname, warns) VALUES (?, ?, ?)',
                         (target_id, f"@{target_user.username}" if target_user.username else f"ID:{target_id}", 0))
    
    new_warns = current_warns + 1
    
    cursorgdb.execute('UPDATE nick_warn SET warns = ? WHERE user_id = ?', (new_warns, target_id))
    conngdb.commit()
    
    if new_warns >= 3:
        try:
            await message.bot.kick_chat_member(chat_id=message.chat.id, user_id=target_id, until_date=60)
            await message.answer(f"🚫 Пользователь {target_user.full_name} был кикнут за 3 варна.")
        except Exception as e:
            await message.answer(f"❌ Не удалось кикнуть пользователя: {e}")
    else:
        await message.answer(f"⚠️ Пользователю {target_user.full_name} выдан варн. Текущее количество: {new_warns}/3")


@antispam
async def user_profile(message: types.Message):
    if not message.reply_to_message:
        await message.answer("ℹ Используйте команду через reply на сообщение пользователя.")
        return

    target_user = message.reply_to_message.from_user
    target_id = target_user.id
    
    cursorgdb.execute('SELECT nickname, warns FROM nick_warn WHERE user_id = ?', (target_id,))
    result = cursorgdb.fetchone()
    
    if not result:
        await message.answer(f"ℹ Пользователь {target_user.full_name} не имеет установленного никнейма.")
        return
    
    nickname, warns = result
    response = (f"📋 Профиль пользователя:\n\n"
               f"👤 Имя: {target_user.full_name}\n"
               f"🆔 ID: {target_id}\n"
               f"🏷️ Никнейм: {nickname}\n"
               f"⚠️ Варны: {warns}/3")
    
    await message.answer(response)


def register_handlers(dp: Dispatcher):
    dp.register_message_handler(set_nick_start, commands=['setnick'])
    dp.register_message_handler(set_nick_finish, state=NickWarnStates.waiting_for_nickname)
    dp.register_message_handler(nick_list, commands=['nlist'])
    dp.register_message_handler(warn_user, commands=['warn'])
    dp.register_message_handler(user_profile, commands=['profile'])


MODULE_DESCRIPTION = {
    'name': '🛡️ Модерация чата',
    'description': 'Модуль для управления никнеймами и варнами пользователей\n'
                  '/setnick - установить никнейм (через reply)\n'
                  '/nlist - список пользователей с никнеймами\n'
                  '/warn - выдать варн (через reply)\n'
                  '/profile - просмотр профиля (через reply)'
}
