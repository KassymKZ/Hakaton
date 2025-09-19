import requests
import telebot
from telebot import types
import logging
from datetime import datetime

logging.basicConfig(level=logging.INFO)

bot = telebot.TeleBot('7567419832:AAGv0eE9K7bAuOMMzv_F8SskyAb4Qcj-tG0')
ADMIN_GROUP_ID = "-4940285744"
ADMIN_IDS = [824360574]

# Временное хранилище для данных пользователей
user_sessions = {}

def create_category_menu():
    """Создает меню с категориями проблем в одну колонку"""
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(types.InlineKeyboardButton("💰 Финансовые проблемы", callback_data="finance"))
    markup.add(types.InlineKeyboardButton("📚 Учебные трудности", callback_data="study"))
    markup.add(types.InlineKeyboardButton("😰 Социальные страхи", callback_data="social"))
    markup.add(types.InlineKeyboardButton("👨‍👩‍👧‍👦 Семья и окружение", callback_data="family"))
    markup.add(types.InlineKeyboardButton("🏠 Бытовые проблемы", callback_data="household"))
    markup.add(types.InlineKeyboardButton("🎯 Профориентация", callback_data="career"))
    return markup

def get_user_info(user):
    """Собирает информацию о пользователе"""
    full_name = user.first_name or ""
    if user.last_name:
        full_name += f" {user.last_name}"
    
    username = f"@{user.username}" if user.username else "Не указан"
    
    return {
        'full_name': full_name,
        'username': username,
        'user_id': user.id,
        'timestamp': datetime.now().strftime("%d.%m.%Y %H:%M")
    }

def send_admin_report(user_info, question, bot_answer, category=None):
    """Отправляет структурированный отчет в админскую группу"""
    try:
        category_names = {
            'finance': '💰 Финансовые проблемы',
            'study': '📚 Учебные трудности',
            'social': '😰 Социальные страхи',
            'family': '👨‍👩‍👧‍👦 Семья и окружение',
            'household': '🏠 Бытовые проблемы',
            'career': '🎯 Профориентация'
        }
        
        category_text = category_names.get(category, 'Общий вопрос') if category else 'Общий вопрос'
        
        report = f"""
📋 ОТЧЕТ О ДИАЛОГЕ

👤 От: {user_info['full_name']}
📞 Username: {user_info['username']}
🆔 ID пользователя: {user_info['user_id']}
📂 Категория: {category_text}
🕐 Время: {user_info['timestamp']}

❓ Вопрос пользователя:
{question}

🤖 Ответ бота:
{bot_answer[:1000]}{'...' if len(bot_answer) > 1000 else ''}

━━━━━━━━━━━━━━━━━━
"""
        
        bot.send_message(ADMIN_GROUP_ID, report)
        
    except Exception as e:
        logging.error(f"Ошибка отправки отчета админам: {e}")

@bot.message_handler(commands=['start', 'menu', 'categories'])
def show_categories(message):
    """Показывает категории проблем"""
    markup = create_category_menu()
    text = """Выберите категорию, которая лучше всего описывает вашу ситуацию:

Я помогу вам найти подходящие решения и рекомендации."""
    
    bot.reply_to(message, text, reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == "back_to_menu")
def back_to_menu(call):
    bot.answer_callback_query(call.id)
    markup = create_category_menu()
    bot.edit_message_text(
        "Выберите категорию проблемы:",
        call.message.chat.id,
        call.message.message_id,
        reply_markup=markup
    )

@bot.callback_query_handler(func=lambda call: True)
def handle_category_selection(call):
    """Обработка выбора категории"""
    bot.answer_callback_query(call.id)
    
    if call.data == "back_to_menu":
        back_to_menu(call)
        return
    
    # Соответствие кнопок и сообщений для классификатора
    category_messages = {
        "finance": "У меня финансовые проблемы с деньгами и стипендией",
        "study": "У меня учебные трудности и проблемы с экзаменами", 
        "social": "У меня социальные страхи и проблемы с общением",
        "family": "У меня проблемы с семьей и окружением",
        "household": "У меня бытовые проблемы и вопросы здоровья",
        "career": "У меня вопросы по профориентации и выбору карьеры"
    }
    
    category_names = {
        "finance": "Финансовые проблемы",
        "study": "Учебные трудности",
        "social": "Социальные страхи", 
        "family": "Семья и окружение",
        "household": "Бытовые проблемы",
        "career": "Профориентация"
    }
    
    if call.data in category_messages:
        # Сохраняем информацию о пользователе и выбранной категории
        user_info = get_user_info(call.from_user)
        user_sessions[call.from_user.id] = {
            'user_info': user_info,
            'category': call.data,
            'question': category_messages[call.data]
        }
        
        bot.edit_message_text(
            f"Вы выбрали: {category_names[call.data]}\n\nОбрабатываю ваш запрос...",
            call.message.chat.id,
            call.message.message_id
        )
        
        # Отправляем в shai.pro
        send_to_shai_pro(category_messages[call.data], call.from_user, call.message.chat, call.data)

def send_to_shai_pro(text, user, chat, category=None):
    """Отправляет запрос в shai.pro"""
    
    headers = {
        'Authorization': 'Bearer app-LqQKmr2WcmFUTAjZk2adM46j',
        'Content-Type': 'application/json'
    }
    
    data = {
        'inputs': {},
        'query': text,
        'response_mode': 'blocking',
        'user': str(user.id)
    }
    
    try:
        response = requests.post('https://hackathon.shai.pro/v1/chat-messages', 
                               json=data, headers=headers, timeout=30)
        
        if response.status_code == 200:
            result = response.json()
            answer = result.get('answer', '')
            
            if not answer or answer.strip() == '':
                answer = "Извините, не смог сформировать ответ. Попробуйте переформулировать вопрос."
            
            if len(answer) > 4096:
                answer = answer[:4090] + "..."
            
            # Добавляем кнопку возврата к меню
            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton("📋 Выбрать другую категорию", callback_data="back_to_menu"))
            
            bot.send_message(chat.id, answer, reply_markup=markup)
            
            # Отправляем структурированный отчет админам
            if user.id in user_sessions:
                session_data = user_sessions[user.id]
                send_admin_report(
                    session_data['user_info'],
                    text,
                    answer,
                    category
                )
                # Очищаем сессию
                del user_sessions[user.id]
                
        else:
            bot.send_message(chat.id, f"Произошла ошибка обработки запроса. Код: {response.status_code}")
            
    except requests.Timeout:
        bot.send_message(chat.id, "Превышено время ожидания ответа. Попробуйте еще раз.")
    except Exception as e:
        logging.error(f"Ошибка запроса: {e}")
        bot.send_message(chat.id, "Произошла техническая ошибка. Попробуйте позже.")

@bot.message_handler(func=lambda message: True)
def handle_message(message):
    """Основная обработка сообщений"""
    
    if message.text.startswith('/menu') or message.text.startswith('/start') or message.text.startswith('/categories'):
        return
    
    # Сохраняем информацию о пользователе для прямых сообщений
    user_info = get_user_info(message.from_user)
    user_sessions[message.from_user.id] = {
        'user_info': user_info,
        'category': None,
        'question': message.text
    }
    
    send_to_shai_pro(message.text, message.from_user, message.chat)

bot.polling()