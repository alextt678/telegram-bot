import telebot
import threading
import time
import random
import re
from collections import deque
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

# Токен и имя владельца (без @)
TOKEN = "8033395300:AAE6B8CMpSEWZH5l5Q759-kWZNsySefrxEU"
OWNER_USERNAME = "JDD452"

bot = telebot.TeleBot(TOKEN, parse_mode="HTML")

ready = False
time_stopped = False
lock = threading.Lock()

user_gif_file_ids = {}
temp_gif_waiting = {}

body_parts = [
    "голову",
    "глаз",
    "руку",
    "ногу",
    "жопу",
    "1488 атом правовой пятки",
    "святой волос на подмышке"
]

recent_messages = {}
MAX_CACHE_SIZE = 50

def cache_bot_message(chat_id, message):
    if chat_id not in recent_messages:
        recent_messages[chat_id] = deque(maxlen=MAX_CACHE_SIZE)
    recent_messages[chat_id].append(message.message_id)

def delete_messages_later(chat_id, message_ids, username):
    time.sleep(10)
    for msg_id in message_ids:
        try:
            bot.delete_message(chat_id, msg_id)
        except Exception:
            pass
    bot.send_message(chat_id, f"@{username} избит стендом Star Platinum")

# --------- RPS GAME SECTION ---------
pending_rps = {}
active_rps_matches = {}
RPS_ROUNDS = 5
rps_losses = [
    "способность дрочить",
    "способность мыслить",
    "девственность",
    "икону правой святой пятки",
    "душу Олега"
]
rps_message_ids = {} # chat_id -> [message_id, ...]
rps_ban_state = {}   # chat_id -> { 'loser_id':..., 'endtime':..., 'ban_type':... }

BAN_TYPES = ["text", "photo", "sticker", "audio", "voice", "video", "animation", "document"]

def clear_rps_messages(chat_id):
    ids = rps_message_ids.get(chat_id, [])
    for mid in ids:
        try:
            bot.delete_message(chat_id, mid)
        except Exception:
            pass
    rps_message_ids[chat_id] = []

@bot.message_handler(func=lambda m: re.match(r'^вызываю\s+@\w+\s+на игру камень ножницы бумага', m.text.lower()))
def rps_challenge(message):
    match = re.match(r'^вызываю\s+@(\w+)\s+на игру камень ножницы бумага', message.text.lower())
    if not match:
        return
    opponent_username = match.group(1)
    chat_id = message.chat.id
    challenger = message.from_user
    if chat_id in pending_rps or chat_id in active_rps_matches:
        bot.reply_to(message, "Дуэль уже запущена!")
        return
    markup = InlineKeyboardMarkup()
    markup.add(
        InlineKeyboardButton("Да", callback_data=f"rps_accept_{challenger.id}"),
        InlineKeyboardButton("Нет", callback_data=f"rps_decline_{challenger.id}"),
    )
    msg = bot.send_message(
        chat_id,
        f"@{opponent_username}, принимаешь вызов от @{challenger.username}?",
        reply_markup=markup
    )
    rps_message_ids[chat_id] = [msg.message_id]
    pending_rps[chat_id] = {'challenger_id': challenger.id, 'challenger_username': challenger.username, 'opponent_username': opponent_username}

@bot.callback_query_handler(func=lambda call: call.data.startswith("rps_accept_") or call.data.startswith("rps_decline_"))
def rps_accept_decline(call):
    chat_id = call.message.chat.id
    user = call.from_user
    state = pending_rps.get(chat_id)
    if not state:
        return
    if user.username is None or user.username.lower() != state['opponent_username'].lower():
        return # Игнор чужих нажатий
    clear_rps_messages(chat_id)
    if call.data.startswith("rps_accept_"):
        msg = bot.send_message(chat_id, f"@{user.username} принял вызов от @{state['challenger_username']}! Дуэль из 5 раундов!")
        rps_message_ids[chat_id].append(msg.message_id)
        challenger_id = state['challenger_id']
        opponent_id = user.id
        active_rps_matches[chat_id] = {
            'player1': challenger_id,
            'username1': state['challenger_username'],
            'player2': opponent_id,
            'username2': state['opponent_username'],
            'score1': 0, 'score2': 0,
            'moves': {},
            'round': 1
        }
        show_rps_buttons(chat_id, challenger_id)
        show_rps_buttons(chat_id, opponent_id)
    else:
        msg = bot.send_message(chat_id, f"Хорошо, пупсик, в другой раз!")
        rps_message_ids[chat_id].append(msg.message_id)
    pending_rps.pop(chat_id, None)

