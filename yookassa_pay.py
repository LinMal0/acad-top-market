import uuid
from yookassa import Configuration, Payment
from config import YOOKASSA_SHOP_ID, YOOKASSA_SECRET_KEY

Configuration.account_id = YOOKASSA_SHOP_ID
Configuration.secret_key = YOOKASSA_SECRET_KEY


def create_payment(amount: int, item_id: int, user_id: int):
    """Создаёт платёж, возвращает (ссылка, payment_id)."""
    idempotence_key = str(uuid.uuid4())

    payment = Payment.create({
        "amount": {
            "value": f"{amount}.00",
            "currency": "RUB"
        },
        "confirmation": {
            "type": "redirect",
            "return_url": "https://t.me"
        },
        "capture": True,
        "description": f"Публикация объявления #{item_id}",
        "metadata": {
            "item_id": item_id,
            "user_id": user_id
        }
    }, idempotence_key)

    return payment.confirmation.confirmation_url, payment.id


def check_payment(payment_id: str) -> bool:
    """Проверяет, оплачен ли платёж."""
    try:
        payment = Payment.find_one(payment_id)
        return payment.status == "succeeded"
    except Exception:
        return False