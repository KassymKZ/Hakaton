import os
import psycopg2
from psycopg2.extras import RealDictCursor
import requests
import telebot
from telebot import types
import logging
from datetime import datetime
import json

logging.basicConfig(level=logging.INFO)

bot = telebot.TeleBot('7567419832:AAGv0eE9K7bAuOMMzv_F8SskyAb4Qcj-tG0')
ADMIN_GROUP_ID = "-4940285744"
ADMIN_IDS = [824360574]

# Хранение состояний пользователей (только временно)
user_states = {}
admin_states = {}

class UserState:
    LANGUAGE = "language"
    AGE = "age"
    GENDER = "gender"
    BIRTHPLACE = "birthplace"
    FAMILY = "family"
    COURSE = "course"
    SPECIALTY = "specialty"
    HOUSING = "housing"
    COMPLETED = "completed"

class AdminState:
    IDLE = "idle"
    SELECTING_USER = "selecting_user"
    WRITING_MESSAGE = "writing_message"
    SEARCHING = "searching"

# Подключение к базе данных
def get_db_connection():
    try:
        conn = psycopg2.connect(
            host=os.environ.get('PGHOST'),
            port=os.environ.get('PGPORT', 5432),
            database=os.environ.get('PGDATABASE'),
            user=os.environ.get('PGUSER'),
            password=os.environ.get('PGPASSWORD')
        )
        return conn
    except Exception as e:
        logging.error(f"Database connection error: {e}")
        return None

# Инициализация базы данных
def init_database():
    conn = get_db_connection()
    if conn:
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS students (
                id SERIAL PRIMARY KEY,
                telegram_id BIGINT UNIQUE NOT NULL,
                telegram_username VARCHAR(255),
                telegram_first_name VARCHAR(255),
                telegram_last_name VARCHAR(255),
                user_language VARCHAR(10),
                user_age INTEGER,
                user_gender VARCHAR(20),
                user_birthplace VARCHAR(100),
                user_family_status VARCHAR(50),
                user_course INTEGER,
                user_specialty TEXT,
                user_housing_type VARCHAR(50),
                registration_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                profile_completed BOOLEAN DEFAULT FALSE,
                last_activity TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS conversations (
                id SERIAL PRIMARY KEY,
                telegram_id BIGINT REFERENCES students(telegram_id),
                question TEXT,
                answer TEXT,
                category VARCHAR(50),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS admin_messages (
                id SERIAL PRIMARY KEY,
                admin_id BIGINT,
                target_user_id BIGINT REFERENCES students(telegram_id),
                message_text TEXT,
                sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                delivered BOOLEAN DEFAULT FALSE
            )
        ''')
        
        conn.commit()
        cursor.close()
        conn.close()
        logging.info("Database initialized successfully")

# Функции для работы с базой данных
def save_student_profile(profile_data):
    conn = get_db_connection()
    if conn:
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO students (
                telegram_id, telegram_username, telegram_first_name, 
                telegram_last_name, user_language, user_age, user_gender,
                user_birthplace, user_family_status, user_course, 
                user_specialty, user_housing_type, profile_completed
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (telegram_id) 
            DO UPDATE SET
                telegram_username = EXCLUDED.telegram_username,
                telegram_first_name = EXCLUDED.telegram_first_name,
                telegram_last_name = EXCLUDED.telegram_last_name,
                user_language = EXCLUDED.user_language,
                user_age = EXCLUDED.user_age,
                user_gender = EXCLUDED.user_gender,
                user_birthplace = EXCLUDED.user_birthplace,
                user_family_status = EXCLUDED.user_family_status,
                user_course = EXCLUDED.user_course,
                user_specialty = EXCLUDED.user_specialty,
                user_housing_type = EXCLUDED.user_housing_type,
                profile_completed = EXCLUDED.profile_completed,
                last_activity = CURRENT_TIMESTAMP
        ''', (
            profile_data['telegram_id'], profile_data.get('telegram_username'),
            profile_data.get('telegram_first_name'), profile_data.get('telegram_last_name'),
            profile_data.get('user_language'), profile_data.get('user_age'),
            profile_data.get('user_gender'), profile_data.get('user_birthplace'),
            profile_data.get('user_family_status'), profile_data.get('user_course'),
            profile_data.get('user_specialty'), profile_data.get('user_housing_type'),
            True
        ))
        conn.commit()
        cursor.close()
        conn.close()

def save_conversation(telegram_id, question, answer, category=None):
    conn = get_db_connection()
    if conn:
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO conversations (telegram_id, question, answer, category)
            VALUES (%s, %s, %s, %s)
        ''', (telegram_id, question, answer, category))
        conn.commit()
        cursor.close()
        conn.close()

def get_student_by_id(telegram_id):
    conn = get_db_connection()
    if conn:
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute('SELECT * FROM students WHERE telegram_id = %s', (telegram_id,))
        result = cursor.fetchone()
        cursor.close()
        conn.close()
        return dict(result) if result else None
    return None

def get_all_students(limit=None, search_term=None):
    conn = get_db_connection()
    if conn:
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        query = 'SELECT * FROM students WHERE profile_completed = TRUE'
        params = []
        
        if search_term:
            query += ''' AND (
                LOWER(telegram_first_name) LIKE LOWER(%s) OR 
                LOWER(telegram_last_name) LIKE LOWER(%s) OR 
                LOWER(telegram_username) LIKE LOWER(%s) OR 
                LOWER(user_specialty) LIKE LOWER(%s)
            )'''
            search_pattern = f"%{search_term}%"
            params.extend([search_pattern, search_pattern, search_pattern, search_pattern])
        
        query += ' ORDER BY registration_date DESC'
        
        if limit:
            query += f' LIMIT {limit}'
            
        cursor.execute(query, params)
        results = cursor.fetchall()
        cursor.close()
        conn.close()
        return [dict(row) for row in results]
    return []

def get_student_conversations(telegram_id, limit=10):
    conn = get_db_connection()
    if conn:
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute('''
            SELECT * FROM conversations 
            WHERE telegram_id = %s 
            ORDER BY created_at DESC 
            LIMIT %s
        ''', (telegram_id, limit))
        results = cursor.fetchall()
        cursor.close()
        conn.close()
        return [dict(row) for row in results]
    return []

def save_admin_message(admin_id, target_user_id, message_text):
    conn = get_db_connection()
    if conn:
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO admin_messages (admin_id, target_user_id, message_text)
            VALUES (%s, %s, %s)
        ''', (admin_id, target_user_id, message_text))
        conn.commit()
        cursor.close()
        conn.close()

