import os
import psycopg2
from psycopg2.extras import RealDictCursor
import requests
import telebot
from telebot import types
import logging
from datetime import datetime

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

bot = telebot.TeleBot('7567419832:AAGv0eE9K7bAuOMMzv_F8SskyAb4Qcj-tG0')
ADMIN_GROUP_ID = "-4940285744"
ADMIN_IDS = [824360574]

# Хранение состояний пользователей
user_states = {}
admin_states = {}
temp_profiles = {}
reply_contexts = {}  # Для хранения контекстов ответов админов

class UserState:
    LANGUAGE = "language"
    PREFERRED_NAME = "preferred_name"
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
    REPLYING = "replying"

# Подключение к базе данных
def get_db_connection():
    try:
        database_url = os.environ.get('DATABASE_URL')
        
        if database_url:
            logging.info("Connecting to database via DATABASE_URL")
            conn = psycopg2.connect(database_url)
            logging.info("Database connection established successfully")
            return conn
        else:
            logging.error("DATABASE_URL not found in environment variables")
            return None
            
    except Exception as e:
        logging.error(f"Database connection error: {e}")
        return None

def init_database():
    logging.info("Initializing database...")
    conn = get_db_connection()
    if conn:
        try:
            cursor = conn.cursor()
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS students (
                    id SERIAL PRIMARY KEY,
                    telegram_id BIGINT UNIQUE NOT NULL,
                    telegram_username VARCHAR(255),
                    telegram_first_name VARCHAR(255),
                    telegram_last_name VARCHAR(255),
                    preferred_name VARCHAR(255),
                    is_anonymous BOOLEAN DEFAULT FALSE,
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
                    telegram_id BIGINT,
                    question TEXT,
                    answer TEXT,
                    category VARCHAR(50),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS admin_replies (
                    id SERIAL PRIMARY KEY,
                    admin_id BIGINT,
                    target_user_id BIGINT,
                    admin_message TEXT,
                    user_response TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    responded_at TIMESTAMP
                )
            ''')
            
            conn.commit()
            cursor.close()
            conn.close()
            logging.info("Database initialized successfully")
            return True
        except Exception as e:
            logging.error(f"Database initialization error: {e}")
            conn.close()
            return False
    else:
        logging.error("Could not initialize database - no connection")
        return False

def save_student_profile(profile_data):
    logging.info(f"Saving profile for user {profile_data.get('telegram_id')}")
    conn = get_db_connection()
    if conn:
        try:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO students (
                    telegram_id, telegram_username, telegram_first_name, 
                    telegram_last_name, preferred_name, is_anonymous, user_language, 
                    user_age, user_gender, user_birthplace, user_family_status, 
                    user_course, user_specialty, user_housing_type, profile_completed
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (telegram_id) 
                DO UPDATE SET
                    telegram_username = EXCLUDED.telegram_username,
                    telegram_first_name = EXCLUDED.telegram_first_name,
                    telegram_last_name = EXCLUDED.telegram_last_name,
                    preferred_name = EXCLUDED.preferred_name,
                    is_anonymous = EXCLUDED.is_anonymous,
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
                profile_data.get('preferred_name'), profile_data.get('is_anonymous', False),
                profile_data.get('user_language'), profile_data.get('user_age'),
                profile_data.get('user_gender'), profile_data.get('user_birthplace'),
                profile_data.get('user_family_status'), profile_data.get('user_course'),
                profile_data.get('user_specialty'), profile_data.get('user_housing_type'),
                profile_data.get('profile_completed', False)
            ))
            conn.commit()
            cursor.close()
            conn.close()
            logging.info("Profile saved successfully")
            return True
        except Exception as e:
            logging.error(f"Error saving profile: {e}")
            conn.close()
            return False
    return False

def get_student_by_id(telegram_id):
    conn = get_db_connection()
    if conn:
        try:
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            cursor.execute('SELECT * FROM students WHERE telegram_id = %s', (telegram_id,))
            result = cursor.fetchone()
            cursor.close()
            conn.close()
            return dict(result) if result else None
        except Exception as e:
            logging.error(f"Error getting student: {e}")
            conn.close()
            return None
    return None

def save_conversation(telegram_id, question, answer, category=None):
    conn = get_db_connection()
    if conn:
        try:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO conversations (telegram_id, question, answer, category)
                VALUES (%s, %s, %s, %s)
            ''', (telegram_id, question, answer, category))
            conn.commit()
            cursor.close()
            conn.close()
            logging.info("Conversation saved")
        except Exception as e:
            logging.error(f"Error saving conversation: {e}")
            conn.close()