def show_rps_buttons(chat_id, user_id):
    markup = InlineKeyboardMarkup(row_width=3)
    markup.add(
        InlineKeyboardButton("🪨 Камень", callback_data=f"rpsmove_rock_{user_id}"),
        InlineKeyboardButton("✂️ Ножницы", callback_data=f"rpsmove_scissors_{user_id}"),
        InlineKeyboardButton("📄 Бумага", callback_data=f"rpsmove_paper_{user_id}"),
    )
    msg = bot.send_message(
        chat_id, 
        f"<b>Раунд!</b> {active_rps_matches[chat_id]['round']} / {RPS_ROUNDS}\n"
        f"<a href='tg://user?id={user_id}'>Твой ход</a>:", 
        reply_markup=markup
    )
    if chat_id not in rps_message_ids:
        rps_message_ids[chat_id] = []
    rps_message_ids[chat_id].append(msg.message_id)

@bot.callback_query_handler(func=lambda call: call.data.startswith("rpsmove_"))
def rps_move(call):
    chat_id = call.message.chat.id
    game = active_rps_matches.get(chat_id)
    if not game:
        return
    arr = call.data.split("_")
    move = arr[1]
    user_id = int(arr[2])
    if call.from_user.id != user_id:
        return
    if user_id not in [game['player1'], game['player2']]:
        return
    if user_id in game['moves']:
        bot.answer_callback_query(call.id, f"Ты уже сделал ход!")
        return
    game['moves'][user_id] = move
    try:
        bot.edit_message_reply_markup(chat_id, call.message.message_id, reply_markup=None)
    except Exception:
        pass
    bot.answer_callback_query(call.id, f"Ход выбран!")
    if len(game['moves']) == 2:
        resolve_rps_round(chat_id)

def resolve_rps_round(chat_id):
    clear_rps_messages(chat_id)
    game = active_rps_matches[chat_id]
    p1, u1 = game['player1'], game['username1']
    p2, u2 = game['player2'], game['username2']
    m1 = game['moves'][p1]
    m2 = game['moves'][p2]
    result_str = f"@{u1}: {display_rps(m1)}\n@{u2}: {display_rps(m2)}\n"
    winner = determine_rps_winner(m1, m2)
    if winner == 0:
        result_str += "<b>Ничья!</b>"
    elif winner == 1:
        game['score1'] += 1
        result_str += f"<b>Раунд за @{u1}!</b> (счёт: {game['score1']}-{game['score2']})"
    else:
        game['score2'] += 1
        result_str += f"<b>Раунд за @{u2}!</b> (счёт: {game['score1']}-{game['score2']})"
    msg = bot.send_message(chat_id, f"Раунд {game['round']}/{RPS_ROUNDS}\n" + result_str)
    rps_message_ids[chat_id] = [msg.message_id]
    game['moves'] = {}
    game['round'] += 1
    if game['round'] > RPS_ROUNDS:
        finish_rps_match(chat_id)
    else:
        show_rps_buttons(chat_id, p1)
        show_rps_buttons(chat_id, p2)

def display_rps(code):
    return {"rock": "🪨 Камень", "scissors": "✂️ Ножницы", "paper": "📄 Бумага"}.get(code, code)

def determine_rps_winner(m1, m2):
    if m1 == m2:
        return 0
    wins = {"rock": "scissors", "scissors": "paper", "paper": "rock"}
    if wins[m1] == m2:
        return 1
    else:
        return 2