# Функции создания меню (остаются без изменений)
def create_language_menu():
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(types.InlineKeyboardButton("🇰🇿 Қазақша", callback_data="lang_kz"))
    markup.add(types.InlineKeyboardButton("🇷🇺 Русский", callback_data="lang_ru"))
    markup.add(types.InlineKeyboardButton("🇺🇸 English", callback_data="lang_en"))
    return markup

def create_gender_menu(language):
    markup = types.InlineKeyboardMarkup(row_width=2)
    
    if language == "kz":
        markup.add(
            types.InlineKeyboardButton("👨 Ер", callback_data="gender_male"),
            types.InlineKeyboardButton("👩 Әйел", callback_data="gender_female")
        )
    elif language == "en":
        markup.add(
            types.InlineKeyboardButton("👨 Male", callback_data="gender_male"),
            types.InlineKeyboardButton("👩 Female", callback_data="gender_female")
        )
    else:
        markup.add(
            types.InlineKeyboardButton("👨 Мужской", callback_data="gender_male"),
            types.InlineKeyboardButton("👩 Женский", callback_data="gender_female")
        )
    return markup

def create_birthplace_menu(language):
    markup = types.InlineKeyboardMarkup(row_width=1)
    
    regions = [
        ("🏛️ Город Астана", "astana"),
        ("🌆 Город Алма-Ата", "almaty"),
        ("🏙️ Город Шымкент", "shymkent"),
        ("🌾 Абайская область", "abai"),
        ("🌱 Акмолинская область", "akmola"),
        ("⚡ Актюбинская область", "aktobe"),
        ("🍎 Алматинская область", "almaty_region"),
        ("🛢️ Атырауская область", "atyrau"),
        ("🏔️ Восточно-Казахстанская область", "east_kz"),
        ("🌿 Жамбылская область", "zhambyl"),
        ("🍇 Жетысуская область", "jetysu"),
        ("🌾 Западно-Казахстанская область", "west_kz"),
        ("⚒️ Карагандинская область", "karaganda"),
        ("🌾 Костанайская область", "kostanay"),
        ("🏜️ Кызылординская область", "kyzylorda"),
        ("🌊 Мангистауская область", "mangistau"),
        ("🏭 Павлодарская область", "pavlodar"),
        ("❄️ Северо-Казахстанская область", "north_kz"),
        ("🕌 Туркестанская область", "turkestan"),
        ("⛰️ Улытауская область", "ulytau")
    ]
    
    for text, callback_data in regions:
        markup.add(types.InlineKeyboardButton(text, callback_data=f"birthplace_{callback_data}"))
    
    return markup

def create_family_menu(language):
    markup = types.InlineKeyboardMarkup(row_width=1)
    
    if language == "kz":
        markup.add(types.InlineKeyboardButton("👨‍👩‍👧‍👦 Толық отбасы", callback_data="family_full"))
        markup.add(types.InlineKeyboardButton("💔 Толық емес отбасы", callback_data="family_incomplete"))
        markup.add(types.InlineKeyboardButton("😔 Жетім", callback_data="family_orphan"))
    elif language == "en":
        markup.add(types.InlineKeyboardButton("👨‍👩‍👧‍👦 Complete family", callback_data="family_full"))
        markup.add(types.InlineKeyboardButton("💔 Incomplete family", callback_data="family_incomplete"))
        markup.add(types.InlineKeyboardButton("😔 Orphan", callback_data="family_orphan"))
    else:
        markup.add(types.InlineKeyboardButton("👨‍👩‍👧‍👦 Полная", callback_data="family_full"))
        markup.add(types.InlineKeyboardButton("💔 Неполная", callback_data="family_incomplete"))
        markup.add(types.InlineKeyboardButton("😔 Сирота", callback_data="family_orphan"))
    return markup

