import asyncio
import logging
import os
import sqlite3
from datetime import datetime
from urllib.parse import quote
from zoneinfo import ZoneInfo

from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)

# ===================== НАСТРОЙКИ =====================
BOT_TOKEN = os.getenv("BOT_TOKEN", "PUT_YOUR_TOKEN_HERE")  # токен от @BotFather

LANG = "uz"  # "uz" или "ru"

CANDIDATE_NAME = "Samadov Elyorjon Ixtiyor o'g'li"
CANDIDATE_NUMBER = 3  # номер кандидата в боте конкурса

CONTEST_BOT_LINK = os.getenv("CONTEST_BOT_LINK", "https://t.me/TIPU_TANLOV_BOT")  # бот конкурса (проверьте!)
CHANNEL_LINK = os.getenv("CHANNEL_LINK", "https://t.me/your_channel")             # канал для подписки
MY_BOT_LINK = "https://t.me/ElyorjonVoteYordamBot"  # ссылка на ВАШЕГО бота-помощника

TIMEZONE = ZoneInfo("Asia/Tashkent")
# Время напоминаний (по Ташкенту), формат "ГГГГ-ММ-ДД ЧЧ:ММ"
REMINDERS = [
    "2026-10-26 10:00",
    "2026-10-27 18:00",
]
DB_PATH = "bot.db"
# =====================================================

TEXTS = {
    "uz": {
        "start": (
            "Salom! 👋\n"
            "Men {name} uchun ovoz yig'ishda yordam beraman.\n\n"
            "Quyidagi tugmalardan birini tanlang:"
        ),
        "how": (
            "🗳 <b>Qanday ovoz berish kerak?</b>\n\n"
            "1️⃣ Tanlov botini oching: {contest}\n"
            "2️⃣ Kanalga obuna bo'ling: {channel}\n"
            "3️⃣ Botda <b>{number}</b>-raqamni bosing\n\n"
            "⚠️ Har bir akkaunt faqat bitta ovoz bera oladi."
        ),
        "share_text": (
            "Salom! {name} uchun ovoz bering 🙏\n"
            "Ovoz berish tartibi: bot {contest}, kanalga obuna bo'ling va "
            "{number}-raqamni bosing. Bir daqiqa vaqt oladi!"
        ),
        "share_msg": "Pastdagi tugmani bosing va do'stlaringizga yoki guruhlarga yuboring 👇",
        "btn_how": "🗳 Qanday ovoz berish kerak",
        "btn_share": "📤 Do'stlarga yuborish",
        "btn_remind_on": "🔔 Eslatma yoqish",
        "btn_remind_off": "🔕 Eslatmani o'chirish",
        "btn_send": "📤 Yuborish",
        "btn_contest": "🗳 Tanlov botini ochish",
        "remind_on": "Eslatma yoqildi ✅ Ovoz berish kunlarida yozaman.",
        "remind_off": "Eslatma o'chirildi.",
        "reminder": (
            "⏰ Eslatma: ovoz berishni unutmang!\n"
            "{name} uchun {number}-raqamni bosing: {contest}"
        ),
    },
    "ru": {
        "start": (
            "Привет! 👋\n"
            "Я помогаю собирать голоса за {name}.\n\n"
            "Выберите действие:"
        ),
        "how": (
            "🗳 <b>Как проголосовать?</b>\n\n"
            "1️⃣ Откройте бота конкурса: {contest}\n"
            "2️⃣ Подпишитесь на канал: {channel}\n"
            "3️⃣ В боте нажмите цифру <b>{number}</b>\n\n"
            "⚠️ Каждый аккаунт может проголосовать только один раз."
        ),
        "share_text": (
            "Привет! Проголосуй за {name} 🙏\n"
            "Открой бота {contest}, подпишись на канал и нажми "
            "цифру {number}. Это займёт минуту!"
        ),
        "share_msg": "Нажмите кнопку ниже и отправьте друзьям или в группы 👇",
        "btn_how": "🗳 Как проголосовать",
        "btn_share": "📤 Переслать друзьям",
        "btn_remind_on": "🔔 Напомнить мне",
        "btn_remind_off": "🔕 Отключить напоминания",
        "btn_send": "📤 Отправить",
        "btn_contest": "🗳 Открыть бота конкурса",
        "remind_on": "Напоминания включены ✅ Напишу в дни голосования.",
        "remind_off": "Напоминания отключены.",
        "reminder": (
            "⏰ Напоминание: не забудьте проголосовать!\n"
            "Нажмите цифру {number} за {name}: {contest}"
        ),
    },
}
T = TEXTS[LANG]


