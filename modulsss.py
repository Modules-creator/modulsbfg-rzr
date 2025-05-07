from aiogram import types
from aiogram.dispatcher import Dispatcher
from aiogram.utils.exceptions import ChatNotFound
import logging
from config import admin  # Импортируем список админов из конфига

async def broadcast_command(message: types.Message):
    """Обработчик команды /all для рассылки сообщений"""
    if message.chat.type != 'private':
        await message.reply("❌ Эта команда доступна только в личных сообщениях с ботом")
        return

    # Проверка прав администратора из config.py
    if message.from_user.id not in ADMINS:
        await message.reply("❌ У вас нет прав для использования этой команды")
        return

    args = message.get_args()
    if not args:
        await message.reply("ℹ️ Использование: /all <текст сообщения>")
        return

    # Получаем список всех чатов (вам нужно реализовать этот метод)
    chats = await get_all_chats()
    if not chats:
        await message.reply("⚠️ Бот не состоит ни в одном чате")
        return

    success = 0
    failed = 0
    total = len(chats)

    status_msg = await message.reply(f"🔄 Начинаю рассылку в {total} чатов...")

    for chat_id in chats:
        try:
            await message.bot.send_message(chat_id, args)
            success += 1
        except Exception as e:
            logging.error(f"Ошибка при отправке в чат {chat_id}: {e}")
            failed += 1
            continue

        # Обновляем статус каждые 10 сообщений
        if (success + failed) % 10 == 0:
            await status_msg.edit_text(
                f"🔄 Рассылка: {success + failed}/{total}\n"
                f"✅ Успешно: {success}\n"
                f"❌ Ошибок: {failed}"
            )

    await status_msg.edit_text(
        f"✅ Рассылка завершена!\n"
        f"Всего чатов: {total}\n"
        f"Успешно отправлено: {success}\n"
        f"Не удалось отправить: {failed}"
    )


async def get_all_chats() -> list:
    """Возвращает список всех чатов, где есть бот"""
    # Реализуйте получение списка чатов из вашей базы данных
    # Или используйте другой метод хранения информации о чатах
    # Пример: return await db.get_all_chats()
    return []  # Замените на реальное получение чатов


def register_broadcast_handlers(dp: Dispatcher):
    dp.register_message_handler(broadcast_command, commands=['all'], state="*")