def create_course_menu(language):
    markup = types.InlineKeyboardMarkup(row_width=4)
    markup.add(
        types.InlineKeyboardButton("1️⃣ 1 курс", callback_data="course_1"),
        types.InlineKeyboardButton("2️⃣ 2 курс", callback_data="course_2"),
        types.InlineKeyboardButton("3️⃣ 3 курс", callback_data="course_3"),
        types.InlineKeyboardButton("4️⃣ 4 курс", callback_data="course_4")
    )
    return markup

def create_housing_menu(language):
    markup = types.InlineKeyboardMarkup(row_width=1)
    
    if language == "kz":
        markup.add(types.InlineKeyboardButton("🏠 Жатақхана", callback_data="housing_dormitory"))
        markup.add(types.InlineKeyboardButton("🏡 Жалдау", callback_data="housing_rent"))
        markup.add(types.InlineKeyboardButton("🏘️ Меншікті үй (туыстарда)", callback_data="housing_own"))
    elif language == "en":
        markup.add(types.InlineKeyboardButton("🏠 Dormitory", callback_data="housing_dormitory"))
        markup.add(types.InlineKeyboardButton("🏡 Rental", callback_data="housing_rent"))
        markup.add(types.InlineKeyboardButton("🏘️ Own housing (relatives)", callback_data="housing_own"))
    else:
        markup.add(types.InlineKeyboardButton("🏠 Общежитие", callback_data="housing_dormitory"))
        markup.add(types.InlineKeyboardButton("🏡 Аренда жилья", callback_data="housing_rent"))
        markup.add(types.InlineKeyboardButton("🏘️ Собственное жилье (у родственников)", callback_data="housing_own"))
    return markup

def create_category_menu(language):
    markup = types.InlineKeyboardMarkup(row_width=1)
    
    categories = {
        'kz': [
            ("💰 Қаржылық мәселелер", "finance"),
            ("📚 Оқу қиындықтары", "study"),
            ("😰 Әлеуметтік қорқыныштар", "social"),
            ("👨‍👩‍👧‍👦 Отбасы және орта", "family"),
            ("🏠 Тұрмыстық мәселелер", "household"),
            ("🎯 Мамандық таңдау", "career")
        ],
        'ru': [
            ("💰 Финансовые проблемы", "finance"),
            ("📚 Учебные трудности", "study"),
            ("😰 Социальные страхи", "social"),
            ("👨‍👩‍👧‍👦 Семья и окружение", "family"),
            ("🏠 Бытовые проблемы", "household"),
            ("🎯 Профориентация", "career")
        ],
        'en': [
            ("💰 Financial problems", "finance"),
            ("📚 Academic difficulties", "study"),
            ("😰 Social fears", "social"),
            ("👨‍👩‍👧‍👦 Family and environment", "family"),
            ("🏠 Household problems", "household"),
            ("🎯 Career guidance", "career")
        ]
    }
    
    for text, callback_data in categories[language]:
        markup.add(types.InlineKeyboardButton(text, callback_data=f"{callback_data}_{language}"))
    
    # Добавляем кнопку возврата к меню
    markup.add(types.InlineKeyboardButton("🔙 Назад к меню", callback_data="back_to_menu"))
    
    return markup

def get_text(language, key):
    texts = {
        'language_select': {
            'kz': '🌐 Тілді таңдаңыз:',
            'ru': '🌐 Выберите язык:',
            'en': '🌐 Choose language:'
        },
        'age_request': {
            'kz': '🎂 Жасыңызды жазыңыз (тек цифрлар):',
            'ru': '🎂 Введите ваш возраст (только цифры):',
            'en': '🎂 Enter your age (numbers only):'
        },
        'gender_request': {
            'kz': '⚧️ Жынысыңызды таңдаңыз:',
            'ru': '⚧️ Выберите ваш пол:',
            'en': '⚧️ Choose your gender:'
        },
        'birthplace_request': {
            'kz': '🏙️ Туған жеріңізді таңдаңыз:',
            'ru': '🏙️ Выберите место рождения:',
            'en': '🏙️ Choose your birthplace:'
        },
        'family_request': {
            'kz': '👨‍👩‍👧‍👦 Отбасылық жағдайыңызды таңдаңыз:',
            'ru': '👨‍👩‍👧‍👦 Выберите семейное положение:',
            'en': '👨‍👩‍👧‍👦 Choose your family status:'
        },
        'course_request': {
            'kz': '📚 Курсыңызды таңдаңыз:',
            'ru': '📚 Выберите курс обучения:',
            'en': '📚 Choose your year of study:'
        },
        'specialty_request': {
            'kz': '🎓 Мамандығыңызды жазыңыз:',
            'ru': '🎓 Введите вашу специальность:',
            'en': '🎓 Enter your specialty:'
        },
        'housing_request': {
            'kz': '🏠 Тұрғылықты жеріңізді таңдаңыз:',
            'ru': '🏠 Выберите тип жилья:',
            'en': '🏠 Choose your housing type:'
        },
        'profile_complete': {
            'kz': '✅ Профиль толтырылды! Категорияны таңдаңыз:',
            'ru': '✅ Профиль заполнен! Выберите категорию:',
            'en': '✅ Profile completed! Choose category:'
        },
        'age_invalid': {
            'kz': '❌ Жасыңызды дұрыс енгізіңіз (16-35 арасында):',
            'ru': '❌ Пожалуйста, введите корректный возраст (16-35):',
            'en': '❌ Please enter a valid age (16-35):'
        }
    }
    
    return texts.get(key, {}).get(language, texts.get(key, {}).get('en', ''))

