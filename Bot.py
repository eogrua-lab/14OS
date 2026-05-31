import asyncio
import os
import random
from datetime import datetime
from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, FSInputFile
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage

# --- НАСТРОЙКИ ---
TOKEN = os.getenv('TOKEN', 'ТВОЙ_ТОКЕН_ЗДЕСЬ')
ADMIN_ID = int(os.getenv('ADMIN_ID', 123456789))
LANG = "ru"
BANNED_FILE = "banned_users.txt"

def get_banned_users():
    if not os.path.exists(BANNED_FILE):
        return set()
    with open(BANNED_FILE, "r") as f:
        return set(int(line.strip()) for line in f)

BANNED_USERS = get_banned_users()

bot = Bot(token=TOKEN)
dp = Dispatcher(storage=MemoryStorage())

# --- СОСТОЯНИЯ ---
class Feedback(StatesGroup):
    category = State()
    level = State()
    waiting_for_media = State()

class AdminReply(StatesGroup):
    waiting_for_admin_text = State()
    target_user_id = State()

# --- ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ---
def log_message(user_id, category, message_text):
    date_str = datetime.now().strftime("%Y-%m-%d")
    time_str = datetime.now().strftime("%H:%M:%S")
    log_file = f"logs_{date_str}.txt"
    log_entry = f"({user_id}) {time_str} - {category} - {message_text}\n"
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(log_entry)

# --- КЛАВИАТУРЫ ---
def main_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🐞 Нашел баг", callback_data="cat_bug")],
        [InlineKeyboardButton(text="🔥 Выразить респект", callback_data="cat_praise")],
        [InlineKeyboardButton(text="🤝 Познакомиться", callback_data="cat_meet")]
    ])

def bug_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❗️ Критически", callback_data="bug_crit")],
        [InlineKeyboardButton(text="⚠️ Немного мешает", callback_data="bug_minor")]
    ])

def admin_reply_kb(user_id):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Автоответ", callback_data=f"rep_auto_{user_id}")],
        [InlineKeyboardButton(text="💬 Ответить", callback_data=f"rep_personal_{user_id}")],
        [InlineKeyboardButton(text="🚫 БАН", callback_data=f"ban_{user_id}")]
    ])

# --- ЛОГИКА ---
@dp.message(Command("start"))
async def start(message: types.Message):
    if message.from_user.id in BANNED_USERS: return
    await message.answer("Привет! Ты нашел секретный канал связи 14ОС. Выбирай:", reply_markup=main_kb())

@dp.message(Command("getlogs"))
async def get_logs_file(message: types.Message):
    if message.from_user.id != ADMIN_ID: return
    date_str = datetime.now().strftime("%Y-%m-%d")
    log_file = f"logs_{date_str}.txt"
    if os.path.exists(log_file):
        await message.answer_document(FSInputFile(log_file))
    else:
        await message.answer("⚠️ Файл логов за сегодня пуст.")

@dp.callback_query(F.data.startswith("cat_"))
async def handle_category(callback: types.CallbackQuery, state: FSMContext):
    cat = callback.data.split("_")[1]
    await state.update_data(category=cat)
    if cat == "bug":
        await callback.message.answer("Ого, ошибка? Насколько она серьезна?", reply_markup=bug_kb())
    else:
        await state.set_state(Feedback.waiting_for_media)
        await callback.message.answer("Принято. Присылай текст, фото или видео:")
    await callback.answer()

@dp.callback_query(F.data.startswith("bug_"))
async def handle_bug_level(callback: types.CallbackQuery, state: FSMContext):
    level = "КРИТИЧЕСКИ ❗️" if callback.data == "bug_crit" else "МЕЛКИЙ БАГ ⚠️"
    await state.update_data(level=level)
    await state.set_state(Feedback.waiting_for_media)
    await callback.message.answer("Принято. Присылай текст, фото или видео:")
    await callback.answer()

@dp.message(Feedback.waiting_for_media)
async def final_message(message: types.Message, state: FSMContext):
    data = await state.get_data()
    cat = data.get('category', 'DEFAULT').upper()
    lvl = f" | {data.get('level')}" if data.get('level') else ""
    
    txt = message.text if message.text else ("[ФОТО/ВИДЕО]" if not message.caption else f"[МЕДИА] {message.caption}")
    log_message(message.from_user.id, f"{cat}{lvl}", txt)
    
    header = f"✉️ {cat}{lvl}\n👤 Юзер: @{message.from_user.username or 'NoName'}\n🆔 ID: `{message.from_user.id}`"
    await bot.send_message(ADMIN_ID, f"{header}\n\n💬 Сообщение:", reply_markup=admin_reply_kb(message.from_user.id))
    await bot.copy_message(ADMIN_ID, message.chat.id, message.message_id)
    await message.answer("✅ ОТПРАВЛЕНО!")
    await state.clear()

@dp.callback_query(F.data.startswith("rep_"))
async def handle_admin_reply(callback: types.CallbackQuery, state: FSMContext):
    action, user_id = callback.data.split("_")[1], callback.data.split("_")[2]
    if action == "auto":
        replies = ["Ваше обращение принято!", "Мы изучаем проблему.", "Спасибо, помогаете 14 OS лучше!"]
        await bot.send_message(user_id, random.choice(replies))
        await callback.message.edit_text(callback.message.text + "\n\n✅ Отправлен автоответ.")
    elif action == "personal":
        await state.update_data(target_user_id=user_id)
        await state.set_state(AdminReply.waiting_for_admin_text)
        await callback.message.answer(f"Пиши ответ для юзера {user_id}:")
    await callback.answer()

@dp.message(AdminReply.waiting_for_admin_text)
async def send_admin_reply(message: types.Message, state: FSMContext):
    data = await state.get_data()
    await bot.send_message(data["target_user_id"], f"Ответ от разработчика:\n\n{message.text}")
    await message.answer("✅ Отправлено.")
    await state.clear()

@dp.callback_query(F.data.startswith("ban_"))
async def ban_user(callback: types.CallbackQuery):
    user_id = callback.data.split("_")[1]
    BANNED_USERS.add(int(user_id))
    with open(BANNED_FILE, "a") as f: f.write(f"{user_id}\n")
    await callback.message.edit_text(callback.message.text + f"\n\n🚫 ЮЗЕР {user_id} В БАНЕ.")
    await callback.answer("Забанено")

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
