from telegram import InlineKeyboardMarkup
from telegram.error import BadRequest

async def safe_edit_message_text(query, new_text: str, new_markup: InlineKeyboardMarkup = None):
    old_text = query.message.text
    old_markup = query.message.reply_markup

    if old_text == new_text and old_markup == new_markup:
        return  # нічого не змінюємо

    try:
        await query.edit_message_text(text=new_text, reply_markup=new_markup)
    except BadRequest as e:
        if "Message is not modified" in str(e):
            pass
        else:
            raise