# АДМИНСКИЕ КОМАНДЫ
@bot.message_handler(commands=['admin'])
def admin_command(message):
    if message.from_user.id not in ADMIN_IDS:
        bot.reply_to(message, "❌ У вас нет доступа к админской панели")
        return
    
    admin_states[message.from_user.id] = AdminState.IDLE
    
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("👥 Список студентов", callback_data="admin_list_students"),
        types.InlineKeyboardButton("📊 Статистика", callback_data="admin_stats")
    )
    markup.add(
        types.InlineKeyboardButton("📧 Отправить сообщение", callback_data="admin_send_message"),
        types.InlineKeyboardButton("🔍 Поиск студента", callback_data="admin_search")
    )
    markup.add(types.InlineKeyboardButton("📋 История диалогов", callback_data="admin_conversations"))
    
    bot.reply_to(message, "🛠️ Админская панель:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('admin_'))
def handle_admin_commands(call):
    if call.from_user.id not in ADMIN_IDS:
        bot.answer_callback_query(call.id, "❌ Нет доступа")
        return
    
    bot.answer_callback_query(call.id)
    
    if call.data == "admin_list_students":
        show_students_list(call.message)
    elif call.data == "admin_stats":
        show_statistics(call.message)
    elif call.data == "admin_send_message":
        start_message_sending(call.message)
    elif call.data == "admin_search":
        start_student_search(call.message)
    elif call.data == "admin_conversations":
        show_conversations_list(call.message)
    elif call.data == "admin_back":
        admin_command(call.message)

def show_students_list(message, page=1, per_page=5):
    students = get_all_students()
    total_students = len(students)
    start_idx = (page - 1) * per_page
    end_idx = start_idx + per_page
    students_page = students[start_idx:end_idx]
    
    if not students_page:
        bot.edit_message_text("📝 Нет зарегистрированных студентов", 
                             message.chat.id, message.message_id)
        return
    
    text = f"👥 Список студентов (стр. {page} из {(total_students + per_page - 1) // per_page}):\n\n"
    
    for i, student in enumerate(students_page, start_idx + 1):
        name = f"{student.get('telegram_first_name', '')} {student.get('telegram_last_name', '')}".strip()
        username = f"@{student.get('telegram_username')}" if student.get('telegram_username') else "без username"
        
        text += f"{i}. {name or 'Без имени'}\n"
        text += f"   ID: {student['telegram_id']}\n"
        text += f"   {username}\n"
        text += f"   Курс: {student.get('user_course', '?')}, {student.get('user_specialty', 'Не указано')}\n"
        text += f"   Регистрация: {student['registration_date'].strftime('%d.%m.%Y')}\n\n"
    
    markup = types.InlineKeyboardMarkup()
    
    # Навигация
    nav_buttons = []
    if page > 1:
        nav_buttons.append(types.InlineKeyboardButton("⬅️ Назад", callback_data=f"students_page_{page-1}"))
    if end_idx < total_students:
        nav_buttons.append(types.InlineKeyboardButton("➡️ Далее", callback_data=f"students_page_{page+1}"))
    
    if nav_buttons:
        markup.add(*nav_buttons)
    
    # Действия
    markup.add(
        types.InlineKeyboardButton("👤 Подробнее", callback_data="admin_student_details"),
        types.InlineKeyboardButton("📧 Отправить сообщение", callback_data="admin_send_to_student")
    )
    markup.add(types.InlineKeyboardButton("🔙 Назад", callback_data="admin_back"))
    
    try:
        bot.edit_message_text(text, message.chat.id, message.message_id, reply_markup=markup)
    except:
        bot.send_message(message.chat.id, text, reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('students_page_'))
def handle_students_pagination(call):
    if call.from_user.id not in ADMIN_IDS:
        return
    
    page = int(call.data.split('_')[-1])
    show_students_list(call.message, page)

def show_statistics(message):
    conn = get_db_connection()
    if not conn:
        try:
            bot.edit_message_text("❌ Ошибка подключения к БД", message.chat.id, message.message_id)
        except:
            bot.send_message(message.chat.id, "❌ Ошибка подключения к БД")
        return
    
    cursor = conn.cursor()
    
    # Общая статистика
    cursor.execute("SELECT COUNT(*) FROM students WHERE profile_completed = TRUE")
    total_students = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM conversations")
    total_conversations = cursor.fetchone()[0]
    
    # По курсам
    cursor.execute("SELECT user_course, COUNT(*) FROM students WHERE profile_completed = TRUE GROUP BY user_course ORDER BY user_course")
    courses_stats = cursor.fetchall()
    
    # По регионам (топ 5)
    cursor.execute("""
        SELECT user_birthplace, COUNT(*) as count 
        FROM students WHERE profile_completed = TRUE 
        GROUP BY user_birthplace 
        ORDER BY count DESC 
        LIMIT 5
    """)
    regions_stats = cursor.fetchall()
    
    # По типу жилья
    cursor.execute("SELECT user_housing_type, COUNT(*) FROM students WHERE profile_completed = TRUE GROUP BY user_housing_type")
    housing_stats = cursor.fetchall()
    
    cursor.close()
    conn.close()
    
    text = f"📊 СТАТИСТИКА СТУДЕНТОВ\n\n"
    text += f"👥 Всего зарегистрировано: {total_students}\n"
    text += f"💬 Всего диалогов: {total_conversations}\n\n"
    
    if courses_stats:
        text += f"📚 По курсам:\n"
        for course, count in courses_stats:
            text += f"   {course} курс: {count} чел.\n"
        text += "\n"
    
    if regions_stats:
        text += f"🏙️ Топ регионов:\n"
        region_names = {
            'astana': 'Астана', 'almaty': 'Алма-Ата', 'shymkent': 'Шымкент',
            'abai': 'Абайская обл.', 'akmola': 'Акмолинская обл.'
        }
        for region, count in regions_stats:
            region_name = region_names.get(region, region.replace('_', ' ').title())
            text += f"   {region_name}: {count} чел.\n"
        text += "\n"
    
    if housing_stats:
        text += f"🏠 По типу жилья:\n"
        housing_names = {'dormitory': 'Общежитие', 'rent': 'Аренда', 'own': 'Собственное'}
        for housing, count in housing_stats:
            housing_name = housing_names.get(housing, housing)
            text += f"   {housing_name}: {count} чел.\n"
    
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("🔙 Назад", callback_data="admin_back"))
    
    try:
        bot.edit_message_text(text, message.chat.id, message.message_id, reply_markup=markup)
    except:
        bot.send_message(message.chat.id, text, reply_markup=markup)

