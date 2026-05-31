import asyncio
import os
from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage

# --- НАСТРОЙКИ --- 
TOKEN = os.getenv('TOKEN')    # Сюда вставь свой токен от BotFather
MY_ID = int(os.getenv('ADMIN_ID'))        # Сюда вставь свой ID (числом)

bot = Bot(token=TOKEN)
dp = Dispatcher(storage=MemoryStorage())

# Состояния для бота
class Feedback(StatesGroup):
    category = State()
    level = State()
    waiting_for_text = State()

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

# --- ЛОГИКА ---
@dp.message(Command("start"))
async def start(message: types.Message):
    await message.answer("Привет! Ты нашел секретный канал связи 14ОС. Выбирай:", reply_markup=main_kb())

@dp.callback_query(F.data.startswith("cat_"))
async def handle_category(callback: types.CallbackQuery, state: FSMContext):
    cat = callback.data.split("_")[1]
    await state.update_data(category=cat)
    
    if cat == "bug":
        await callback.message.answer("Ого, ошибка? Насколько она серьезна?", reply_markup=bug_kb())
    else:
        await state.set_state(Feedback.waiting_for_text)
        await callback.message.answer("Принято. Пиши, что хочешь передать автору:")
    await callback.answer()

@dp.callback_query(F.data.startswith("bug_"))
async def handle_bug_level(callback: types.CallbackQuery, state: FSMContext):
    level = "КРИТИЧЕСКИ ❗️" if callback.data == "bug_crit" else "МЕЛКИЙ БАГ ⚠️"
    await state.update_data(level=level)
    await state.set_state(Feedback.waiting_for_text)
    await callback.message.answer(f"Принято ({level}). Опиши баг подробнее:")
    await callback.answer()

@dp.message(Feedback.waiting_for_text)
async def final_message(message: types.Message, state: FSMContext):
    data = await state.get_data()
    cat = data.get('category').upper()
    lvl = f" | {data.get('level')}" if data.get('level') else ""
    
    # Если юзернейм есть, он покажет его (например, @Yegor_baka), если нет — напишет NoName
    username = f"@{message.from_user.username}" if message.from_user.username else "NoName"
    
    text_to_me = (f"✉️ {cat}{lvl}\n"
                  f"👤 Юзер: {username}\n"
                  f"🆔 ID: `{message.from_user.id}`\n\n"
                  f"💬 Сообщение: {message.text}")
    
    await bot.send_message(chat_id=MY_ID, text=text_to_me, parse_mode="Markdown")
    await message.answer("Сообщение успешно доставлено Егору! Спасибо!")
    await state.clear()

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())