from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup


def start_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="➕ Задача"), KeyboardButton(text="📋 Список")],
            [KeyboardButton(text="🗓 План"), KeyboardButton(text="⚙️ Настройки")],
        ],
        resize_keyboard=True,
    )


def task_card_keyboard(task_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Done", callback_data=f"done:{task_id}"),
                InlineKeyboardButton(text="🕒 Snooze 10m", callback_data=f"snooze:{task_id}:10"),
                InlineKeyboardButton(text="🕒 Snooze 1h", callback_data=f"snooze:{task_id}:60"),
            ],
            [
                InlineKeyboardButton(text="📅 Tomorrow 10:00", callback_data=f"tomorrow:{task_id}"),
                InlineKeyboardButton(text="🗑 Delete", callback_data=f"delete:{task_id}"),
            ],
        ]
    )