def start_message_sending(message):
    admin_states[message.from_user.id] = AdminState.SELECTING_USER
    
    text = "📧 Отправка сообщения студенту\n\nВведите Telegram ID студента:"
    
    try:
        bot.edit_message_text(text, message.chat.id, message.message_id)
    except:
        bot.send_message(message.chat.id, text)

def start_student_search(message):
    admin_states[message.from_user.id] = AdminState.SEARCHING
    
    text = "🔍 Поиск студента\n\nВведите имя, username или специальность для поиска:"
    
    try:
        bot.edit_message_text(text, message.chat.id, message.message_id)
    except:
        bot.send_message(message.chat.id, text)

def show_conversations_list(message):
    conn = get_db_connection()
    if not conn:
        try:
            bot.edit_message_text("❌ Ошибка подключения к БД", message.chat.id, message.message_id)
        except:
            bot.send_message(message.chat.id, "❌ Ошибка подключения к БД")
        return
    
    cursor = conn.cursor()
    cursor.execute('''
        SELECT c.*, s.telegram_first_name, s.telegram_last_name, s.telegram_username
        FROM conversations c
        JOIN students s ON c.telegram_id = s.telegram_id
        ORDER BY c.created_at DESC
        LIMIT 10
    ''')
    conversations = cursor.fetchall()
    cursor.close()
    conn.close()
    
    if not conversations:
        text = "💬 Нет диалогов"
    else:
        text = "💬 Последние 10 диалогов:\n\n"
        
    for conv in conversations:
            name = f"{conv[5] or ''} {conv[6] or ''}".strip() or "Без имени"
            username = f"@{conv[7]}" if conv[7] else ""
            
            text += f"👤 {name} {username}\n"
            text += f"❓ {conv[1][:50]}{'...' if len(conv[1]) > 50 else ''}\n"
            text += f"🤖 {conv[2][:50]}{'...' if len(conv[2]) > 50 else ''}\n"
            text += f"📅 {conv[4].strftime('%d.%m.%Y %H:%M')}\n\n"
    
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("🔙 Назад", callback_data="admin_back"))
    
    try:
        bot.edit_message_text(text, message.chat.id, message.message_id, reply_markup=markup)
    except:
        bot.send_message(message.chat.id, text, reply_markup=markup)

# ОСНОВНЫЕ ОБРАБОТЧИКИ АНКЕТИРОВАНИЯ
@bot.message_handler(commands=['start'])
def start_command(message):
    # Проверяем, есть ли уже профиль в БД
    student = get_student_by_id(message.from_user.id)
    
    if student and student.get('profile_completed'):
        # Профиль уже заполнен, показываем меню категорий
        language = student.get('user_language', 'ru')
        markup = create_category_menu(language)
        bot.reply_to(message, get_text(language, 'profile_complete'), reply_markup=markup)
    else:
        # Начинаем анкетирование
        user_states[message.from_user.id] = UserState.LANGUAGE
        markup = create_language_menu()
        bot.reply_to(message, get_text('en', 'language_select'), reply_markup=markup)

