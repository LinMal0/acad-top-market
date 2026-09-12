from aiogram.types import (
    ReplyKeyboardMarkup, KeyboardButton,
    InlineKeyboardMarkup, InlineKeyboardButton
)


def main_menu():
    kb = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📦 Подать объявление")],
            [KeyboardButton(text="📋 Мои объявления"), KeyboardButton(text="❓ Помощь")],
            [KeyboardButton(text="📢 Канал с объявлениями")],
        ],
        resize_keyboard=True
    )
    return kb


def categories_kb():
    kb = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="💻 Техника"), KeyboardButton(text="📚 Книги")],
            [KeyboardButton(text="👕 Одежда"), KeyboardButton(text="📦 Другое")],
            [KeyboardButton(text="⬅️ Отмена")],
        ],
        resize_keyboard=True
    )
    return kb


def moderation_kb(item_id):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Опубликовать", callback_data=f"approve_{item_id}"),
            InlineKeyboardButton(text="❌ Отклонить", callback_data=f"reject_{item_id}")
        ]
    ])
    return kb


def consent_kb():
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Согласен", callback_data="consent_yes")],
        [InlineKeyboardButton(text="❌ Отказаться", callback_data="consent_no")],
    ])
    return kb


def confirm_cancel_kb():
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Да, отменить", callback_data="cancel_yes")],
        [InlineKeyboardButton(text="↩️ Нет, вернуться", callback_data="cancel_no")],
    ])
    return kb


def admin_menu_kb():
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📊 Статистика", callback_data="admin_stats")],
        [InlineKeyboardButton(text="⏳ На модерации", callback_data="admin_pending")],
        [InlineKeyboardButton(text="📢 Рассылка", callback_data="admin_broadcast")],
    ])
    return kb


def admin_back_kb():
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⬅️ Назад в админ-панель", callback_data="admin_back")],
    ])
    return kb


def broadcast_confirm_kb():
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Отправить всем", callback_data="broadcast_send")],
        [InlineKeyboardButton(text="❌ Отмена", callback_data="admin_back")],
    ])
    return kb
def payment_kb(pay_url, item_id):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💳 Оплатить через СБП", url=pay_url)],
        [InlineKeyboardButton(text="🔄 Проверить оплату", callback_data=f"check_{item_id}")]
    ])
    return kb