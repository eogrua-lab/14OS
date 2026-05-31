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
from aiogram.fsm.storage.base import StorageKey

# --- НАСТРОЙКИ ---
# Читаем строго из переменных окружения
TOKEN = os.getenv('TOKEN')
ADMIN_ID = int(os.getenv('ADMIN_ID', 6324212559))
BANNED_FILE = "banned_users.txt"

def get_banned_users():
    if not os.path.exists(BANNED_FILE): return set()
    with open(BANNED_FILE, "r") as f: return set(int(line.strip()) for line in f)

BANNED_USERS = get_banned_users()

bot = Bot(token=TOKEN)
dp = Dispatcher(storage=MemoryStorage())

# --- ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ---
def log_message(user_id, category, message_text):
    date_str = datetime.now().strftime("%Y-%m-%d")
    log_file = f"logs_{date_str}.txt"
    with open(log_file, "a", encoding="utf-8") as f: 
        f.write(f"({user_id}) {datetime.now().strftime('%H:%M:%S')} - {category} - {message_text}\n")

def storage_key(user_id: int) -> StorageKey:
    return StorageKey(bot_id=bot.id, user_id=user_id, chat_id=user_id)

# --- СОСТОЯНИЯ ---
class Feedback(StatesGroup):
    category = State()
    level = State()
    waiting_for_media = State()

class AdminReply(StatesGroup):
    waiting_for_admin_text = State()
    target_user_id = State()

# --- КЛАВИАТУРЫ ---
def admin_reply_kb(user_id):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Автоответ", callback_data=f"rep_auto_{user_id}")],
        [InlineKeyboardButton(text="💬 Ответить", callback_data=f"rep_personal_{user_id}")],
        [InlineKeyboardButton(text="🚫 БАН", callback_data=f"ban_{user_id}")]
    ])

# --- КОМАНДЫ И ОБРАБОТЧИКИ ---
@dp.message(Command("start"))
async def start(message: types.Message):
    if message.from_user.id in BANNED_USERS: return
    await message.answer("Привет! 14ОС на связи. Команды: /bug, /respect, /meet")

@dp.message(Command("bug"))
async def cmd_bug(message: types.Message, state: FSMContext):
    await state.update_data(category="bug")
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="❗️ Критически", callback_data="bug_crit"), InlineKeyboardButton(text="⚠️ Мелкий", callback_data="bug_minor")]])
    await message.answer("Какая серьезность бага?", reply_markup=kb)

@dp.message(Command("respect"))
async def cmd_respect(message: types.Message, state: FSMContext):
    await state.update_data(category="praise")
    await state.set_state(Feedback.waiting_for_media)
    await message.answer("Принято, респект! Присылай текст/медиа:")

@dp.message(Command("meet"))
async def cmd_meet(message: types.Message, state: FSMContext):
    await state.update_data(category="meet")
    await state.set_state(Feedback.waiting_for_media)
    await message.answer("Рад знакомству! Расскажи о себе:")

@dp.message(Command("helpad"))
async def admin_help(message: types.Message):
    if message.from_user.id != ADMIN_ID: return
    await message.answer("/getlogs, /unban [ID], /reset [ID], /stop")

@dp.message(Command("getlogs"))
async def get_logs(message: types.Message):
    if message.from_user.id != ADMIN_ID: return
    log_file = f"logs_{datetime.now().strftime('%Y-%m-%d')}.txt"
    if os.path.exists(log_file): await message.answer_document(FSInputFile(log_file))
    else: await message.answer("Логи пусты.")

@dp.message(Command("unban"))
async def unban_user(message: types.Message):
    if message.from_user.id != ADMIN_ID: return
    args = message.text.split()
    if len(args) < 2: return
    uid = int(args[1])
    if uid in BANNED_USERS:
        BANNED_USERS.remove(uid)
        with open(BANNED_FILE, "w") as f: f.write("\n".join(map(str, BANNED_USERS)))
        await message.answer("Разбанен.")

@dp.message(Command("reset"))
async def reset_state(message: types.Message):
    if message.from_user.id != ADMIN_ID: return
    args = message.text.split()
    if len(args) < 2: return
    uid = int(args[1])
    await dp.fsm.storage.set_state(key=storage_key(uid), state=None)
    await message.answer(f"Состояние {uid} сброшено.")

# --- ЛОГИКА ---
@dp.callback_query(F.data.startswith("bug_"))
async def handle_bug(callback: types.CallbackQuery, state: FSMContext):
    await state.update_data(level="КРИТИЧЕСКИ" if callback.data == "bug_crit" else "МЕЛКИЙ")
    await state.set_state(Feedback.waiting_for_media)
    await callback.message.answer("Принято. Присылай текст или медиа:")
    await callback.answer()

@dp.message(Feedback.waiting_for_media)
async def final_message(message: types.Message, state: FSMContext):
    data = await state.get_data()
    cat, lvl = data.get('category', 'DEFAULT').upper(), data.get('level', '')
    txt = message.text or (message.caption or "[МЕДИА]")
    log_message(message.from_user.id, f"{cat} | {lvl}", txt)
    
    await bot.send_message(ADMIN_ID, f"✉️ {cat} | {lvl}\nID: `{message.from_user.id}`\nСообщение:", reply_markup=admin_reply_kb(message.from_user.id))
    await bot.copy_message(ADMIN_ID, message.chat.id, message.message_id)
    await message.answer("✅ Отправлено!")
    await state.clear()

@dp.callback_query(F.data.startswith("rep_"))
async def handle_admin(callback: types.CallbackQuery, state: FSMContext):
    action, uid = callback.data.split("_")[1], callback.data.split("_")[2]
    if action == "auto":
        await bot.send_message(uid, "Ваше обращение принято!")
        await callback.message.edit_text(callback.message.text + "\n\n✅ Отправлен автоответ.")
    elif action == "personal":
        await state.update_data(target_user_id=uid)
        await state.set_state(AdminReply.waiting_for_admin_text)
        await callback.message.answer(f"Пиши ответ для {uid} (/stop для выхода):")
    await callback.answer()

@dp.message(AdminReply.waiting_for_admin_text)
async def admin_reply(message: types.Message, state: FSMContext):
    if message.text == "/stop":
        await state.clear()
        return await message.answer("🛑 Диалог окончен.")
    data = await state.get_data()
    await bot.send_message(data["target_user_id"], f"Ответ: {message.text}")
    await message.answer("✅ Отправлено.")

@dp.callback_query(F.data.startswith("ban_"))
async def ban(callback: types.CallbackQuery):
    uid = callback.data.split("_")[1]
    BANNED_USERS.add(int(uid))
    with open(BANNED_FILE, "a") as f: f.write(f"{uid}\n")
    await callback.message.edit_text(callback.message.text + f"\n\n🚫 {uid} В БАНЕ.")
    await callback.answer("Забанено")

async def main(): await dp.start_polling(bot)

if __name__ == "__main__": asyncio.run(main())