# Обработчики выбора языка
@bot.callback_query_handler(func=lambda call: call.data.startswith('lang_'))
def handle_language_selection(call):
    bot.answer_callback_query(call.id)
    
    language = call.data.split('_')[1]
    user_states[call.from_user.id] = UserState.AGE
    
    # Сохраняем базовую информацию
    profile_data = {
        'telegram_id': call.from_user.id,
        'telegram_username': call.from_user.username,
        'telegram_first_name': call.from_user.first_name,
        'telegram_last_name': call.from_user.last_name,
        'user_language': language,
        'profile_completed': False
    }
    save_student_profile(profile_data)
    
    bot.edit_message_text(
        get_text(language, 'age_request'),
        call.message.chat.id,
        call.message.message_id
    )

@bot.callback_query_handler(func=lambda call: call.data.startswith('gender_'))
def handle_gender_selection(call):
    bot.answer_callback_query(call.id)
    
    gender = call.data.split('_')[1]
    student = get_student_by_id(call.from_user.id)
    language = student.get('user_language', 'ru')
    
    # Обновляем профиль
    profile_data = student.copy()
    profile_data['user_gender'] = gender
    save_student_profile(profile_data)
    
    user_states[call.from_user.id] = UserState.BIRTHPLACE
    
    markup = create_birthplace_menu(language)
    bot.edit_message_text(
        get_text(language, 'birthplace_request'),
        call.message.chat.id,
        call.message.message_id,
        reply_markup=markup
    )

@bot.callback_query_handler(func=lambda call: call.data.startswith('birthplace_'))
def handle_birthplace_selection(call):
    bot.answer_callback_query(call.id)
    
    birthplace = call.data.split('_')[1]
    student = get_student_by_id(call.from_user.id)
    language = student.get('user_language', 'ru')
    
    profile_data = student.copy()
    profile_data['user_birthplace'] = birthplace
    save_student_profile(profile_data)
    
    user_states[call.from_user.id] = UserState.FAMILY
    
    markup = create_family_menu(language)
    bot.edit_message_text(
        get_text(language, 'family_request'),
        call.message.chat.id,
        call.message.message_id,
        reply_markup=markup
    )

@bot.callback_query_handler(func=lambda call: call.data.startswith('family_'))
def handle_family_selection(call):
    bot.answer_callback_query(call.id)
    
    family = call.data.split('_')[1]
    student = get_student_by_id(call.from_user.id)
    language = student.get('user_language', 'ru')
    
    profile_data = student.copy()
    profile_data['user_family_status'] = family
    save_student_profile(profile_data)
    
    user_states[call.from_user.id] = UserState.COURSE
    
    markup = create_course_menu(language)
    bot.edit_message_text(
        get_text(language, 'course_request'),
        call.message.chat.id,
        call.message.message_id,
        reply_markup=markup
    )

@bot.callback_query_handler(func=lambda call: call.data.startswith('course_'))
def handle_course_selection(call):
    bot.answer_callback_query(call.id)
    
    course = call.data.split('_')[1]
    student = get_student_by_id(call.from_user.id)
    language = student.get('user_language', 'ru')
    
    profile_data = student.copy()
    profile_data['user_course'] = int(course)
    save_student_profile(profile_data)
    
    user_states[call.from_user.id] = UserState.SPECIALTY
    
    bot.edit_message_text(
        get_text(language, 'specialty_request'),
        call.message.chat.id,
        call.message.message_id
    )

@bot.callback_query_handler(func=lambda call: call.data.startswith('housing_'))
def handle_housing_selection(call):
    bot.answer_callback_query(call.id)
    
    housing = call.data.split('_')[1]
    student = get_student_by_id(call.from_user.id)
    language = student.get('user_language', 'ru')
    
    profile_data = student.copy()
    profile_data['user_housing_type'] = housing
    profile_data['profile_completed'] = True
    save_student_profile(profile_data)
    
    user_states[call.from_user.id] = UserState.COMPLETED
    
    # Отправляем уведомление в админскую группу
    send_profile_to_admin(profile_data)
    
    # Показываем меню категорий
    markup = create_category_menu(language)
    bot.edit_message_text(
        get_text(language, 'profile_complete'),
        call.message.chat.id,
        call.message.message_id,
        reply_markup=markup
    )

@bot.callback_query_handler(func=lambda call: call.data == 'back_to_menu')
def handle_back_to_menu(call):
    bot.answer_callback_query(call.id)
    
    student = get_student_by_id(call.from_user.id)
    if student and student.get('profile_completed'):
        language = student.get('user_language', 'ru')
        markup = create_category_menu(language)
        bot.edit_message_text(
            get_text(language, 'profile_complete'),
            call.message.chat.id,
            call.message.message_id,
            reply_markup=markup
        )

