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

TEXTS = {
    "ru": {
        "start": "Привет! Ты нашел секретный канал связи 14ОС. Выбирай:",
        "cat_bug": "🐞 Нашел баг",
        "cat_praise": "🔥 Выразить респект",
        "cat_meet": "🤝 Познакомиться",
        "bug_crit": "❗️ Критически",
        "bug_minor": "⚠️ Немного мешает",
        "prompt_bug": "Ого, ошибка? Насколько она серьезна?",
        "prompt_text": "Принято. Присылай текст, фото или видео:",
        "success": "✅ ОТПРАВЛЕНО!"
    }
}

AUTO_REPLIES = [
    "Ваше обращение принято и находится на рассмотрении. Спасибо за участие!",
    "Мы получили ваш тикет. Разработчик уже изучает проблему, ожидайте обновлений.",
    "Спасибо, что помогаете делать 14 OS лучше! Обращение принято в работу."
]

bot = Bot(token=TOKEN)
dp = Dispatcher(storage=MemoryStorage())

class Feedback(StatesGroup):
    category = State()
    level = State()
    waiting_for_media = State()

# --- ЛОГИРОВАНИЕ ---
def log_message(user_id, category, message_text):
    date_str = datetime.now().strftime("%Y-%m-%d")
    time_str = datetime.now().strftime("%H:%M:%S")
    log_file = f"logs_{date_str}.txt"
    log_entry = f"({user_id}) {time_str} - {category} - {message_text}\n"
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(log_entry)

# --- КЛАВИАТУРЫ ---
def main_kb():
    t = TEXTS[LANG]
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=t["cat_bug"], callback_data="cat_bug")],
        [InlineKeyboardButton(text=t["cat_praise"], callback_data="cat_praise")],
        [InlineKeyboardButton(text=t["cat_meet"], callback_data="cat_meet")]
    ])

def bug_kb():
    t = TEXTS[LANG]
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=t["bug_crit"], callback_data="bug_crit")],
        [InlineKeyboardButton(text=t["bug_minor"], callback_data="bug_minor")]
    ])

def admin_reply_kb(user_id):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Ответ шаблоном", callback_data=f"rep_auto_{user_id}")],
        [InlineKeyboardButton(text="💬 Написать лично", callback_data=f"rep_personal_{user_id}")]
    ])

# --- ЛОГИКА ---
@dp.message(Command("start"))
async def start(message: types.Message):
    await message.answer(TEXTS[LANG]["start"], reply_markup=main_kb())

# Команда для получения логов админом
@dp.message(Command("getlogs"))
async def get_logs_file(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        return
    date_str = datetime.now().strftime("%Y-%m-%d")
    log_file = f"logs_{date_str}.txt"
    if os.path.exists(log_file):
        await message.answer_document(FSInputFile(log_file))
    else:
        await message.answer("⚠️ Файл логов за сегодня еще не создан.")

@dp.callback_query(F.data.startswith("cat_"))
async def handle_category(callback: types.CallbackQuery, state: FSMContext):
    cat = callback.data.split("_")[1]
    await state.update_data(category=cat)
    if cat == "bug":
        await callback.message.answer(TEXTS[LANG]["prompt_bug"], reply_markup=bug_kb())
    else:
        await state.set_state(Feedback.waiting_for_media)
        await callback.message.answer(TEXTS[LANG]["prompt_text"])
    await callback.answer()

@dp.callback_query(F.data.startswith("bug_"))
async def handle_bug_level(callback: types.CallbackQuery, state: FSMContext):
    level = "КРИТИЧЕСКИ ❗️" if callback.data == "bug_crit" else "МЕЛКИЙ БАГ ⚠️"
    await state.update_data(level=level)
    await state.set_state(Feedback.waiting_for_media)
    await callback.message.answer(TEXTS[LANG]["prompt_text"])
    await callback.answer()

@dp.message(Feedback.waiting_for_media)
async def final_message(message: types.Message, state: FSMContext):
    data = await state.get_data()
    cat = data.get('category', 'DEFAULT').upper()
    lvl = f" | {data.get('level')}" if data.get('level') else ""
    
    # Логируем
    txt = message.text if message.text else ("[ФОТО/ВИДЕО]" if not message.caption else f"[МЕДИА] {message.caption}")
    log_message(message.from_user.id, f"{cat}{lvl}", txt)
    
    username = f"@{message.from_user.username}" if message.from_user.username else "NoName"
    header = f"✉️ {cat}{lvl}\n👤 Юзер: {username}\n🆔 ID: `{message.from_user.id}`"
    
    await bot.send_message(
        chat_id=ADMIN_ID, 
        text=f"{header}\n\n💬 Сообщение юзера:", 
        reply_markup=admin_reply_kb(message.from_user.id)
    )
    await bot.copy_message(chat_id=ADMIN_ID, from_chat_id=message.chat.id, message_id=message.message_id)
    
    await message.answer(TEXTS[LANG]["success"])
    await state.clear()

@dp.callback_query(F.data.startswith("rep_"))
async def handle_admin_reply(callback: types.CallbackQuery):
    _, action, user_id = callback.data.split("_")
    if action == "auto":
        await bot.send_message(chat_id=user_id, text=random.choice(AUTO_REPLIES))
        await callback.message.edit_text(callback.message.text + "\n\n✅ Отправлен автоответ.")
    elif action == "personal":
        await bot.send_message(chat_id=user_id, text="Привет! Это разработчик 14 OS. О чем ты хотел поговорить?")
        await callback.message.edit_text(callback.message.text + "\n\n💬 Отправлено личное приветствие.")
    await callback.answer()

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