def save_admin_reply(admin_id, target_user_id, admin_message):
    conn = get_db_connection()
    if conn:
        try:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO admin_replies (admin_id, target_user_id, admin_message)
                VALUES (%s, %s, %s) RETURNING id
            ''', (admin_id, target_user_id, admin_message))
            reply_id = cursor.fetchone()[0]
            conn.commit()
            cursor.close()
            conn.close()
            return reply_id
        except Exception as e:
            logging.error(f"Error saving admin reply: {e}")
            conn.close()
            return None
    return None

def update_admin_reply_response(reply_id, user_response):
    conn = get_db_connection()
    if conn:
        try:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE admin_replies 
                SET user_response = %s, responded_at = CURRENT_TIMESTAMP 
                WHERE id = %s
            ''', (user_response, reply_id))
            conn.commit()
            cursor.close()
            conn.close()
        except Exception as e:
            logging.error(f"Error updating admin reply: {e}")
            conn.close()

# Функции создания меню
def create_language_menu():
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(types.InlineKeyboardButton("🇰🇿 Қазақша", callback_data="lang_kz"))
    markup.add(types.InlineKeyboardButton("🇷🇺 Русский", callback_data="lang_ru"))
    markup.add(types.InlineKeyboardButton("🇺🇸 English", callback_data="lang_en"))
    return markup

def create_name_preference_menu(language):
    markup = types.InlineKeyboardMarkup(row_width=1)
    
    if language == "kz":
        markup.add(types.InlineKeyboardButton("✍️ Атымды жазу", callback_data="name_custom"))
        markup.add(types.InlineKeyboardButton("🎭 Анонимды қалу", callback_data="name_anonymous"))
    elif language == "en":
        markup.add(types.InlineKeyboardButton("✍️ Enter my name", callback_data="name_custom"))
        markup.add(types.InlineKeyboardButton("🎭 Stay anonymous", callback_data="name_anonymous"))
    else:
        markup.add(types.InlineKeyboardButton("✍️ Написать имя", callback_data="name_custom"))
        markup.add(types.InlineKeyboardButton("🎭 Остаться анонимным", callback_data="name_anonymous"))
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
    
    markup.add(types.InlineKeyboardButton("🔙 Назад к меню", callback_data="back_to_menu"))
    return markup