# ОБРАБОТЧИКИ КАТЕГОРИЙ И SHAI.PRO
@bot.callback_query_handler(func=lambda call: any(cat in call.data for cat in ['finance_', 'study_', 'social_', 'family_', 'household_', 'career_']))
def handle_category_selection(call):
    bot.answer_callback_query(call.id)
    
    # Разбираем callback_data
    parts = call.data.split('_')
    category = parts[0]
    language = parts[1] if len(parts) > 1 else 'ru'
    
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
    
    if category in category_messages:
        bot.edit_message_text(
            f"Вы выбрали: {category_names[category]}\n\nОбрабатываю ваш запрос...",
            call.message.chat.id,
            call.message.message_id
        )
        
        # Отправляем в shai.pro
        send_to_shai_pro(category_messages[category], call.from_user, call.message.chat, category)

def send_to_shai_pro(text, user, chat, category=None):
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
            
            # Сохраняем диалог в БД
            save_conversation(user.id, text, answer, category)
            
            # Кнопка возврата к меню
            student = get_student_by_id(user.id)
            language = student.get('user_language', 'ru') if student else 'ru'
            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton("🔙 Назад к меню", callback_data="back_to_menu"))
            
            bot.send_message(chat.id, answer, reply_markup=markup)
            
            # Отправляем отчет в админскую группу
            send_conversation_report(user, text, answer, category)
            
        else:
            bot.send_message(chat.id, f"Произошла ошибка обработки запроса. Код: {response.status_code}")
            
    except requests.Timeout:
        bot.send_message(chat.id, "Превышено время ожидания ответа. Попробуйте еще раз.")
    except Exception as e:
        logging.error(f"Ошибка запроса: {e}")
        bot.send_message(chat.id, "Произошла техническая ошибка. Попробуйте позже.")

def send_conversation_report(user, question, answer, category):
    try:
        student = get_student_by_id(user.id)
        if not student:
            return
            
        category_names = {
            'finance': '💰 Финансовые проблемы',
            'study': '📚 Учебные трудности',
            'social': '😰 Социальные страхи',
            'family': '👨‍👩‍👧‍👦 Семья и окружение',
            'household': '🏠 Бытовые проблемы',
            'career': '🎯 Профориентация'
        }
        
        name = f"{student.get('telegram_first_name', '')} {student.get('telegram_last_name', '')}".strip()
        username = f"@{student.get('telegram_username')}" if student.get('telegram_username') else ""
        
        report = f"""
💬 НОВЫЙ ДИАЛОГ

👤 От: {name or 'Без имени'} {username}
🆔 ID: {user.id}
📂 Категория: {category_names.get(category, 'Общий вопрос')}
🕐 Время: {datetime.now().strftime("%d.%m.%Y %H:%M")}

❓ Вопрос:
{question}

🤖 Ответ:
{answer[:300]}{'...' if len(answer) > 300 else ''}

━━━━━━━━━━━━━━━━━━
"""
        
        bot.send_message(ADMIN_GROUP_ID, report)
        
    except Exception as e:
        logging.error(f"Ошибка отправки отчета: {e}")

@bot.message_handler(func=lambda message: True)
def handle_message(message):
    user_id = message.from_user.id
    
    # Проверяем админские состояния
    if user_id in ADMIN_IDS and user_id in admin_states:
        handle_admin_message(message)
        return
    
    # Проверяем состояние анкетирования
    if user_id in user_states:
        state = user_states[user_id]
        student = get_student_by_id(user_id)
        language = student.get('user_language', 'ru') if student else 'ru'
        
        if state == UserState.AGE:
            try:
                age = int(message.text)
                if 16 <= age <= 35:
                    profile_data = student.copy()
                    profile_data['user_age'] = age
                    save_student_profile(profile_data)
                    
                    user_states[user_id] = UserState.GENDER
                    markup = create_gender_menu(language)
                    bot.reply_to(message, get_text(language, 'gender_request'), reply_markup=markup)
                else:
                    bot.reply_to(message, get_text(language, 'age_invalid'))
            except ValueError:
                bot.reply_to(message, get_text(language, 'age_invalid'))
                
        elif state == UserState.SPECIALTY:
            profile_data = student.copy()
            profile_data['user_specialty'] = message.text
            save_student_profile(profile_data)
            
            user_states[user_id] = UserState.HOUSING
            markup = create_housing_menu(language)
            bot.reply_to(message, get_text(language, 'housing_request'), reply_markup=markup)
    
    else:
        # Обычное сообщение от зарегистрированного пользователя
        student = get_student_by_id(user_id)
        if student and student.get('profile_completed'):
            send_to_shai_pro(message.text, message.from_user, message.chat)
        else:
            start_command(message)