def finish_rps_match(chat_id):
    clear_rps_messages(chat_id)
    game = active_rps_matches[chat_id]
    p1, u1 = game['player1'], game['username1']
    p2, u2 = game['player2'], game['username2']
    s1, s2 = game['score1'], game['score2']
    if s1 > s2:
        loser_id = p2
        loser_username = u2
        winner = u1
    elif s2 > s1:
        loser_id = p1
        loser_username = u1
        winner = u2
    else:
        bot.send_message(chat_id, f"Ничья! Итоговый счёт: {s1}-{s2}")
        active_rps_matches.pop(chat_id, None)
        return

    ban_type = random.choice(BAN_TYPES)
    loss = random.choice(rps_losses)
    bot.send_message(chat_id, f"Матч окончен! Победитель: @{winner}")
    bot.send_message(chat_id, f"@{loser_username} проиграл. В течение 5 минут все его сообщения типа <b>{ban_type}</b> будут удаляться!\n"
                              f"Стенд Star Platinum временно забрал у него <b>{loss}</b>!")

    rps_ban_state[chat_id] = {
        'loser_id': loser_id,
        'loser_username': loser_username,
        'endtime': time.time() + 300,
        'ban_type': ban_type,
        'loss': loss
    }

    def unban_rps():
        time.sleep(300)
        state = rps_ban_state.get(chat_id)
        if state:
            bot.send_message(chat_id,
                f'@{state["loser_username"]} пришёл в норму после того как стенд Starplatinum забрал у него <b>{state["loss"]}</b>!\nОграничение на <b>{state["ban_type"]}</b> сообщения снято.')
            rps_ban_state.pop(chat_id, None)
    threading.Thread(target=unban_rps).start()
    active_rps_matches.pop(chat_id, None)

# --- GIF в личке (handler-ы должны быть выше глобального handler-)
@bot.message_handler(func=lambda m: m.chat.type == 'private' and m.from_user and m.from_user.username == OWNER_USERNAME, content_types=['animation'])
def handle_gif_upload(message):
    file_id = message.animation.file_id
    temp_gif_waiting[message.chat.id] = file_id
    sent = bot.send_message(message.chat.id, "Получил гифку! Под каким номером её сохранить? (например, 1 или 2)")
    cache_bot_message(message.chat.id, sent)

@bot.message_handler(func=lambda m: m.chat.type == 'private' and m.from_user and m.from_user.username == OWNER_USERNAME, content_types=['text'])
def handle_gif_number(message):
    chat_id = message.chat.id
    if chat_id not in temp_gif_waiting:
        return
    text = message.text.strip()
    if text.isdigit():
        num = int(text)
        file_id = temp_gif_waiting.pop(chat_id)
        if message.from_user.id not in user_gif_file_ids:
            user_gif_file_ids[message.from_user.id] = {}
        user_gif_file_ids[message.from_user.id][num] = file_id
        sent = bot.send_message(chat_id, f"Гифка сохранена под номером {num}!")
        cache_bot_message(chat_id, sent)
    else:
        sent = bot.send_message(chat_id, "Пожалуйста, введите число (например, 1 или 2) для сохранения гифки.")
        cache_bot_message(chat_id, sent)

# --- ОТМЕНА только владельцем ---
@bot.message_handler(func=lambda m: m.text and m.text.lower().strip() == "отмена")
def rps_cancel(message):
    if not (message.from_user and message.from_user.username == OWNER_USERNAME):
        return
    chat_id = message.chat.id
    if chat_id in pending_rps:
        clear_rps_messages(chat_id)
        pending_rps.pop(chat_id, None)
        bot.send_message(chat_id, "Дуэль отменена.")
    elif chat_id in active_rps_matches:
        clear_rps_messages(chat_id)
        active_rps_matches.pop(chat_id, None)
        bot.send_message(chat_id, "Игра камень-ножницы-бумага отменена.")