def get_text(language, key):
    texts = {
        'language_select': {
            'kz': '🌐 Тілді таңдаңыз:',
            'ru': '🌐 Выберите язык:',
            'en': '🌐 Choose language:'
        },
        'name_preference': {
            'kz': '👋 Сізге қалай қаратылуын қалайсыз?',
            'ru': '👋 Как к вам обращаться?',
            'en': '👋 How would you like to be addressed?'
        },
        'name_input': {
            'kz': '✍️ Атыңызды жазыңыз:',
            'ru': '✍️ Введите ваше имя:',
            'en': '✍️ Enter your name:'
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

# КОМАНДЫ
@bot.message_handler(commands=['start'])
def start_command(message):
    logging.info(f"Start command from user {message.from_user.id}")
    
    student = get_student_by_id(message.from_user.id)
    
    if student and student.get('profile_completed'):
        logging.info(f"User {message.from_user.id} already has completed profile")
        language = student.get('user_language', 'ru')
        markup = create_category_menu(language)
        bot.reply_to(message, get_text(language, 'profile_complete'), reply_markup=markup)
    else:
        logging.info(f"Starting registration for user {message.from_user.id}")
        user_states[message.from_user.id] = UserState.LANGUAGE
        
        temp_profiles[message.from_user.id] = {
            'telegram_id': message.from_user.id,
            'telegram_username': message.from_user.username,
            'telegram_first_name': message.from_user.first_name,
            'telegram_last_name': message.from_user.last_name,
            'profile_completed': False
        }
        
        markup = create_language_menu()
        bot.reply_to(message, get_text('en', 'language_select'), reply_markup=markup)

@bot.message_handler(commands=['admin'])
def admin_command(message):
    if message.from_user.id not in ADMIN_IDS:
        bot.reply_to(message, "❌ У вас нет доступа к админской панели")
        return
    
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("📊 Статистика", callback_data="admin_stats"),
        types.InlineKeyboardButton("📈 Детальная статистика", callback_data="admin_detailed_stats")
    )
    markup.add(
        types.InlineKeyboardButton("👥 Список студентов", callback_data="admin_users"),
        types.InlineKeyboardButton("💬 История диалогов", callback_data="admin_conversations")
    )
    
    bot.reply_to(message, "🛠️ Админская панель:", reply_markup=markup)

# ОБРАБОТЧИКИ CALLBACK'ОВ
@bot.callback_query_handler(func=lambda call: call.data.startswith('lang_'))
def handle_language_selection(call):
    logging.info(f"Language selection: {call.data} from user {call.from_user.id}")
    bot.answer_callback_query(call.id)
    
    language = call.data.split('_')[1]
    user_id = call.from_user.id
    
    if user_id not in temp_profiles:
        temp_profiles[user_id] = {
            'telegram_id': user_id,
            'telegram_username': call.from_user.username,
            'telegram_first_name': call.from_user.first_name,
            'telegram_last_name': call.from_user.last_name,
        }
    
    temp_profiles[user_id]['user_language'] = language
    user_states[user_id] = UserState.PREFERRED_NAME
    
    markup = create_name_preference_menu(language)
    bot.edit_message_text(
        get_text(language, 'name_preference'),
        call.message.chat.id,
        call.message.message_id,
        reply_markup=markup
    )

@bot.callback_query_handler(func=lambda call: call.data.startswith('name_'))
def handle_name_preference(call):
    bot.answer_callback_query(call.id)
    
    preference = call.data.split('_')[1]
    user_id = call.from_user.id
    language = temp_profiles[user_id].get('user_language', 'ru')
    
    if preference == "anonymous":
        temp_profiles[user_id]['is_anonymous'] = True
        temp_profiles[user_id]['preferred_name'] = "Анонимный пользователь"
        user_states[user_id] = UserState.AGE
        
        bot.edit_message_text(
            get_text(language, 'age_request'),
            call.message.chat.id,
            call.message.message_id
        )
    else:  # custom name
        temp_profiles[user_id]['is_anonymous'] = False
        user_states[user_id] = UserState.PREFERRED_NAME
        
        bot.edit_message_text(
            get_text(language, 'name_input'),
            call.message.chat.id,
            call.message.message_id
        )

@bot.callback_query_handler(func=lambda call: call.data.startswith('gender_'))
def handle_gender_selection(call):
    bot.answer_callback_query(call.id)
    
    gender = call.data.split('_')[1]
    user_id = call.from_user.id
    
    temp_profiles[user_id]['user_gender'] = gender
    user_states[user_id] = UserState.BIRTHPLACE
    
    language = temp_profiles[user_id].get('user_language', 'ru')
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
    user_id = call.from_user.id
    
    temp_profiles[user_id]['user_birthplace'] = birthplace
    user_states[user_id] = UserState.FAMILY
    
    language = temp_profiles[user_id].get('user_language', 'ru')
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
    user_id = call.from_user.id
    
    temp_profiles[user_id]['user_family_status'] = family
    user_states[user_id] = UserState.COURSE
    
    language = temp_profiles[user_id].get('user_language', 'ru')
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
    user_id = call.from_user.id
    
    temp_profiles[user_id]['user_course'] = int(course)
    user_states[user_id] = UserState.SPECIALTY
    
    language = temp_profiles[user_id].get('user_language', 'ru')
    
    bot.edit_message_text(
        get_text(language, 'specialty_request'),
        call.message.chat.id,
        call.message.message_id
    )

@bot.callback_query_handler(func=lambda call: call.data.startswith('housing_'))
def handle_housing_selection(call):
    bot.answer_callback_query(call.id)
    
    housing = call.data.split('_')[1]
    user_id = call.from_user.id
    
    temp_profiles[user_id]['user_housing_type'] = housing
    temp_profiles[user_id]['profile_completed'] = True
    
    if save_student_profile(temp_profiles[user_id]):
        logging.info(f"Profile saved for user {user_id}")
        send_profile_to_admin(temp_profiles[user_id])
    
    user_states[user_id] = UserState.COMPLETED
    
    language = temp_profiles[user_id].get('user_language', 'ru')
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

@bot.callback_query_handler(func=lambda call: any(cat in call.data for cat in ['finance_', 'study_', 'social_', 'family_', 'household_', 'career_']))
def handle_category_selection(call):
    bot.answer_callback_query(call.id)
    
    parts = call.data.split('_')
    category = parts[0]
    
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
        
        send_to_shai_pro(category_messages[category], call.from_user, call.message.chat, category)

# АДМИНСКИЕ ОБРАБОТЧИКИ
@bot.callback_query_handler(func=lambda call: call.data.startswith('admin_'))
def handle_admin_commands(call):
    if call.from_user.id not in ADMIN_IDS:
        bot.answer_callback_query(call.id, "Нет доступа")
        return
    
    bot.answer_callback_query(call.id)
    
    if call.data == "admin_stats":
        show_statistics(call.message)
    elif call.data == "admin_detailed_stats":
        show_detailed_statistics(call.message)
    elif call.data == "admin_users":
        show_users_list(call.message)
    elif call.data == "admin_conversations":
        show_conversations_history(call.message)
    elif call.data == "admin_back":
        admin_command(call.message)

def show_detailed_statistics(message):
    conn = get_db_connection()
    if not conn:
        try:
            bot.edit_message_text("❌ Ошибка подключения к БД", message.chat.id, message.message_id)
        except:
            bot.send_message(message.chat.id, "❌ Ошибка подключения к БД")
        return
    
    try:
        cursor = conn.cursor()
        
        # Общая статистика
        cursor.execute("SELECT COUNT(*) FROM students WHERE profile_completed = TRUE")
        total_students = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM conversations")
        total_conversations = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM admin_replies")
        total_admin_replies = cursor.fetchone()[0]
        
        # По регионам
        cursor.execute("""
            SELECT user_birthplace, COUNT(*) as count 
            FROM students WHERE profile_completed = TRUE 
            GROUP BY user_birthplace 
            ORDER BY count DESC 
            LIMIT 5
        """)
        regions_stats = cursor.fetchall()
        
        # По полу
        cursor.execute("SELECT user_gender, COUNT(*) FROM students WHERE profile_completed = TRUE GROUP BY user_gender")
        gender_stats = cursor.fetchall()
        
        # По типу жилья
        cursor.execute("SELECT user_housing_type, COUNT(*) FROM students WHERE profile_completed = TRUE GROUP BY user_housing_type")
        housing_stats = cursor.fetchall()
        
        # По семейному статусу
        cursor.execute("SELECT user_family_status, COUNT(*) FROM students WHERE profile_completed = TRUE GROUP BY user_family_status")
        family_stats = cursor.fetchall()
        
        # По категориям вопросов
        cursor.execute("SELECT category, COUNT(*) FROM conversations WHERE category IS NOT NULL GROUP BY category ORDER BY COUNT(*) DESC")
        category_stats = cursor.fetchall()
        
        # Анонимные пользователи
        cursor.execute("SELECT COUNT(*) FROM students WHERE is_anonymous = TRUE AND profile_completed = TRUE")
        anonymous_count = cursor.fetchone()[0]
        
        cursor.close()
        conn.close()
        
        # Формируем отчет
        text = f"📊 ДЕТАЛЬНАЯ СТАТИСТИКА\n\n"
        text += f"👥 Всего студентов: {total_students}\n"
        text += f"💬 Всего диалогов: {total_conversations}\n"
        text += f"📧 Ответов админов: {total_admin_replies}\n"
        text += f"🎭 Анонимных: {anonymous_count}\n\n"
        
        # Топ регионов
        if regions_stats:
            text += f"🏙️ Топ регионов:\n"
            region_names = {
                'astana': 'Астана', 'almaty': 'Алма-Ата', 'shymkent': 'Шымкент',
                'akmola': 'Акмолинская', 'almaty_region': 'Алматинская'
            }
            for region, count in regions_stats:
                region_name = region_names.get(region, region.replace('_', ' ').title())
                text += f"   {region_name}: {count}\n"
            text += "\n"
        
        # По полу
        if gender_stats:
            text += f"⚧️ По полу:\n"
            gender_names = {'male': 'Мужской', 'female': 'Женский'}
            for gender, count in gender_stats:
                gender_name = gender_names.get(gender, gender)
                text += f"   {gender_name}: {count}\n"
            text += "\n"
        
        # По жилью
        if housing_stats:
            text += f"🏠 Тип жилья:\n"
            housing_names = {'dormitory': 'Общежитие', 'rent': 'Аренда', 'own': 'Собственное'}
            for housing, count in housing_stats:
                housing_name = housing_names.get(housing, housing)
                text += f"   {housing_name}: {count}\n"
            text += "\n"
        
        # Популярные категории
        if category_stats:
            text += f"📈 Популярные категории:\n"
            category_names = {
                'finance': 'Финансы', 'study': 'Учеба', 'social': 'Социальные',
                'family': 'Семья', 'household': 'Быт', 'career': 'Карьера'
            }
            for category, count in category_stats:
                category_name = category_names.get(category, category)
                text += f"   {category_name}: {count}\n"
        
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("🔙 Назад", callback_data="admin_back"))
        
        try:
            bot.edit_message_text(text, message.chat.id, message.message_id, reply_markup=markup)
        except:
            bot.send_message(message.chat.id, text, reply_markup=markup)
        
    except Exception as e:
        logging.error(f"Error in detailed stats: {e}")
        try:
            bot.edit_message_text("❌ Ошибка получения статистики", message.chat.id, message.message_id)
        except:
            bot.send_message(message.chat.id, "❌ Ошибка получения статистики")