def handle_admin_message(message):
    admin_id = message.from_user.id
    state = admin_states.get(admin_id, AdminState.IDLE)
    
    if state == AdminState.SELECTING_USER:
        try:
            target_user_id = int(message.text)
            student = get_student_by_id(target_user_id)
            
            if student:
                admin_states[admin_id] = AdminState.WRITING_MESSAGE
                # Временно сохраняем ID целевого пользователя
                if 'temp_data' not in globals():
                    globals()['temp_data'] = {}
                globals()['temp_data'][admin_id] = {'target_user_id': target_user_id}
                
                name = f"{student.get('telegram_first_name', '')} {student.get('telegram_last_name', '')}".strip()
                bot.reply_to(message, f"Найден студент: {name or 'Без имени'}\n\nВведите сообщение для отправки:")
            else:
                bot.reply_to(message, "Студент не найден. Попробуйте еще раз:")
        except ValueError:
            bot.reply_to(message, "Некорректный ID. Введите числовой ID:")
    
    elif state == AdminState.WRITING_MESSAGE:
        if 'temp_data' in globals() and admin_id in globals()['temp_data']:
            target_user_id = globals()['temp_data'][admin_id]['target_user_id']
            message_text = message.text
            
            # Сохраняем сообщение в БД
            save_admin_message(admin_id, target_user_id, message_text)
            
            # Отправляем сообщение студенту
            try:
                bot.send_message(target_user_id, f"📧 Сообщение от администрации:\n\n{message_text}")
                bot.reply_to(message, "✅ Сообщение отправлено!")
            except Exception as e:
                bot.reply_to(message, f"❌ Ошибка отправки: {e}")
            
            # Очищаем состояние
            admin_states[admin_id] = AdminState.IDLE
            del globals()['temp_data'][admin_id]
        
    elif state == AdminState.SEARCHING:
        search_term = message.text
        students = get_all_students(limit=10, search_term=search_term)
        
        if students:
            text = f"🔍 Результаты поиска по '{search_term}':\n\n"
            
            for i, student in enumerate(students, 1):
                name = f"{student.get('telegram_first_name', '')} {student.get('telegram_last_name', '')}".strip()
                username = f"@{student.get('telegram_username')}" if student.get('telegram_username') else ""
                
                text += f"{i}. {name or 'Без имени'} {username}\n"
                text += f"   ID: {student['telegram_id']}\n"
                text += f"   Специальность: {student.get('user_specialty', 'Не указано')}\n\n"
            
            bot.reply_to(message, text)
        else:
            bot.reply_to(message, "Ничего не найдено")
        
        admin_states[admin_id] = AdminState.IDLE

def send_profile_to_admin(profile):
    try:
        region_names = {
            'astana': 'Город Астана', 'almaty': 'Город Алма-Ата', 'shymkent': 'Город Шымкент',
            'abai': 'Абайская область', 'akmola': 'Акмолинская область', 'aktobe': 'Актюбинская область',
            'almaty_region': 'Алматинская область', 'atyrau': 'Атырауская область', 'east_kz': 'Восточно-Казахстанская область',
            'zhambyl': 'Жамбылская область', 'jetysu': 'Жетысуская область', 'west_kz': 'Западно-Казахстанская область',
            'karaganda': 'Карагандинская область', 'kostanay': 'Костанайская область', 'kyzylorda': 'Кызылординская область',
            'mangistau': 'Мангистауская область', 'pavlodar': 'Павлодарская область', 'north_kz': 'Северо-Казахстанская область',
            'turkestan': 'Туркестанская область', 'ulytau': 'Улытауская область'
        }
        
        family_names = {'full': '👨‍👩‍👧‍👦 Полная семья', 'incomplete': '💔 Неполная семья', 'orphan': '😔 Сирота'}
        gender_names = {'male': '👨 Мужской', 'female': '👩 Женский'}
        housing_names = {'dormitory': '🏠 Общежитие', 'rent': '🏡 Аренда жилья', 'own': '🏘️ Собственное жилье'}
        
        name = f"{profile.get('telegram_first_name', '')} {profile.get('telegram_last_name', '')}".strip()
        
        report = f"""
📋 НОВЫЙ СТУДЕНТ ЗАРЕГИСТРИРОВАН

🆔 Telegram ID: {profile.get('telegram_id')}
📞 Username: @{profile.get('telegram_username', 'не указан')}
👤 Имя: {name or 'Не указано'}
🎂 Возраст: {profile.get('user_age')}
⚧️ Пол: {gender_names.get(profile.get('user_gender'), 'Не указано')}
🏙️ Место рождения: {region_names.get(profile.get('user_birthplace'), 'Не указано')}
👨‍👩‍👧‍👦 Семья: {family_names.get(profile.get('user_family_status'), 'Не указано')}
📚 Курс: {profile.get('user_course')} курс
🎓 Специальность: {profile.get('user_specialty')}
🏠 Жилье: {housing_names.get(profile.get('user_housing_type'), 'Не указано')}
🌐 Язык: {profile.get('user_language', 'ru').upper()}
🕐 Время регистрации: {datetime.now().strftime("%d.%m.%Y %H:%M")}

━━━━━━━━━━━━━━━━━━
"""
        
        bot.send_message(ADMIN_GROUP_ID, report)
        
    except Exception as e:
        logging.error(f"Ошибка отправки профиля админам: {e}")

# Инициализируем базу данных при запуске
init_database()

# Запуск бота
if __name__ == "__main__":
    logging.info("Bot started")
    bot.polling()