def fmt(key: str) -> str:
    return T[key].format(
        name=CANDIDATE_NAME,
        number=CANDIDATE_NUMBER,
        contest=CONTEST_BOT_LINK,
        channel=CHANNEL_LINK,
    )


# ---------- база данных ----------
def db():
    return sqlite3.connect(DB_PATH)


def init_db():
    with db() as c:
        c.execute("CREATE TABLE IF NOT EXISTS subs (user_id INTEGER PRIMARY KEY)")
        c.execute("CREATE TABLE IF NOT EXISTS sent (slot TEXT PRIMARY KEY)")


def is_subscribed(user_id: int) -> bool:
    with db() as c:
        return c.execute("SELECT 1 FROM subs WHERE user_id=?", (user_id,)).fetchone() is not None


def set_subscribed(user_id: int, on: bool):
    with db() as c:
        if on:
            c.execute("INSERT OR IGNORE INTO subs VALUES (?)", (user_id,))
        else:
            c.execute("DELETE FROM subs WHERE user_id=?", (user_id,))


# ---------- клавиатуры ----------
def main_kb(user_id: int) -> InlineKeyboardMarkup:
    remind_btn = (
        InlineKeyboardButton(text=T["btn_remind_off"], callback_data="remind_off")
        if is_subscribed(user_id)
        else InlineKeyboardButton(text=T["btn_remind_on"], callback_data="remind_on")
    )
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=T["btn_how"], callback_data="how")],
            [InlineKeyboardButton(text=T["btn_share"], callback_data="share")],
            [remind_btn],
        ]
    )


dp = Dispatcher()


@dp.message(CommandStart())
async def start(m: Message):
    await m.answer(fmt("start"), reply_markup=main_kb(m.from_user.id))


@dp.callback_query(F.data == "how")
async def how(cb: CallbackQuery):
    kb = InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text=T["btn_contest"], url=CONTEST_BOT_LINK)]]
    )
    await cb.message.answer(fmt("how"), reply_markup=kb, parse_mode="HTML",
                            disable_web_page_preview=True)
    await cb.answer()


@dp.callback_query(F.data == "share")
async def share(cb: CallbackQuery):
    text = fmt("share_text")
    share_url = f"https://t.me/share/url?url={quote(MY_BOT_LINK)}&text={quote(text)}"
    kb = InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text=T["btn_send"], url=share_url)]]
    )
    await cb.message.answer(fmt("share_msg"), reply_markup=kb)
    await cb.answer()


@dp.callback_query(F.data.in_({"remind_on", "remind_off"}))
async def remind(cb: CallbackQuery):
    on = cb.data == "remind_on"
    set_subscribed(cb.from_user.id, on)
    await cb.message.edit_reply_markup(reply_markup=main_kb(cb.from_user.id))
    await cb.answer(T["remind_on"] if on else T["remind_off"], show_alert=False)


# ---------- рассылка напоминаний ----------
async def reminder_loop(bot: Bot):
    while True:
        now = datetime.now(TIMEZONE).strftime("%Y-%m-%d %H:%M")
        if now in REMINDERS:
            with db() as c:
                already = c.execute("SELECT 1 FROM sent WHERE slot=?", (now,)).fetchone()
                if not already:
                    c.execute("INSERT INTO sent VALUES (?)", (now,))
                    users = [r[0] for r in c.execute("SELECT user_id FROM subs")]
                else:
                    users = []
            for uid in users:
                try:
                    await bot.send_message(uid, fmt("reminder"))
                except Exception as e:  # пользователь заблокировал бота и т.п.
                    logging.warning("send to %s failed: %s", uid, e)
                await asyncio.sleep(0.05)  # не превышаем лимиты Telegram
        await asyncio.sleep(30)


async def main():
    logging.basicConfig(level=logging.INFO)
    init_db()
    bot = Bot(BOT_TOKEN)
    asyncio.create_task(reminder_loop(bot))
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