def show_users_list(message, page=1):
    conn = get_db_connection()
    if not conn:
        try:
            bot.edit_message_text("❌ Ошибка подключения к БД", message.chat.id, message.message_id)
        except:
            bot.send_message(message.chat.id, "❌ Ошибка подключения к БД")
        return
    
    try:
        cursor = conn.cursor()
        offset = (page - 1) * 5
        
        cursor.execute('''
            SELECT telegram_id, preferred_name, is_anonymous, user_course, 
                   user_specialty, registration_date, last_activity
            FROM students 
            WHERE profile_completed = TRUE 
            ORDER BY last_activity DESC 
            LIMIT 5 OFFSET %s
        ''', (offset,))
        users = cursor.fetchall()
        
        cursor.execute("SELECT COUNT(*) FROM students WHERE profile_completed = TRUE")
        total_users = cursor.fetchone()[0]
        
        cursor.close()
        conn.close()
        
        if not users:
            text = "Нет зарегистрированных студентов"
        else:
            text = f"👥 Студенты (стр. {page}):\n\n"
            
            for user in users:
                telegram_id, preferred_name, is_anonymous, course, specialty, reg_date, last_activity = user
                
                if is_anonymous:
                    name = "🎭 Анонимный"
                else:
                    name = preferred_name or "Без имени"
                
                text += f"👤 {name}\n"
                text += f"ID: {telegram_id}\n"
                text += f"Курс: {course or '?'}\n"
                text += f"Специальность: {specialty or 'Не указано'}\n"
                text += f"Последняя активность: {last_activity.strftime('%d.%m %H:%M')}\n"
                text += f"📧 Ответить: /reply_{telegram_id}\n\n"
        
        markup = types.InlineKeyboardMarkup(row_width=2)
        
        # Навигация
        nav_buttons = []
        if page > 1:
            nav_buttons.append(types.InlineKeyboardButton("⬅️", callback_data=f"users_page_{page-1}"))
        if len(users) == 5 and (page * 5) < total_users:
            nav_buttons.append(types.InlineKeyboardButton("➡️", callback_data=f"users_page_{page+1}"))
        
        if nav_buttons:
            markup.add(*nav_buttons)
        
        markup.add(types.InlineKeyboardButton("🔙 Назад", callback_data="admin_back"))
        
        try:
            bot.edit_message_text(text, message.chat.id, message.message_id, reply_markup=markup)
        except:
            bot.send_message(message.chat.id, text, reply_markup=markup)
        
    except Exception as e:
        logging.error(f"Error in users list: {e}")
        try:
            bot.edit_message_text("❌ Ошибка получения списка", message.chat.id, message.message_id)
        except:
            bot.send_message(message.chat.id, "❌ Ошибка получения списка")

