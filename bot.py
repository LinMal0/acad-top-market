import asyncio
import logging

from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import Message, CallbackQuery

from config import BOT_TOKEN, ADMIN_ID, CHANNEL_ID, PRICE_PER_AD
import database as db
from keyboards import (
    main_menu, categories_kb, moderation_kb,
    consent_kb, confirm_cancel_kb,
    admin_menu_kb, admin_back_kb, broadcast_confirm_kb,
    payment_kb
)

logging.basicConfig(level=logging.INFO)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

CHANNEL_LINK = "https://t.me/AcadTopMarket"


# ---------- Состояния FSM ----------
class AdForm(StatesGroup):
    category = State()
    title = State()
    price = State()
    description = State()
    photo = State()
    consent = State()


class BroadcastForm(StatesGroup):
    waiting_text = State()


# ---------- /start ----------
@dp.message(CommandStart())
async def start(message: Message):
    db.init_db()
    db.register_user(message.from_user.id)
    await message.answer(
        f"👋 Привет, {message.from_user.first_name}!\n\n"
        f"Это <b>ТОП Маркет</b> — барахолка Академии ТОП.\n\n"
        f"📦 Здесь можно продать или купить технику, книги, одежду и всё что угодно.\n"
        f"🎁 Публикация объявлений — бесплатно!\n\n"
        f"📢 <b>Канал с объявлениями:</b>\n"
        f"{CHANNEL_LINK}",
        reply_markup=main_menu(),
        parse_mode="HTML",
        disable_web_page_preview=False
    )


# ---------- Помощь ----------
@dp.message(F.text == "❓ Помощь")
async def help_cmd(message: Message):
    db.update_last_seen(message.from_user.id)
    await message.answer(
        "❓ Как пользоваться:\n\n"
        "1. Нажми «📦 Подать объявление»\n"
        "2. Заполни данные о товаре\n"
        "3. Отправь фото\n"
        "4. Подтверди публикацию\n"
        "5. Дождись модерации\n\n"
        "После одобрения объявление появится в канале."
    )


# ---------- Канал ----------
@dp.message(F.text == "📢 Канал с объявлениями")
async def go_to_channel(message: Message):
    db.update_last_seen(message.from_user.id)
    await message.answer(
        f"📢 Все объявления публикуются здесь:\n\n"
        f"👉 {CHANNEL_LINK}\n\n"
        f"Подпишись, чтобы не пропустить свежие предложения!",
        disable_web_page_preview=False
    )


# ---------- Подача объявления ----------
@dp.message(F.text == "📦 Подать объявление")
async def start_ad(message: Message, state: FSMContext):
    db.update_last_seen(message.from_user.id)
    await state.clear()
    await message.answer("Выбери категорию товара:", reply_markup=categories_kb())
    await state.set_state(AdForm.category)


@dp.message(AdForm.category)
async def process_category(message: Message, state: FSMContext):
    if message.text == "⬅️ Отмена":
        await state.clear()
        await message.answer("Отменено.", reply_markup=main_menu())
        return
    await state.update_data(category=message.text)
    await message.answer("✏️ Введи название товара:")
    await state.set_state(AdForm.title)


@dp.message(AdForm.title)
async def process_title(message: Message, state: FSMContext):
    await state.update_data(title=message.text)
    await message.answer("💰 Введи цену в рублях (только число):")
    await state.set_state(AdForm.price)


@dp.message(AdForm.price)
async def process_price(message: Message, state: FSMContext):
    if not message.text.isdigit():
        await message.answer("Пожалуйста, введи число без букв. Например: 500")
        return
    await state.update_data(price=int(message.text))
    await message.answer("📝 Опиши товар (состояние, детали, причина продажи):")
    await state.set_state(AdForm.description)


@dp.message(AdForm.description)
async def process_description(message: Message, state: FSMContext):
    await state.update_data(description=message.text)
    await message.answer("📸 Отправь фото товара:")
    await state.set_state(AdForm.photo)


@dp.message(AdForm.photo, F.photo)
async def process_photo(message: Message, state: FSMContext):
    photo_id = message.photo[-1].file_id
    await state.update_data(photo_id=photo_id)

    await message.answer(
        "📢 <b>Перед публикацией</b>\n\n"
        "В объявлении в канале будет указан твой @username, "
        "чтобы покупатель мог с тобой связаться.\n\n"
        "Ты согласен на публикацию?",
        reply_markup=consent_kb(),
        parse_mode="HTML"
    )
    await state.set_state(AdForm.consent)


@dp.message(AdForm.photo)
async def process_photo_invalid(message: Message):
    await message.answer("Пожалуйста, отправь именно фото 📸")


