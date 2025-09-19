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

# Функции создания меню
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
    
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(types.InlineKeyboardButton("📊 Статистика", callback_data="admin_stats"))
    
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
    user_states[user_id] = UserState.AGE
    
    logging.info(f"Set user {user_id} state to AGE, language to {language}")
    
    bot.edit_message_text(
        get_text(language, 'age_request'),
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

@bot.callback_query_handler(func=lambda call: call.data == "admin_stats")
def handle_admin_stats(call):
    if call.from_user.id not in ADMIN_IDS:
        return
    
    bot.answer_callback_query(call.id)
    show_statistics(call.message)

# ОБРАБОТКА ТЕКСТОВЫХ СООБЩЕНИЙ
@bot.message_handler(func=lambda message: True)
def handle_message(message):
    user_id = message.from_user.id
    
    logging.info(f"Message from user {user_id}: '{message.text}'")
    logging.info(f"User state: {user_states.get(user_id, 'None')}")
    
    if user_id in user_states:
        state = user_states[user_id]
        
        if state == UserState.AGE:
            logging.info(f"Processing age input: {message.text}")
            try:
                age = int(message.text.strip())
                if 16 <= age <= 35:
                    logging.info(f"Valid age {age} for user {user_id}")
                    
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
            logging.info(f"Processing specialty input: {message.text}")
            
            if user_id in temp_profiles:
                temp_profiles[user_id]['user_specialty'] = message.text
                user_states[user_id] = UserState.HOUSING
                
                language = temp_profiles[user_id].get('user_language', 'ru')
                markup = create_housing_menu(language)
                bot.reply_to(message, get_text(language, 'housing_request'), reply_markup=markup)
            else:
                bot.reply_to(message, "Ошибка. Начните заново с /start")
        
        else:
            bot.reply_to(message, "Пожалуйста, используйте кнопки для выбора")
    
    else:
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
            
            student = get_student_by_id(user.id)
            language = student.get('user_language', 'ru') if student else 'ru'
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
        logging.info("Profile report sent to admin group")
        
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
    
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(types.InlineKeyboardButton("📊 Статистика", callback_data="admin_stats"))
    
    try:
        bot.edit_message_text("🛠️ Админская панель:", call.message.chat.id, call.message.message_id, reply_markup=markup)
    except:
        bot.send_message(call.message.chat.id, "🛠️ Админская панель:", reply_markup=markup)

# ИНИЦИАЛИЗАЦИЯ И ЗАПУСК
if __name__ == "__main__":
    logging.info("Starting bot initialization...")
    
    # Проверяем DATABASE_URL вместо отдельных переменных
    if not os.environ.get('DATABASE_URL'):
        logging.error("DATABASE_URL not found")
        logging.error("Bot cannot start without database configuration")
    else:
        logging.info("DATABASE_URL found")
        
        if init_database():
            logging.info("Bot started successfully")
            try:
                bot.polling(none_stop=True, interval=0)
            except Exception as e:
                logging.error(f"Polling error: {e}")
        else:
            logging.error("Failed to initialize database")