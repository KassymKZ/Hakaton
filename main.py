import requests
import telebot
from telebot import types
import logging

logging.basicConfig(level=logging.INFO)

bot = telebot.TeleBot('7567419832:AAGv0eE9K7bAuOMMzv_F8SskyAb4Qcj-tG0')
ADMIN_GROUP_ID = "-4940285744"
ADMIN_IDS = [824360574]

def create_category_menu():
    """Создает меню с категориями проблем"""
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("💰 Финансовые проблемы", callback_data="finance"),
        types.InlineKeyboardButton("📚 Учебные трудности", callback_data="study")
    )
    markup.add(
        types.InlineKeyboardButton("😰 Социальные страхи", callback_data="social"),
        types.InlineKeyboardButton("👨‍👩‍👧‍👦 Семья и окружение", callback_data="family")
    )
    markup.add(
        types.InlineKeyboardButton("🏠 Бытовые проблемы", callback_data="household"),
        types.InlineKeyboardButton("🎯 Профориентация", callback_data="career")
    )
    return markup

@bot.message_handler(commands=['start', 'menu', 'categories'])
def show_categories(message):
    """Показывает категории проблем"""
    markup = create_category_menu()
    text = """Выберите категорию, которая лучше всего описывает вашу ситуацию:

Я помогу вам найти подходящие решения и рекомендации."""
    
    bot.reply_to(message, text, reply_markup=markup)

@bot.callback_query_handler(func=lambda call: True)
def handle_category_selection(call):
    """Обработка выбора категории"""
    bot.answer_callback_query(call.id)
    
    # Соответствие кнопок и сообщений для классификатора
    category_messages = {
        "finance": "У меня финансовые проблемы с деньгами и стипендией",
        "study": "У меня учебные трудности и проблемы с экзаменами", 
        "social": "У меня социальные страхи и проблемы с общением",
        "family": "У меня проблемы с семьей и окружением",
        "household": "У меня бытовые проблемы и вопросы здоровья",
        "career": "У меня вопросы по профориентации и выбору карьеры"
    }
    
    if call.data in category_messages:
        # Создаем фальшивое сообщение для отправки в shai.pro
        fake_message = type('obj', (object,), {
            'text': category_messages[call.data],
            'from_user': call.from_user,
            'chat': call.message.chat,
            'message_id': call.message.message_id
        })
        
        # Уведомляем пользователя о выборе
        category_names = {
            "finance": "Финансовые проблемы",
            "study": "Учебные трудности",
            "social": "Социальные страхи", 
            "family": "Семья и окружение",
            "household": "Бытовые проблемы",
            "career": "Профориентация"
        }
        
        bot.edit_message_text(
            f"Вы выбрали: {category_names[call.data]}\n\nОбрабатываю ваш запрос...",
            call.message.chat.id,
            call.message.message_id
        )
        
        # Отправляем в систему shai.pro
        handle_message(fake_message)

@bot.message_handler(func=lambda message: True)
def handle_message(message):
    """Основная обработка сообщений"""
    # Если сообщение не команда - добавляем кнопку возврата к категориям
    if not message.text.startswith('/'):
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("📋 Выбрать другую категорию", callback_data="back_to_categories"))
    else:
        markup = None
    
    # Дублируем сообщение админам
    try:
        user_name = message.from_user.first_name
        if message.from_user.username:
            user_name += f" (@{message.from_user.username})"
        
        admin_msg = f"Входящее от {user_name}: {message.text}"
        bot.send_message(ADMIN_GROUP_ID, admin_msg)
    except:
        pass
    
    # Отправляем запрос в shai.pro
    headers = {
        'Authorization': 'Bearer app-LqQKmr2WcmFUTAjZk2adM46j',
        'Content-Type': 'application/json'
    }
    
    data = {
        'inputs': {},
        'query': message.text,
        'response_mode': 'blocking',
        'user': str(message.from_user.id)
    }
    
    try:
        response = requests.post('https://hackathon.shai.pro/v1/chat-messages', 
                               json=data, headers=headers, timeout=30)
        
        if response.status_code == 200:
            result = response.json()
            answer = result.get('answer', 'Ответ получен')
            
            bot.reply_to(message, answer, reply_markup=markup)
            
            # Дублируем ответ админам
            try:
                bot.send_message(ADMIN_GROUP_ID, f"Ответ для {user_name}: {answer}")
            except:
                pass
        else:
            bot.reply_to(message, "Извините, произошла ошибка", reply_markup=markup)
            
    except Exception as e:
        bot.reply_to(message, "Техническая ошибка", reply_markup=markup)

# Обработка возврата к категориям
@bot.callback_query_handler(func=lambda call: call.data == "back_to_categories")
def back_to_categories(call):
    bot.answer_callback_query(call.id)
    markup = create_category_menu()
    bot.edit_message_text(
        "Выберите категорию проблемы:",
        call.message.chat.id,
        call.message.message_id,
        reply_markup=markup
    )

bot.polling()