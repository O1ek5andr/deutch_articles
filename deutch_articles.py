import os
import json, datetime, random
from dotenv import load_dotenv
from telegram import Update, ReplyKeyboardMarkup, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.error import BadRequest
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    ContextTypes, CallbackQueryHandler, filters
)
from utils import safe_edit_message_text

# Завантажуємо змінні з .env
load_dotenv()
TOKEN = os.getenv("TELEGRAM_TOKEN")

user_state = {}

async def error_handler(update, context: ContextTypes.DEFAULT_TYPE):
    print(f"Exception: {context.error}")

async def articles(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "<b>📘 Означені артиклі (der, die, das)</b>\n\n"
        "<pre>"
        "          | m     | f     | n     | pl       \n"
        "----------+-------+-------+-------+-------\n"
        "Nominativ | der   | die   | das   | die      \n"
        "Akkusativ | den   | die   | das   | die      \n"
        "Dativ     | dem   | der   | dem   | den      \n"
        "Genitiv   | des   | der   | des   | der      \n"
        "</pre>\n"
        "<b>📗 Неозначені артиклі (ein, eine)</b>\n\n"
        "<pre>"
        "          | m     | f     | n     \n"
        "----------+-------+-------+-------\n"
        "Nominativ | ein   | eine  | ein   \n"
        "Akkusativ | einen | eine  | ein   \n"
        "Dativ     | einem | einer | einem \n"
        "Genitiv   | eines | einer | eines \n"
        "</pre>\n"
        "ℹ️ У множині неозначені артиклі не вживаються."
    )

    if update.message:
        await update.message.reply_text(text, parse_mode="HTML", reply_markup=get_result_keyboard())
    elif update.callback_query:
        await update.callback_query.message.reply_text(text, parse_mode="HTML", reply_markup=get_result_keyboard())
        
def get_filtered_questions(case: str, gender: str, limit: int = 5):
    try:
        with open("deutch_articles.json", "r", encoding="utf-8") as f:
            all_questions = json.load(f)
    except Exception as e:
        print(f"Помилка при завантаженні запитань: {e}")
        return []

    filtered = [q for q in all_questions if q.get("case") == case and q.get("gender") == gender]
    return random.sample(filtered, min(limit, len(filtered)))

def get_result_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📊 Моя статистика", callback_data="my_stats")],
        [InlineKeyboardButton("🏆 Таблиця лідерів", callback_data="leaderboard")],
        [InlineKeyboardButton("🔁 Пройти ще раз", callback_data="restart")],
        [InlineKeyboardButton("🧠 Обрати відмінок і рід", callback_data="choose_start")],
        [InlineKeyboardButton("📚 Артиклі", callback_data="show_articles")],
        [InlineKeyboardButton("🏠 Головне меню", callback_data="main_menu")],
        [InlineKeyboardButton("❓ Допомога", callback_data="help")]
    ])

