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
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(BASE_DIR, ".env"))
TOKEN = os.getenv("TELEGRAM_TOKEN")

user_state = {}

async def error_handler(update, context: ContextTypes.DEFAULT_TYPE):
    print(f"Exception: {context.error}")

async def articles(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "<b>📘 Означені артиклі (der, die, das)</b>\n\n"
        "<pre>"
        "          | m   | f   | n   | pl  \n"
        "----------+-----+-----+-----+-----\n"
        "Nominativ | der | die | das | die \n"
        "Akkusativ | den | die | das | die \n"
        "Dativ     | dem | der | dem | den \n"
        "Genitiv   | des | der | des | der \n"
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
        
def get_filtered_questions(cases, genders, limit: int = 5):
    try:
        with open("deutch_articles.json", "r", encoding="utf-8") as f:
            all_questions = json.load(f)
    except Exception as e:
        print(f"Помилка при завантаженні запитань: {e}")
        return []

    filtered = [
        q for q in all_questions
        if q.get("case") in cases and q.get("gender") in genders
    ]
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
        s["total"] = total
        s["points"] = s["ok"]
        s["percent"] = round((s["ok"] / total) * 100, 2) if total > 0 else 0

    # Один бал нараховується за кожну правильну відповідь.
    sorted_scores = sorted(
        scores.values(),
        key=lambda x: (x["points"], x["percent"]),
        reverse=True
    )
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
            "⚙️ Використання: /select <відмінки через кому> <роди через кому>\n"
            "Наприклад: /select Nominativ,Akkusativ masculine,feminine\n\n"
            "Відмінки: Nominativ, Akkusativ, Dativ, Genitiv\n"
            "Роди: masculine, feminine, neuter, plural"
        )
        return

    cases = list(dict.fromkeys(args[0].split(",")))
    genders = list(dict.fromkeys(args[1].split(",")))
    valid_cases = {"Nominativ", "Akkusativ", "Dativ", "Genitiv"}
    valid_genders = {"masculine", "feminine", "neuter", "plural"}
    if not set(cases) <= valid_cases or not set(genders) <= valid_genders:
        await update.message.reply_text("⚠️ Перевір відмінки та роди у списку доступних значень.")
        return

    selected = get_filtered_questions(cases, genders)
    if not selected:
        await update.message.reply_text("⚠️ Для такого вибору немає завдань.")
        return
    user_id = update.effective_user.id
    user_state[user_id] = {'index': 0, 'quiz': selected}

    await update.message.reply_text(
        f"🔎 Обрано {len(selected)} завдань для {', '.join(cases)} / {', '.join(genders)}. Починаємо!"
    )
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
        text += f"{i}. 👤 {entry['name']} — {entry['points']} балів ({entry['percent']}%, {entry['total']} вправ)\n"
    await update.message.reply_text(text)

user_selection = {}  # тимчасове збереження вибору
AVAILABLE_CASES = ["Nominativ", "Akkusativ", "Dativ", "Genitiv"]
AVAILABLE_GENDERS = ["masculine", "feminine", "neuter", "plural"]

def get_selection_keyboard(items, selected, callback_prefix, done_callback, done_text):
    keyboard = [
        [InlineKeyboardButton(
            f"{'✅ ' if item in selected else ''}{item}",
            callback_data=f"{callback_prefix}{item}"
        )]
        for item in items
    ]
    if selected:
        keyboard.append([InlineKeyboardButton(done_text, callback_data=done_callback)])
    return InlineKeyboardMarkup(keyboard)

async def handle_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    data = query.data

    # --- Багатовибір відмінків ---
    if data.startswith("choose_case_"):
        case = data.replace("choose_case_", "")
        selection = user_selection.setdefault(user_id, {"cases": set(), "genders": set()})
        if case in selection["cases"]:
            selection["cases"].remove(case)
        else:
            selection["cases"].add(case)
        selected_cases = [item for item in AVAILABLE_CASES if item in selection["cases"]]
        await query.edit_message_text(
            f"🔘 Обери один або кілька відмінків:\nОбрано: {', '.join(selected_cases) or 'нічого'}",
            reply_markup=get_selection_keyboard(
                AVAILABLE_CASES, selection["cases"], "choose_case_", "choose_cases_done", "Далі: обрати роди"
            )
        )
        return

    elif data == "choose_cases_done":
        selection = user_selection.get(user_id)
        if not selection or not selection["cases"]:
            await query.edit_message_text("⚠️ Обери хоча б один відмінок.")
            return
        await query.edit_message_text(
            "🔘 Обери один або кілька родів:\nОбрано: нічого",
            reply_markup=get_selection_keyboard(
                AVAILABLE_GENDERS, selection["genders"], "choose_gender_", "choose_genders_done", "Почати тест"
            )
        )
        return

    # --- Багатовибір родів ---
    elif data.startswith("choose_gender_"):
        gender = data.replace("choose_gender_", "")
        if user_id not in user_selection or not user_selection[user_id]["cases"]:
            await query.edit_message_text("⚠️ Спочатку обери відмінок.")
            return
        selection = user_selection[user_id]
        if gender in selection["genders"]:
            selection["genders"].remove(gender)
        else:
            selection["genders"].add(gender)
        selected_genders = [item for item in AVAILABLE_GENDERS if item in selection["genders"]]
        await query.edit_message_text(
            f"🔘 Обери один або кілька родів:\nОбрано: {', '.join(selected_genders) or 'нічого'}",
            reply_markup=get_selection_keyboard(
                AVAILABLE_GENDERS, selection["genders"], "choose_gender_", "choose_genders_done", "Почати тест"
            )
        )
        return

    elif data == "choose_genders_done":
        selection = user_selection.get(user_id)
        if not selection or not selection["genders"]:
            await query.edit_message_text("⚠️ Обери хоча б один рід.")
            return
        cases = [item for item in AVAILABLE_CASES if item in selection["cases"]]
        genders = [item for item in AVAILABLE_GENDERS if item in selection["genders"]]
        selected = get_filtered_questions(cases, genders)
        if not selected:
            await query.edit_message_text("⚠️ Для такого вибору немає завдань.")
            return
        user_state[user_id] = {'index': 0, 'quiz': selected}
        await query.edit_message_text(
            f"🔎 Обрано {len(selected)} завдань для {', '.join(cases)} / {', '.join(genders)}. Починаємо!"
        )
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
            text += f"{i}. 👤 {entry['name']} — {entry['points']} балів ({entry['percent']}%, {entry['total']} вправ)\n"
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
        user_selection[user_id] = {"cases": set(), "genders": set()}
        await query.edit_message_text(
            "🔘 Обери один або кілька відмінків:\nОбрано: нічого",
            reply_markup=get_selection_keyboard(
                AVAILABLE_CASES, set(), "choose_case_", "choose_cases_done", "Далі: обрати роди"
            )
        )
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
            "⚙️ <b>/select Akkusativ masculine,feminine</b> — обрати кілька значень\n"
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
    user_selection[update.effective_user.id] = {"cases": set(), "genders": set()}
    await update.message.reply_text(
        "🔘 Обери один або кілька відмінків:\nОбрано: нічого",
        reply_markup=get_selection_keyboard(
            AVAILABLE_CASES, set(), "choose_case_", "choose_cases_done", "Далі: обрати роди"
        )
    )
    
def main():
    if not TOKEN:
        raise ValueError("Токен бота не знайдено! Встанови TELEGRAM_TOKEN у середовищі або у файлі .env.")

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