"""
Carpet Cleaning Telegram Bot
=============================
pip install python-telegram-bot==20.7
python carpet_cleaning_bot.py
"""

import logging
import math
import os
from telegram import (
    Update,
    ReplyKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardRemove,
)
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ConversationHandler,
    filters,
    ContextTypes,
)

BOT_TOKEN = os.environ["BOT_TOKEN"]
ADMIN_CHAT_IDS = [
    int(cid.strip())
    for cid in os.environ.get("ADMIN_CHAT_ID", "7286678108").split(",")
    if cid.strip()
]

OFFICE_LAT = 40.881278
OFFICE_LON = 71.151750

PRICE_PER_SQM = 10_000   # gilam va korpacha uchun

# Odiyol narxlari (o'lchamlarsiz)
ODIYOL_PRICES = {
    "Kichik odiyol - 40 000 som": 40_000,
    "Katta odiyol - 50 000 som": 50_000,
}

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)

(
    CHOOSE_TYPE,
    GET_SIZE,
    CHOOSE_ODIYOL_SIZE,
    GET_LOCATION,
    CHOOSE_DELIVERY,
    GET_CONTACT,
    GET_NAME,
) = range(7)

ITEM_TYPES = {
    "Gilam": "gilam",
    "Korpacha": "korpacha",
    "Odiyol": "odiyol",
}


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data.clear()

    await update.message.reply_text(
        "Assalomu alaykum!\n"
        "Xush kelibsiz Gilam yuvish xizmatiga!\n\n"
        "Quyidagilardan birini tanlang:",
        reply_markup=ReplyKeyboardMarkup(
            [[btn] for btn in ITEM_TYPES.keys()],
            resize_keyboard=True,
        ),
    )
    return CHOOSE_TYPE