# --- Функція логування ---
def log_result(user_id, username, first_name, question, user_answer, correct_answer, is_correct):
    log_entry = {
        "time": datetime.datetime.now().isoformat(timespec="seconds"),
        "user_id": user_id,
        "username": username,
        "first_name": first_name,
        "question": question,
        "answer": user_answer,
        "correct": correct_answer,
        "result": "OK" if is_correct else "FAIL"
    }

    if os.path.exists("results.json"):
        with open("results.json", "r", encoding="utf-8") as f:
            data = json.load(f)
    else:
        data = []

    data.append(log_entry)

    with open("results.json", "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

# --- Функція статистики ---
def get_user_stats(user_id):
    if not os.path.exists("results.json"):
        return {"OK": 0, "FAIL": 0, "PERCENT": 0}

    with open("results.json", "r", encoding="utf-8") as f:
        data = json.load(f)

    ok = sum(1 for entry in data if entry["user_id"] == user_id and entry["result"] == "OK")
    fail = sum(1 for entry in data if entry["user_id"] == user_id and entry["result"] == "FAIL")
    total = ok + fail
    percent = round((ok / total) * 100, 2) if total > 0 else 0

    return {"OK": ok, "FAIL": fail, "PERCENT": percent}

# --- Функція лідерборду ---
def get_leaderboard(top_n=5):
    if not os.path.exists("results.json"):
        return []

    with open("results.json", "r", encoding="utf-8") as f:
        data = json.load(f)

    scores = {}
    for entry in data:
        uid = entry["user_id"]
        name = entry.get("username") or entry.get("first_name") or str(uid)
        if uid not in scores:
            scores[uid] = {"name": name, "ok": 0, "fail": 0}
        if entry["result"] == "OK":
            scores[uid]["ok"] += 1
        else:
            scores[uid]["fail"] += 1

    for uid, s in scores.items():
        total = s["ok"] + s["fail"]
        s["percent"] = round((s["ok"] / total) * 100, 2) if total > 0 else 0

    # 🔽 Сортування за відсотком правильних відповідей
    sorted_scores = sorted(scores.values(), key=lambda x: x["percent"], reverse=True)
    return sorted_scores[:top_n]

# --- Хендлери ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    with open("deutch_articles.json", "r", encoding="utf-8") as f:
        all_questions = json.load(f)

    selected = random.sample(all_questions, 5)
    user_state[user_id] = {'index': 0, 'quiz': selected}

    await update.message.reply_text("🔎 Починаємо новий тест із 5 випадкових завдань!")
    await send_question(update, context)

async def select(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args
    if len(args) != 2:
        await update.message.reply_text(
            "⚙️ Використання: /select <Відмінок> <Рід>\n"
            "Наприклад: /select Akkusativ masculine\n\n"
            "Відмінки: Nominativ, Akkusativ, Dativ, Genitiv\n"
            "Роди: masculine, feminine, neuter, plural"
        )
        return

    case, gender = args[0], args[1]

    selected = get_filtered_questions(case, gender)
    user_id = update.effective_user.id
    user_state[user_id] = {'index': 0, 'quiz': selected}

    await update.message.reply_text(f"🔎 Обрано 5 завдань для {case} {gender}. Починаємо!")
    await send_question(update, context)

async def send_question(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    state = user_state.get(user_id)
    if not state:
        await update.message.reply_text("⚠️ Спочатку запусти тест командою /start або /select.")
        return

    index = state['index']
    quiz = state['quiz']

    if index >= len(quiz):
        keyboard = get_result_keyboard()
        if update.message:
            await update.message.reply_text("✅ Тест завершено! Молодець!\nОберіть дію:", reply_markup=keyboard)
        elif update.callback_query:
            await update.callback_query.message.reply_text("✅ Тест завершено! Молодець!\nОберіть дію:", reply_markup=keyboard)
        return

    q = quiz[index]
    options = [[opt] for opt in q['options']]
    markup = ReplyKeyboardMarkup(options, one_time_keyboard=True, resize_keyboard=True)

    if update.message:
        await update.message.reply_text(q['question'], reply_markup=markup)
    elif update.callback_query:
        await update.callback_query.message.reply_text(q['question'], reply_markup=markup)

async def handle_answer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_id = user.id
    username = user.username
    first_name = user.first_name

    state = user_state.get(user_id)
    if not state:
        await update.message.reply_text("Напиши /start щоб почати тест.")
        return

    quiz = state['quiz']
    index = state['index']
    q = quiz[index]

    user_answer = update.message.text.strip()
    correct = q['options'][q['answer'][0]]
    is_correct = (user_answer == correct)

    if is_correct:
        await update.message.reply_text("✅ Правильно!\n" + q['explanation'])
    else:
        await update.message.reply_text(f"❌ Неправильно.\nПравильна відповідь: {correct}\n" + q['explanation'])

    log_result(user_id, username, first_name, q['question'], user_answer, correct, is_correct)

    state['index'] += 1
    await send_question(update, context)

async def leaderboard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    leaders = get_leaderboard()
    if not leaders:
        await update.message.reply_text("Поки що немає результатів.")
        return

    text = "🏆 Лідерборд:\n"
    for i, entry in enumerate(leaders, start=1):
        text += f"{i}. 👤 {entry['name']} — {entry['ok']} правильних ({entry['percent']}%)\n"
    await update.message.reply_text(text)

user_selection = {}  # тимчасове збереження вибору

async def handle_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    data = query.data

    # --- Вибір відмінка ---
    if data.startswith("choose_case_"):
        case = data.replace("choose_case_", "")
        user_selection[user_id] = {"case": case}
        genders = ["masculine", "feminine", "neuter", "plural"]
        keyboard = [[InlineKeyboardButton(g, callback_data=f"choose_gender_{g}")] for g in genders]
        await query.edit_message_text(f"📌 Обрано відмінок: {case}\n🔘 Тепер обери рід:", reply_markup=InlineKeyboardMarkup(keyboard))
        return

    # --- Вибір роду + запуск тесту ---
    elif data.startswith("choose_gender_"):
        gender = data.replace("choose_gender_", "")
        if user_id not in user_selection or "case" not in user_selection[user_id]:
            await query.edit_message_text("⚠️ Спочатку обери відмінок.")
            return

        case = user_selection[user_id]["case"]
        user_selection[user_id]["gender"] = gender

        selected = get_filtered_questions(case, gender)

        user_state[user_id] = {'index': 0, 'quiz': selected}
        await query.edit_message_text(f"🔎 Обрано 5 завдань для {case} {gender}. Починаємо!")
        await send_question(update, context)
        return

    # --- Статистика / Лідерборд / Рестарт ---
    elif data == "my_stats":
        stats = get_user_stats(user_id)
        await query.edit_message_text(
            f"📊 Твоя статистика:\n"
            f"✅ Правильних: {stats['OK']}\n"
            f"❌ Неправильних: {stats['FAIL']}\n"
            f"📈 Успішність: {stats['PERCENT']}%",
            reply_markup=get_result_keyboard()
        )
        return

    elif data == "leaderboard":
        leaders = get_leaderboard()
        if not leaders:
            await query.edit_message_text("Поки що немає результатів.", reply_markup=get_result_keyboard())
            return

        text = "🏆 Лідерборд:\n"
        for i, entry in enumerate(leaders, start=1):
            text += f"{i}. 👤 {entry['name']} — {entry['ok']} правильних ({entry['percent']}%)\n"
        await safe_edit_message_text(query, text, get_result_keyboard())

        return

    elif data == "restart":
        with open("deutch_articles.json", "r", encoding="utf-8") as f:
            all_questions = json.load(f)
        selected = random.sample(all_questions, 5)
        user_state[user_id] = {'index': 0, 'quiz': selected}
        await query.edit_message_text("🔁 Починаємо тест заново!")
        await send_question(update, context)
        return
    elif data == "choose_start":
        cases = ["Nominativ", "Akkusativ", "Dativ", "Genitiv"]
        keyboard = [[InlineKeyboardButton(case, callback_data=f"choose_case_{case}")] for case in cases]
        await query.edit_message_text("🔘 Обери відмінок:", reply_markup=InlineKeyboardMarkup(keyboard))
        return
    elif data == "main_menu":
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🧠 Обрати відмінок і рід", callback_data="choose_start")],
            [InlineKeyboardButton("🎲 Пройти випадковий тест", callback_data="restart")],
            [InlineKeyboardButton("📊 Моя статистика", callback_data="my_stats")],
            [InlineKeyboardButton("🏆 Таблиця лідерів", callback_data="leaderboard")]
        ])
        await query.edit_message_text("🏠 Головне меню:\nОберіть дію:", reply_markup=keyboard)
        return
    elif data == "help":
        help_text = (
            "❓ <b>Допомога по боту</b>\n\n"
            "🧠 <b>/choose</b> — обрати граматичну комбінацію (відмінок + рід)\n"
            "🎲 <b>/start</b> — пройти випадковий тест із 5 завдань\n"
            "⚙️ <b>/select Akkusativ masculine</b> — вручну задати комбінацію\n"
            "📊 <b>/stats</b> — переглянути свою статистику\n"
            "🏆 <b>/leaderboard</b> — топ користувачів за точністю\n\n"
            "✅ Після кожного тесту ти побачиш кнопки для повтору, перегляду результатів або вибору нової теми."
        )
        await query.edit_message_text(help_text, reply_markup=get_result_keyboard(), parse_mode="HTML")
        return
    elif data == "show_articles":
        await articles(update, context)
        return

async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    stats = get_user_stats(user_id)
    await update.message.reply_text(
        f"📊 Твоя статистика:\n"
        f"✅ Правильних: {stats['OK']}\n"
        f"❌ Неправильних: {stats['FAIL']}\n"
        f"📈 Успішність: {stats['PERCENT']}%"
    )
    
async def choose(update: Update, context: ContextTypes.DEFAULT_TYPE):
    cases = ["Nominativ", "Akkusativ", "Dativ", "Genitiv"]
    keyboard = [[InlineKeyboardButton(case, callback_data=f"choose_case_{case}")] for case in cases]
    await update.message.reply_text("🔘 Обери відмінок:", reply_markup=InlineKeyboardMarkup(keyboard))
    
def main():
    print(">>> main() стартував")
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_error_handler(error_handler)
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("stats", stats))
    app.add_handler(CommandHandler("leaderboard", leaderboard))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_answer))
    app.add_handler(CallbackQueryHandler(handle_buttons))
    app.add_handler(CommandHandler("select", select))
    app.add_handler(CommandHandler("choose", choose))
    app.add_handler(CommandHandler("articles", articles))
    print("Бот запущено. Очікуємо повідомлень...")
    app.run_polling()

if __name__ == '__main__':
    main()