@bot.callback_query_handler(func=lambda call: call.data.startswith('users_page_'))
def handle_users_pagination(call):
    if call.from_user.id not in ADMIN_IDS:
        return
    
    bot.answer_callback_query(call.id)
    page = int(call.data.split('_')[-1])
    show_users_list(call.message, page)

def show_conversations_history(message):
    conn = get_db_connection()
    if not conn:
        try:
            bot.edit_message_text("❌ Ошибка подключения к БД", message.chat.id, message.message_id)
        except:
            bot.send_message(message.chat.id, "❌ Ошибка подключения к БД")
        return
    
    try:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT c.telegram_id, s.preferred_name, s.is_anonymous, c.question, 
                   c.answer, c.category, c.created_at
            FROM conversations c
            JOIN students s ON c.telegram_id = s.telegram_id
            ORDER BY c.created_at DESC
            LIMIT 5
        ''')
        conversations = cursor.fetchall()
        
        cursor.close()
        conn.close()
        
        if not conversations:
            text = "Нет диалогов"
        else:
            text = "💬 Последние диалоги:\n\n"
            
            for conv in conversations:
                telegram_id, preferred_name, is_anonymous, question, answer, category, created_at = conv
                
                if is_anonymous:
                    name = "🎭 Анонимный"
                else:
                    name = preferred_name or "Без имени"
                
                text += f"👤 {name} (ID: {telegram_id})\n"
                text += f"❓ {question[:50]}{'...' if len(question) > 50 else ''}\n"
                text += f"🤖 {answer[:50]}{'...' if len(answer) > 50 else ''}\n"
                text += f"📅 {created_at.strftime('%d.%m %H:%M')}\n"
                text += f"📧 Ответить: /reply_{telegram_id}\n\n"
        
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("🔙 Назад", callback_data="admin_back"))
        
        try:
            bot.edit_message_text(text, message.chat.id, message.message_id, reply_markup=markup)
        except:
            bot.send_message(message.chat.id, text, reply_markup=markup)
        
    except Exception as e:
        logging.error(f"Error in conversations history: {e}")
        try:
            bot.edit_message_text("❌ Ошибка получения истории", message.chat.id, message.message_id)
        except:
            bot.send_message(message.chat.id, "❌ Ошибка получения истории")

# ОБРАБОТКА ОТВЕТОВ АДМИНОВ
@bot.message_handler(func=lambda message: message.text and message.text.startswith('/reply_') and message.from_user.id in ADMIN_IDS)
def handle_admin_reply_command(message):
    try:
        target_user_id = int(message.text.split('_')[1])
        admin_states[message.from_user.id] = AdminState.REPLYING
        reply_contexts[message.from_user.id] = target_user_id
        
        student = get_student_by_id(target_user_id)
        if student:
            name = "Анонимный пользователь" if student.get('is_anonymous') else (student.get('preferred_name') or "Без имени")
            bot.reply_to(message, f"💬 Ответ пользователю {name} (ID: {target_user_id})\n\nВведите ваше сообщение:")
        else:
            bot.reply_to(message, "Пользователь не найден")
    except (ValueError, IndexError):
        bot.reply_to(message, "Неверный формат команды")

# ОБРАБОТКА ТЕКСТОВЫХ СООБЩЕНИЙ
@bot.message_handler(func=lambda message: True)
def handle_message(message):
    user_id = message.from_user.id
    
    # Проверяем, отвечает ли админ пользователю
    if user_id in ADMIN_IDS and user_id in admin_states and admin_states[user_id] == AdminState.REPLYING:
        target_user_id = reply_contexts.get(user_id)
        if target_user_id:
            try:
                bot.send_message(target_user_id, f"📩 Сообщение от поддержки:\n\n{message.text}")
                
                # Сохраняем в БД
                reply_id = save_admin_reply(user_id, target_user_id, message.text)
                
                # Уведомляем админа
                bot.reply_to(message, "✅ Сообщение отправлено пользователю")
                
                # Очищаем состояние
                admin_states[user_id] = AdminState.IDLE
                if user_id in reply_contexts:
                    del reply_contexts[user_id]
                
            except Exception as e:
                bot.reply_to(message, f"❌ Ошибка отправки: {e}")
        return
    
    logging.info(f"Message from user {user_id}: '{message.text}'")
    logging.info(f"User state: {user_states.get(user_id, 'None')}")
    
    # Проверяем, отвечает ли пользователь на сообщение поддержки
    if user_id not in user_states and message.reply_to_message and "Сообщение от поддержки" in message.reply_to_message.text:
        student = get_student_by_id(user_id)
        if student:
            name = "Анонимный пользователь" if student.get('is_anonymous') else (student.get('preferred_name') or "Без имени")
            
            admin_notification = f"""
📨 ОТВЕТ НА СООБЩЕНИЕ ПОДДЕРЖКИ

👤 От: {name}
🆔 ID: {user_id}
📧 Ответить: /reply_{user_id}

💬 Ответ:
{message.text}

━━━━━━━━━━━━━━━━━━
"""
            try:
                bot.send_message(ADMIN_GROUP_ID, admin_notification)
                logging.info(f"Admin notification sent for user {user_id}")
            except Exception as e:
                logging.error(f"Error sending admin notification: {e}")
        return
    
    # Обработка состояний регистрации
    if user_id in user_states:
        state = user_states[user_id]
        
        if state == UserState.PREFERRED_NAME:
            if user_id in temp_profiles and not temp_profiles[user_id].get('is_anonymous', False):
                temp_profiles[user_id]['preferred_name'] = message.text
                user_states[user_id] = UserState.AGE
                
                language = temp_profiles[user_id].get('user_language', 'ru')
                bot.reply_to(message, get_text(language, 'age_request'))
            else:
                language = temp_profiles.get(user_id, {}).get('user_language', 'ru')
                bot.reply_to(message, "Пожалуйста, используйте кнопки для выбора")
                
        elif state == UserState.AGE:
            try:
                age = int(message.text.strip())
                if 16 <= age <= 35:
                    if user_id in temp_profiles:
                        temp_profiles[user_id]['user_age'] = age
                        user_states[user_id] = UserState.GENDER
                        
                        language = temp_profiles[user_id].get('user_language', 'ru')
                        markup = create_gender_menu(language)
                        bot.reply_to(message, get_text(language, 'gender_request'), reply_markup=markup)
                    else:
                        bot.reply_to(message, "Ошибка. Начните заново с /start")
                else:
                    language = temp_profiles.get(user_id, {}).get('user_language', 'ru')
                    bot.reply_to(message, get_text(language, 'age_invalid'))
            except ValueError:
                language = temp_profiles.get(user_id, {}).get('user_language', 'ru')
                bot.reply_to(message, get_text(language, 'age_invalid'))
                
        elif state == UserState.SPECIALTY:
            if user_id in temp_profiles:
                temp_profiles[user_id]['user_specialty'] = message.text
                user_states[user_id] = UserState.HOUSING
                
                language = temp_profiles[user_id].get('user_language', 'ru')
                markup = create_housing_menu(language)
                bot.reply_to(message, get_text(language, 'housing_request'), reply_markup=markup)
            else:
                bot.reply_to(message, "Ошибка. Начните заново с /start")
        
        else:
            # Для всех остальных состояний, которые требуют кнопок
            language = temp_profiles.get(user_id, {}).get('user_language', 'ru')
            if state in [UserState.LANGUAGE, UserState.GENDER, UserState.BIRTHPLACE, UserState.FAMILY, UserState.COURSE, UserState.HOUSING]:
                bot.reply_to(message, "Пожалуйста, используйте кнопки для выбора")
            else:
                # Если пользователь завершил регистрацию
                student = get_student_by_id(user_id)
                if student and student.get('profile_completed'):
                    send_to_shai_pro(message.text, message.from_user, message.chat)
                else:
                    start_command(message)
    
    else:
        # Пользователь не в процессе регистрации
        student = get_student_by_id(user_id)
        
        if student and student.get('profile_completed'):
            send_to_shai_pro(message.text, message.from_user, message.chat)
        else:
            start_command(message)

# SHAI.PRO ИНТЕГРАЦИЯ
def send_to_shai_pro(text, user, chat, category=None):
    logging.info(f"Sending to shai.pro: {text[:50]}... from user {user.id}")
    
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
        
        logging.info(f"Shai.pro response status: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            answer = result.get('answer', '')
            
            if not answer or answer.strip() == '':
                answer = "Извините, не смог сформировать ответ. Попробуйте переформулировать вопрос."
            
            if len(answer) > 4096:
                answer = answer[:4090] + "..."
            
            save_conversation(user.id, text, answer, category)
            
            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton("🔙 Назад к меню", callback_data="back_to_menu"))
            
            bot.send_message(chat.id, answer, reply_markup=markup)
            send_conversation_report(user, text, answer, category)
            
        else:
            bot.send_message(chat.id, f"Произошла ошибка обработки запроса. Код: {response.status_code}")
            
    except requests.Timeout:
        bot.send_message(chat.id, "Превышено время ожидания ответа. Попробуйте еще раз.")
    except Exception as e:
        logging.error(f"Shai.pro request error: {e}")
        bot.send_message(chat.id, "Произошла техническая ошибка. Попробуйте позже.")

def send_conversation_report(user, question, answer, category):
    try:
        logging.info(f"Attempting to send conversation report for user {user.id}")
        
        student = get_student_by_id(user.id)
        if not student:
            logging.warning(f"No student found for user {user.id}")
            return
            
        if student.get('is_anonymous'):
            name = "🎭 Анонимный пользователь"
        else:
            name = student.get('preferred_name') or "Без имени"
        
        category_names = {
            'finance': '💰 Финансовые проблемы',
            'study': '📚 Учебные трудности',
            'social': '😰 Социальные страхи',
            'family': '👨‍👩‍👧‍👦 Семья и окружение',
            'household': '🏠 Бытовые проблемы',
            'career': '🎯 Профориентация'
        }
        
        report = f"""
💬 НОВЫЙ ДИАЛОГ

👤 От: {name}
🆔 ID: {user.id}
📂 Категория: {category_names.get(category, 'Общий вопрос')}
🕐 Время: {datetime.now().strftime("%d.%m.%Y %H:%M")}
📧 Ответить: /reply_{user.id}

❓ Вопрос:
{question}

🤖 Ответ:
{answer[:300]}{'...' if len(answer) > 300 else ''}

━━━━━━━━━━━━━━━━━━
"""
        
        bot.send_message(ADMIN_GROUP_ID, report)
        logging.info("Conversation report sent to admin group successfully")
        
    except Exception as e:
        logging.error(f"Ошибка отправки отчета: {e}")

def send_profile_to_admin(profile):
    try:
        logging.info(f"Attempting to send profile to admin group for user {profile.get('telegram_id')}")
        
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
        
        if profile.get('is_anonymous'):
            display_name = "🎭 Анонимный пользователь"
        else:
            display_name = profile.get('preferred_name') or "Без имени"
        
        report = f"""
📋 НОВЫЙ СТУДЕНТ ЗАРЕГИСТРИРОВАН

👤 Имя: {display_name}
🆔 Telegram ID: {profile.get('telegram_id')}
📞 Username: @{profile.get('telegram_username', 'не указан')}
🎂 Возраст: {profile.get('user_age')}
⚧️ Пол: {gender_names.get(profile.get('user_gender'), 'Не указано')}
🏙️ Место рождения: {region_names.get(profile.get('user_birthplace'), 'Не указано')}
👨‍👩‍👧‍👦 Семья: {family_names.get(profile.get('user_family_status'), 'Не указано')}
📚 Курс: {profile.get('user_course')} курс
🎓 Специальность: {profile.get('user_specialty')}
🏠 Жилье: {housing_names.get(profile.get('user_housing_type'), 'Не указано')}
🌐 Язык: {profile.get('user_language', 'ru').upper()}
🕐 Время регистрации: {datetime.now().strftime("%d.%m.%Y %H:%M")}
📧 Написать: /reply_{profile.get('telegram_id')}

━━━━━━━━━━━━━━━━━━
"""
        
        bot.send_message(ADMIN_GROUP_ID, report)
        logging.info("Profile report sent to admin group successfully")
        
    except Exception as e:
        logging.error(f"Ошибка отправки профиля админам: {e}")

def show_statistics(message):
    conn = get_db_connection()
    if not conn:
        try:
            bot.edit_message_text("❌ Ошибка подключения к БД", message.chat.id, message.message_id)
        except:
            bot.send_message(message.chat.id, "❌ Ошибка подключения к БД")
        return
    
    try:
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*) FROM students WHERE profile_completed = TRUE")
        total_students = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM conversations")
        total_conversations = cursor.fetchone()[0]
        
        cursor.execute("SELECT user_course, COUNT(*) FROM students WHERE profile_completed = TRUE GROUP BY user_course ORDER BY user_course")
        courses_stats = cursor.fetchall()
        
        cursor.close()
        conn.close()
        
        text = f"📊 СТАТИСТИКА СТУДЕНТОВ\n\n"
        text += f"👥 Всего зарегистрировано: {total_students}\n"
        text += f"💬 Всего диалогов: {total_conversations}\n\n"
        
        if courses_stats:
            text += f"📚 По курсам:\n"
            for course, count in courses_stats:
                text += f"   {course} курс: {count} чел.\n"
        
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("🔙 Назад", callback_data="admin_back"))
        
        try:
            bot.edit_message_text(text, message.chat.id, message.message_id, reply_markup=markup)
        except:
            bot.send_message(message.chat.id, text, reply_markup=markup)
        
    except Exception as e:
        logging.error(f"Error showing statistics: {e}")
        try:
            bot.edit_message_text("❌ Ошибка получения статистики", message.chat.id, message.message_id)
        except:
            bot.send_message(message.chat.id, "❌ Ошибка получения статистики")

@bot.callback_query_handler(func=lambda call: call.data == "admin_back")
def admin_back(call):
    if call.from_user.id not in ADMIN_IDS:
        return
    
    bot.answer_callback_query(call.id)
    admin_command(call.message)

# ИНИЦИАЛИЗАЦИЯ И ЗАПУСК
if __name__ == "__main__":
    logging.info("Starting bot initialization...")
    
    database_url = os.environ.get('DATABASE_URL')
    if not database_url:
        logging.error("DATABASE_URL not found")
        logging.error("Starting bot without database for testing...")
        
        # Заглушки для функций БД
        def save_student_profile(profile_data):
            logging.info(f"Would save profile for {profile_data.get('telegram_id')}")
            return True

        def get_student_by_id(telegram_id):
            return None

        def save_conversation(telegram_id, question, answer, category=None):
            logging.info(f"Would save conversation for {telegram_id}")

        def save_admin_reply(admin_id, target_user_id, admin_message):
            logging.info(f"Would save admin reply from {admin_id} to {target_user_id}")
            return 1

        def update_admin_reply_response(reply_id, user_response):
            logging.info(f"Would update admin reply {reply_id}")

        # Переопределяем глобальные функции
        globals()['save_student_profile'] = save_student_profile
        globals()['get_student_by_id'] = get_student_by_id
        globals()['save_conversation'] = save_conversation
        globals()['save_admin_reply'] = save_admin_reply
        globals()['update_admin_reply_response'] = update_admin_reply_response
        
        logging.info("Bot started successfully (without database)")
        try:
            bot.polling(none_stop=True, interval=0)
        except Exception as e:
            logging.error(f"Polling error: {e}")
    else:
        logging.info(f"DATABASE_URL found: {database_url[:30]}...")
        
        if init_database():
            logging.info("Bot started successfully with database")
            try:
                bot.polling(none_stop=True, interval=0)
            except Exception as e:
                logging.error(f"Polling error: {e}")
        else:
            logging.error("Failed to initialize database")