# --- ОСНОВНОЙ ХЕНДЛЕР ---
@bot.message_handler(func=lambda m: True, content_types=[
    'text','sticker','photo','video','animation','audio','voice','document',
    'video_note','contact','location','venue','poll'
])
def main_handler(message):
    chat_id = message.chat.id
    user_id = message.from_user.id if message.from_user else None
    state = rps_ban_state.get(chat_id)
    if state and user_id == state['loser_id'] and time.time() < state['endtime']:
        ban_type = state['ban_type']
        if message.content_type == ban_type:
            try:
                bot.delete_message(chat_id, message.message_id)
            except Exception:
                pass
            return
    global ready, time_stopped
    if message.from_user is None or message.from_user.is_bot:
        return

    if chat_id not in recent_messages:
        recent_messages[chat_id] = deque(maxlen=MAX_CACHE_SIZE)
    recent_messages[chat_id].append(message.message_id)

    if message.chat.type in ['group', 'supergroup']:
        if message.from_user.username != OWNER_USERNAME:
            if time_stopped:
                try:
                    bot.delete_message(chat_id, message.message_id)
                except Exception as e:
                    pass
            return

    user = message.from_user
    text = message.text.lower().strip() if message.content_type == 'text' else ""

    if message.chat.type in ['group', 'supergroup'] and user.username == OWNER_USERNAME and text == "the hand":
        try:
            bot.delete_message(chat_id, message.message_id)
        except Exception:
            pass
        file_id = user_gif_file_ids.get(user.id, {}).get(2)
        if not file_id:
            sent = bot.send_message(chat_id, "Гифка номер 2 не найдена! Сначала отправьте её мне в ЛС.")
            cache_bot_message(chat_id, sent)
            return

        sent_gif = bot.send_animation(chat_id, file_id)
        cache_bot_message(chat_id, sent_gif)

        def delete_gif_later():
            time.sleep(1)
            try:
                bot.delete_message(chat_id, sent_gif.message_id)
            except Exception:
                pass
            msg_ids_to_delete = list(recent_messages.get(chat_id, []))[-15:]
            for msg_id in msg_ids_to_delete:
                try:
                    bot.delete_message(chat_id, msg_id)
                    time.sleep(0.1)
                except Exception:
                    pass
            sent = bot.send_message(chat_id, "пространство стёрто")
            cache_bot_message(chat_id, sent)

        threading.Thread(target=delete_gif_later).start()
        return

    if message.chat.type == 'private' and user.username == OWNER_USERNAME:
        return

    if user.username != OWNER_USERNAME:
        if time_stopped:
            try:
                bot.delete_message(chat_id, message.message_id)
            except Exception:
                pass
        return

    with lock:
        if not time_stopped:
            if text.startswith("starplatinum"):
                ready = True
                return

            if ready and text.startswith("the world"):
                ready = False
                time_stopped = True
                sent = bot.send_message(chat_id, "Time has stopped")
                cache_bot_message(chat_id, sent)

                def timer():
                    global time_stopped
                    time.sleep(25)
                    sent2 = bot.send_message(chat_id, "Time has resumed")
                    cache_bot_message(chat_id, sent2)
                    time_stopped = False

                threading.Thread(target=timer).start()
                return

        if message.reply_to_message and text == "ora":
            replied_user = message.reply_to_message.from_user
            username_to_mention = replied_user.username if replied_user.username else replied_user.first_name
            file_id = user_gif_file_ids.get(user.id, {}).get(1)
            if not file_id:
                sent = bot.send_message(chat_id, "GIF номер 1 не найдена! Отправьте её мне в личку перед использованием команды.")
                cache_bot_message(chat_id, sent)
                return
            sent_gif = bot.send_animation(chat_id, file_id)
            cache_bot_message(chat_id, sent_gif)
            sent_text = bot.send_message(chat_id, f"ORA ORA ORA ORA @{username_to_mention}")
            cache_bot_message(chat_id, sent_text)
            threading.Thread(target=delete_messages_later, args=(chat_id, [sent_gif.message_id, sent_text.message_id], username_to_mention)).start()
            return

        if message.reply_to_message and text == "star finger":
            replied_user = message.reply_to_message.from_user
            username_to_mention = replied_user.username if replied_user.username else replied_user.first_name
            try:
                bot.delete_message(chat_id, message.message_id)
            except Exception:
                pass
            part = random.choice(body_parts)
            sent = bot.send_message(chat_id, f"Star Platinum поразил: {part} у @{username_to_mention}")
            cache_bot_message(chat_id, sent)
            return

if __name__ == "__main__":
    print("Bot started")
    bot.infinity_polling()