@dp.callback_query(F.data == "consent_yes", AdForm.consent)
async def consent_yes(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    user_id = callback.from_user.id
    username = callback.from_user.username or "нет username"

    db.update_last_seen(user_id)

    item_id = db.add_item(
        user_id=user_id,
        username=username,
        category=data["category"],
        title=data["title"],
        price=data["price"],
        description=data["description"],
        photo_id=data["photo_id"],
    )

    await callback.message.edit_text(
        f"✅ Объявление отправлено на модерацию!\n\n"
        f"После проверки оно появится в канале:\n"
        f"👉 {CHANNEL_LINK}"
    )
    await callback.message.answer("Главное меню:", reply_markup=main_menu())

    await notify_admin(item_id)
    await state.clear()
    await callback.answer()


@dp.callback_query(F.data == "consent_no", AdForm.consent)
async def consent_no(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text(
        "⚠️ Если ты откажешься, объявление не будет опубликовано.\n\n"
        "Ты уверен?",
        reply_markup=confirm_cancel_kb()
    )
    await callback.answer()


@dp.callback_query(F.data == "cancel_yes", AdForm.consent)
async def cancel_yes(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text(
        "❌ Объявление отменено.\n"
        "Ты можешь подать новое в любой момент."
    )
    await callback.message.answer("Главное меню:", reply_markup=main_menu())
    await callback.answer()


@dp.callback_query(F.data == "cancel_no", AdForm.consent)
async def cancel_no(callback: CallbackQuery):
    await callback.message.edit_text(
        "📢 <b>Перед публикацией</b>\n\n"
        "В объявлении в канале будет указан твой @username, "
        "чтобы покупатель мог с тобой связаться.\n\n"
        "Ты согласен на публикацию?",
        reply_markup=consent_kb(),
        parse_mode="HTML"
    )
    await callback.answer()


# ---------- Уведомление админу ----------
async def notify_admin(item_id: int):
    item = db.get_item(item_id)

    text = (
        f"🆕 <b>Новое объявление #{item[0]}</b>\n\n"
        f"👤 @{item[2]}\n"
        f"📂 {item[3]}\n"
        f"📦 <b>{item[4]}</b>\n"
        f"💰 {item[5]} ₽\n"
        f"📝 {item[6]}"
    )

    await bot.send_photo(
        ADMIN_ID,
        photo=item[7],
        caption=text,
        reply_markup=moderation_kb(item_id),
        parse_mode="HTML"
    )


# ---------- Публикация в канал ----------
async def publish_to_channel(item):
    text = (
        f"🛒 <b>{item[4]}</b>\n\n"
        f"💰 Цена: <b>{item[5]} ₽</b>\n"
        f"📂 Категория: {item[3]}\n"
        f"📝 {item[6]}\n\n"
        f"📞 Связь: @{item[2]}"
    )
    await bot.send_photo(CHANNEL_ID, photo=item[7], caption=text, parse_mode="HTML")

    try:
        await bot.send_message(
            item[1],
            f"✅ Твоё объявление <b>«{item[4]}»</b> опубликовано в канале!\n\n"
            f"Посмотреть: {CHANNEL_LINK}",
            parse_mode="HTML"
        )
    except Exception:
        pass


# ---------- Модерация: одобрить ----------
@dp.callback_query(F.data.startswith("approve_"))
async def approve_ad(callback: CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("Не твоё дело 😉", show_alert=True)
        return

    item_id = int(callback.data.split("_")[1])
    db.update_status(item_id, "approved")
    item = db.get_item(item_id)

    await publish_to_channel(item)

    await callback.message.edit_caption(
        caption=callback.message.caption + "\n\n✅ <b>ОПУБЛИКОВАНО</b>",
        parse_mode="HTML"
    )
    await callback.answer("Опубликовано!")


# ---------- Проверка оплаты (заглушка) ----------
@dp.callback_query(F.data.startswith("check_"))
async def check_pay(callback: CallbackQuery):
    await callback.answer("Оплата временно отключена", show_alert=True)


# ---------- Модерация: отклонить ----------
@dp.callback_query(F.data.startswith("reject_"))
async def reject_ad(callback: CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("Не твоё дело 😉", show_alert=True)
        return

    item_id = int(callback.data.split("_")[1])
    item = db.get_item(item_id)
    db.update_status(item_id, "rejected")

    try:
        await bot.send_message(
            item[1],
            f"❌ Твоё объявление <b>«{item[4]}»</b> отклонено модератором.",
            parse_mode="HTML"
        )
    except Exception:
        pass

    await callback.message.edit_caption(
        caption=callback.message.caption + "\n\n❌ <b>ОТКЛОНЕНО</b>",
        parse_mode="HTML"
    )
    await callback.answer("Отклонено")


# ---------- Мои объявления ----------
@dp.message(F.text == "📋 Мои объявления")
async def my_ads(message: Message):
    db.update_last_seen(message.from_user.id)
    rows = db.get_user_items(message.from_user.id)

    if not rows:
        await message.answer("У тебя пока нет объявлений.")
        return

    status_map = {
        "pending": "⏳ На модерации",
        "approved": "✅ Опубликовано",
        "rejected": "❌ Отклонено"
    }

    text = "📋 <b>Твои объявления:</b>\n\n"
    for r in rows:
        text += f"#{r[0]} — {r[1]} — {r[2]} ₽ — {status_map.get(r[3], r[3])}\n"

    await message.answer(text, parse_mode="HTML")


# ==================================================
#                    АДМИН-ПАНЕЛЬ
# ==================================================

@dp.message(F.text == "/admin")
async def admin_panel(message: Message):
    if message.from_user.id != ADMIN_ID:
        return

    await message.answer(
        "🎛️ <b>Админ-панель</b>\n\n"
        "Выбери действие:",
        reply_markup=admin_menu_kb(),
        parse_mode="HTML"
    )


@dp.callback_query(F.data == "admin_back")
async def admin_back(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("Не твоё дело 😉", show_alert=True)
        return

    await state.clear()
    await callback.message.edit_text(
        "🎛️ <b>Админ-панель</b>\n\n"
        "Выбери действие:",
        reply_markup=admin_menu_kb(),
        parse_mode="HTML"
    )
    await callback.answer()


@dp.callback_query(F.data == "admin_stats")
async def admin_stats_cb(callback: CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("Не твоё дело 😉", show_alert=True)
        return

    stats = db.get_stats()
    text = (
        f"📊 <b>Статистика барахолки</b>\n\n"
        f"👥 Всего пользователей: {stats['users']}\n"
        f"📈 Новых за неделю: {stats['new_week']}\n"
        f"🔥 Активных за неделю: {stats['active_week']}\n\n"
        f"📦 Всего объявлений: {stats['total']}\n"
        f"⏳ На модерации: {stats['pending']}\n"
        f"✅ Опубликовано: {stats['approved']}\n"
        f"❌ Отклонено: {stats['rejected']}"
    )
    await callback.message.edit_text(
        text,
        reply_markup=admin_back_kb(),
        parse_mode="HTML"
    )
    await callback.answer()


@dp.callback_query(F.data == "admin_pending")
async def admin_pending_cb(callback: CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("Не твоё дело 😉", show_alert=True)
        return

    rows = db.get_pending_items()

    if not rows:
        text = "✅ На модерации ничего нет."
    else:
        text = "⏳ <b>На модерации:</b>\n\n"
        for r in rows:
            text += f"#{r[0]} — {r[1]} — {r[2]} ₽\n"

    await callback.message.edit_text(
        text,
        reply_markup=admin_back_kb(),
        parse_mode="HTML"
    )
    await callback.answer()


@dp.callback_query(F.data == "admin_broadcast")
async def admin_broadcast_cb(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("Не твоё дело 😉", show_alert=True)
        return

    await state.set_state(BroadcastForm.waiting_text)
    await callback.message.edit_text(
        "📢 <b>Рассылка</b>\n\n"
        "Отправь текст, который нужно разослать всем пользователям.\n\n"
        "⚠️ Отменить: /cancel",
        parse_mode="HTML"
    )
    await callback.answer()


@dp.message(BroadcastForm.waiting_text, F.text == "/cancel")
async def broadcast_cancel(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(
        "❌ Рассылка отменена.",
        reply_markup=admin_menu_kb()
    )


@dp.message(BroadcastForm.waiting_text)
async def broadcast_preview(message: Message, state: FSMContext):
    await state.update_data(broadcast_text=message.text)

    await message.answer(
        f"📢 <b>Предпросмотр:</b>\n\n{message.text}\n\n"
        f"Отправить всем пользователям?",
        reply_markup=broadcast_confirm_kb(),
        parse_mode="HTML"
    )


@dp.callback_query(F.data == "broadcast_send", BroadcastForm.waiting_text)
async def broadcast_send(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("Не твоё дело 😉", show_alert=True)
        return

    data = await state.get_data()
    text = data.get("broadcast_text", "")
    user_ids = db.get_all_user_ids()

    await callback.message.edit_text(
        f"📢 Отправляю {len(user_ids)} пользователям..."
    )

    sent = 0
    failed = 0

    for uid in user_ids:
        try:
            await bot.send_message(uid, text)
            sent += 1
        except Exception:
            failed += 1
        await asyncio.sleep(0.05)

    await callback.message.edit_text(
        f"✅ <b>Рассылка завершена</b>\n\n"
        f"📨 Отправлено: {sent}\n"
        f"❌ Ошибок: {failed}",
        reply_markup=admin_back_kb(),
        parse_mode="HTML"
    )
    await state.clear()
    await callback.answer()


# ---------- Запуск ----------
async def main():
    db.init_db()
    print("🤖 Бот запущен...")
    await dp.start_polling(
        bot,
        allowed_updates=["message", "callback_query"]
    )


if __name__ == "__main__":
    asyncio.run(main())