async def choose_type(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = update.message.text
    if text not in ITEM_TYPES:
        await update.message.reply_text("Iltimos, quyidagi tugmalardan birini tanlang.")
        return CHOOSE_TYPE

    context.user_data["item_type"] = ITEM_TYPES[text]
    context.user_data["item_label"] = text

    if ITEM_TYPES[text] == "odiyol":
        await update.message.reply_text(
            "Odiyol turini tanlang:",
            reply_markup=ReplyKeyboardMarkup(
                [[btn] for btn in ODIYOL_PRICES.keys()],
                resize_keyboard=True,
            ),
        )
        return CHOOSE_ODIYOL_SIZE

    if ITEM_TYPES[text] == "korpacha":
        await update.message.reply_text(
            f"Siz tanladingiz: {text}\n\n"
            "Korpachaning uzunligini kiriting (metrda).\n"
            "Masalan: 3 yoki 4.5",
            reply_markup=ReplyKeyboardRemove(),
        )
    else:
        await update.message.reply_text(
            f"Siz tanladingiz: {text}\n\n"
            "Endi o'lchamini kiriting.\n"
            "Masalan: 2x3 yoki 1.5x2 (metrda)",
            reply_markup=ReplyKeyboardRemove(),
        )
    return GET_SIZE


async def choose_odiyol_size(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = update.message.text
    if text not in ODIYOL_PRICES:
        await update.message.reply_text("Iltimos, quyidagi tugmalardan birini tanlang.")
        return CHOOSE_ODIYOL_SIZE

    price = ODIYOL_PRICES[text]
    context.user_data["item_label"] = text
    context.user_data["washing_cost"] = price
    context.user_data["area"] = None
    context.user_data["width"] = None
    context.user_data["height"] = None

    await update.message.reply_text(
        f"Narx: {price:,} som\n\n"
        "Manzilingizni yuboring.\n"
        "Quyidagi tugmani bosib joylashuvingizni ulashing:",
        reply_markup=ReplyKeyboardMarkup(
            [[KeyboardButton("Joylashuvni ulashish", request_location=True)]],
            resize_keyboard=True,
        ),
    )
    return GET_LOCATION


async def get_size(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = update.message.text.strip().replace(" ", "").replace(",", ".")
    item_type = context.user_data.get("item_type")

    # Korpacha — faqat uzunlik (pogon metr)
    if item_type == "korpacha":
        try:
            length = float(text)
        except ValueError:
            await update.message.reply_text(
                "Uzunlikni to'g'ri kiriting.\n"
                "Masalan: 3 yoki 4.5",
            )
            return GET_SIZE

        total = int(length * PRICE_PER_SQM)
        context.user_data["width"] = None
        context.user_data["height"] = length
        context.user_data["area"] = None
        context.user_data["washing_cost"] = total

        await update.message.reply_text(
            f"Uzunlik: {length} m\n"
            f"Yuvish narxi: {total:,} som\n\n"
            "Manzilingizni yuboring.\n"
            "Quyidagi tugmani bosib joylashuvingizni ulashing:",
            reply_markup=ReplyKeyboardMarkup(
                [[KeyboardButton("Joylashuvni ulashish", request_location=True)]],
                resize_keyboard=True,
            ),
        )
        return GET_LOCATION

    # Gilam — kvadrat metr (eni x uzunlik)
    for sep in ["x", "х", "*", "×"]:
        if sep in text:
            parts = text.split(sep)
            try:
                w = float(parts[0])
                h = float(parts[1])
                break
            except (ValueError, IndexError):
                pass
    else:
        await update.message.reply_text(
            "O'lchamni to'g'ri kiriting.\n"
            "Masalan: 2x3 yoki 1.5x2",
        )
        return GET_SIZE

    area = round(w * h, 2)
    total = int(area * PRICE_PER_SQM)

    context.user_data["width"] = w
    context.user_data["height"] = h
    context.user_data["area"] = area
    context.user_data["washing_cost"] = total

    await update.message.reply_text(
        f"O'lcham: {w} x {h} m = {area} m2\n"
        f"Yuvish narxi: {total:,} som\n\n"
        "Manzilingizni yuboring.\n"
        "Quyidagi tugmani bosib joylashuvingizni ulashing:",
        reply_markup=ReplyKeyboardMarkup(
            [[KeyboardButton("Joylashuvni ulashish", request_location=True)]],
            resize_keyboard=True,
        ),
    )
    return GET_LOCATION


def haversine(lat1, lon1, lat2, lon2) -> float:
    R = 6371
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(math.radians(lat1))
        * math.cos(math.radians(lat2))
        * math.sin(dlon / 2) ** 2
    )
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


async def get_location(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    location = update.message.location
    if not location:
        await update.message.reply_text("Iltimos, joylashuvingizni ulashing.")
        return GET_LOCATION

    lat = location.latitude
    lon = location.longitude
    dist = round(haversine(OFFICE_LAT, OFFICE_LON, lat, lon), 1)

    context.user_data["lat"] = lat
    context.user_data["lon"] = lon
    context.user_data["distance_km"] = dist
    context.user_data["delivery_cost"] = 0  # Yetkazib berish bepul

    await update.message.reply_text(
        f"Ofisdan masofasi: {dist} km\n"
        f"Yetkazib berish: BEPUL\n\n"
        "Qanday usulda olishni xohlaysiz?",
        reply_markup=ReplyKeyboardMarkup(
            [["Yetkazib berish kerak", "O'zim olib ketaman"]],
            resize_keyboard=True,
        ),
    )
    return CHOOSE_DELIVERY


async def choose_delivery(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = update.message.text

    if "O'zim" in text or "olib" in text.lower():
        context.user_data["delivery"] = "O'zim olib ketaman"
        context.user_data["delivery_cost"] = 0
    else:
        context.user_data["delivery"] = "Yetkazib berish"

    await update.message.reply_text(
        "Telefon raqamingizni yuboring.\n\n"
        "Tugmani bosib ulashing yoki o'zingiz qo'lda yozing.\n"
        "Masalan: +998 94 999 99 99",
        reply_markup=ReplyKeyboardMarkup(
            [[KeyboardButton("Raqamni ulashish", request_contact=True)]],
            resize_keyboard=True,
        ),
    )
    return GET_CONTACT


def normalize_phone(raw: str) -> str:
    """
    Telefon raqamni qabul qiladi va kerak bo'lsa formatlaydi.
    Raqamlarni (va boshidagi +ni) qoldiradi, bo'sh joy/tire kabi belgilarni olib tashlaydi.
    Qabul qilinadigan misollar:
      +998 94 999 99 99
      998999999999
      99 999 99 99
      999999999
    """
    raw = raw.strip()
    digits = "".join(ch for ch in raw if ch.isdigit())

    if not digits:
        return ""

    # Agar 998 bilan boshlanmasa va 9 xonali bo'lsa (masalan 94 999 99 99 -> 999999999), 998 qo'shamiz
    if digits.startswith("998"):
        normalized = digits
    elif len(digits) == 9:
        normalized = "998" + digits
    else:
        normalized = digits

    return "+" + normalized


async def get_contact(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    contact = update.message.contact
    text = update.message.text

    if contact:
        phone = contact.phone_number
    elif text:
        phone = normalize_phone(text)
        if not phone or len(phone) < 9:
            await update.message.reply_text(
                "Telefon raqamni to'g'ri kiriting.\n"
                "Masalan: +998 94 999 99 99\n\n"
                "Yoki tugmani bosib ulashing:"
            )
            return GET_CONTACT
    else:
        await update.message.reply_text("Iltimos, raqamingizni yuboring (yozing yoki ulashing).")
        return GET_CONTACT

    context.user_data["phone"] = phone

    await update.message.reply_text(
        "Ism va familiyangizni kiriting:\nMasalan: Alisher Karimov",
        reply_markup=ReplyKeyboardRemove(),
    )
    return GET_NAME


async def get_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    name = update.message.text.strip()
    if len(name) < 2:
        await update.message.reply_text("Iltimos, to'liq ism va familiyangizni kiriting.")
        return GET_NAME

    d = context.user_data
    d["full_name"] = name

    total = d["washing_cost"] + d.get("delivery_cost", 0)
    d["total"] = total

    if d.get("delivery") == "Yetkazib berish":
        delivery_line = f"Yetkazib berish: BEPUL ({d.get('distance_km', 0)} km)"
    else:
        delivery_line = "O'zim olib ketaman"

    if d.get("item_type") == "gilam" and d.get("area"):
        size_line = f"O'lcham: {d['width']} x {d['height']} m = {d['area']} m2"
    elif d.get("item_type") == "korpacha" and d.get("height"):
        size_line = f"Uzunlik: {d['height']} m"
    else:
        size_line = "O'lcham: belgilanmagan (odiyol)"

    summary = (
        f"Buyurtmangiz qabul qilindi!\n\n"
        f"Tur: {d['item_label']}\n"
        f"{size_line}\n"
        f"Yuvish: {d['washing_cost']:,} som\n"
        f"{delivery_line}\n"
        f"Jami: {total:,} som\n\n"
        f"Mijoz: {name}\n"
        f"Tel: {d['phone']}\n\n"
        "Tez orada siz bilan bog'lanamiz!"
    )

    await update.message.reply_text(summary)

    admin_msg = (
        f"Yangi buyurtma!\n\n"
        f"Mijoz: {name}\n"
        f"Tel: {d['phone']}\n"
        f"Manzil (koordinatalar): {d['lat']}, {d['lon']}\n"
        f"Tur: {d['item_label']}\n"
        f"{size_line}\n"
        f"Yuvish: {d['washing_cost']:,} som\n"
        f"Yetkazib berish: BEPUL\n"
        f"Usul: {d['delivery']}\n"
        f"Jami: {total:,} som"
    )

    for admin_id in ADMIN_CHAT_IDS:
        try:
            await context.bot.send_message(
                chat_id=admin_id,
                text=admin_msg,
            )
            await context.bot.send_location(
                chat_id=admin_id,
                latitude=d["lat"],
                longitude=d["lon"],
            )
        except Exception as e:
            logging.error(f"Admin xabari yuborilmadi ({admin_id}): {e}")

    return ConversationHandler.END


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text(
        "Buyurtma bekor qilindi.\n/start - qayta boshlash uchun",
        reply_markup=ReplyKeyboardRemove(),
    )
    return ConversationHandler.END


def main() -> None:
    app = Application.builder().token(BOT_TOKEN).build()

    conv = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            CHOOSE_TYPE:       [MessageHandler(filters.TEXT & ~filters.COMMAND, choose_type)],
            GET_SIZE:          [MessageHandler(filters.TEXT & ~filters.COMMAND, get_size)],
            CHOOSE_ODIYOL_SIZE:[MessageHandler(filters.TEXT & ~filters.COMMAND, choose_odiyol_size)],
            GET_LOCATION:      [MessageHandler(filters.LOCATION, get_location)],
            CHOOSE_DELIVERY:   [MessageHandler(filters.TEXT & ~filters.COMMAND, choose_delivery)],
            GET_CONTACT:       [MessageHandler((filters.CONTACT | (filters.TEXT & ~filters.COMMAND)), get_contact)],
            GET_NAME:          [MessageHandler(filters.TEXT & ~filters.COMMAND, get_name)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    app.add_handler(conv)

    print("Bot ishga tushdi...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
