import logging
import aiogram
import psycopg2
import asyncio
print('привет')
from docxtpl import DocxTemplate
import os

from aiogram import Bot, Dispatcher, types,Router,F 
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.context import FSMContext
from aiogram.filters.state import State, StatesGroup
from aiogram.types import Message
from aiogram.filters import Command
from aiogram.utils.keyboard import ReplyKeyboardBuilder
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, ReplyKeyboardMarkup
from dotenv import load_dotenv
load_dotenv()


import requests
from typing import List, Tuple
from datetime import datetime

ACCESS_TOKEN = os.getenv("VK_API_TOKEN")
API_VERSION = "5.131"
API_TOKEN = os.getenv("TELEGRAM_BOT_API_KEY")




logging.basicConfig(level=logging.INFO,format="%(filename)s:%(lineno)d #%(levelname)-8s " "[%(asctime)s] - %(name)s - %(message)s")

bot = Bot(token=API_TOKEN)
async def main():
    dp = Dispatcher(storage=MemoryStorage())
    dp.include_router(router)
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())

router: Router=Router()
params = {
        'host': 'localhost',
        'port': 5432,
        'database': 'botCyberSup',
        'user': 'postgres',
        'password': 'parol'
     }
conn = psycopg2.connect(**params)

class Dialog(StatesGroup):
    addProjectId = State()    # Новое состояние для ID проекта
    addProjectName = State()  # Новое состояние для названия проекта
    deleteProject = State()
    deleteUser = State()
    selectCustomer = State()  # Новое состояние для выбора заказчика
    assignProjects = State()  # Новое состояние для назначения проектов
    # Новые состояния для статистики
    selectProject = State()
    startDate = State()
    endDate = State()

# Функция главного меню
async def send_main_menu(message: Message):
    cur = conn.cursor()
    cur.execute("SELECT role, chapter FROM users WHERE key = %s", (message.from_user.id,))
    user = cur.fetchone()
    
    if not user:
        await message.answer("❌ У вас нет доступа к боту.")
        return
    
    role, chapter = user
    keyboard = ReplyKeyboardBuilder()
    
    # Если пользователь заказчик, показываем только кнопку статистики
    if chapter == "Заказчик":
        keyboard.add(types.KeyboardButton(text='Статистика'))
    else:
        # Для сотрудников показываем все кнопки
        keyboard.add(types.KeyboardButton(text='Управление проектами'))
        keyboard.add(types.KeyboardButton(text='Управление пользователями'))
        keyboard.add(types.KeyboardButton(text='Статистика'))
    
    keyboard.adjust(2)
    await message.answer("🏠 Вы на главной странице.", 
                        reply_markup=keyboard.as_markup(resize_keyboard=True))

# Обработчик команды /start
@router.message(Command('start'))
async def start(message: Message):
    cur = conn.cursor()
    cur.execute("SELECT role, chapter FROM users WHERE key = %s", (message.from_user.id,))
    user = cur.fetchone()
    
    if not user:
        await message.answer("❌ У вас нет доступа к боту.")
        return
    
    role, chapter = user
    await message.answer(
        "👋 Добро пожаловать в бот для работы с рекламными кабинетами VK!", 
        reply_markup=main_keyboard(chapter)
    )

# Функция для главного меню
def main_keyboard(user_chapter: str = None) -> ReplyKeyboardMarkup:
    """Генерация главной клавиатуры в зависимости от роли пользователя"""
    keyboard = ReplyKeyboardBuilder()
    
    if user_chapter == "Заказчик":
        keyboard.add(types.KeyboardButton(text='Статистика'))
    else:
        keyboard.add(types.KeyboardButton(text='Управление проектами'))
        keyboard.add(types.KeyboardButton(text='Управление пользователями'))
        keyboard.add(types.KeyboardButton(text='Статистика'))
    
    keyboard.adjust(2)
    return keyboard.as_markup(resize_keyboard=True)

# Обработчик кнопки "На главную"
@router.message(F.text == 'На главную')
async def back_to_main(message: Message, state: FSMContext):
    await state.clear()
    cur = conn.cursor()
    cur.execute("SELECT role, chapter FROM users WHERE key = %s", (message.from_user.id,))
    user = cur.fetchone()
    
    if not user:
        await message.answer("❌ У вас нет доступа к боту.")
        return
    
    role, chapter = user
    await message.answer(
        "🏠 Вы на главной странице.", 
        reply_markup=main_keyboard(chapter)
    )

@router.message(F.text == 'Назад к управлению проектами')
async def back_to_project_management(message: Message, state: FSMContext):
    # Сначала очищаем состояние
    await state.clear()

    # Получаем список всех проектов из базы данных
    cur = conn.cursor()
    cur.execute('SELECT id, name FROM projects')
    projects = cur.fetchall()

    if not projects:
        await message.answer("❌ Нет добавленных проектов.", reply_markup=companies_keyboard())
        return

    response_text = "<b>📋 Список проектов:</b>\n\n"
    for idx, (project_id, project_name) in enumerate(projects, start=1):
        response_text += f"{idx}. 🏢 {project_name}\n"

    await message.answer(response_text.strip(), parse_mode="HTML", reply_markup=companies_keyboard())
    await message.answer('🔧 Выберите действие:', reply_markup=companies_keyboard())


@router.message(F.text == 'Назад к управлению пользователями')
async def back_to_user_management(message: Message, state: FSMContext):
    await state.clear()
    cur = conn.cursor()
    cur.execute("SELECT role FROM users WHERE key = %s", (message.from_user.id,))
    user = cur.fetchone()
    
    if not user or user[0] != "Суперадмин":
        await message.answer("❌ У вас нет доступа к этому разделу.")
        return
    
    keyboard = ReplyKeyboardBuilder()
    keyboard.add(types.KeyboardButton(text='Добавить пользователя'))
    keyboard.add(types.KeyboardButton(text='Удалить пользователя'))
    keyboard.add(types.KeyboardButton(text='Назначить проекты'))
    keyboard.add(types.KeyboardButton(text='Просмотр назначенных проектов'))  # Новая кнопка
    keyboard.add(types.KeyboardButton(text='На главную'))
    keyboard.adjust(1)

    cur.execute("SELECT key, name, role, chapter FROM users ORDER BY chapter, role")
    users = cur.fetchall()
    
    if not users:
        await message.answer("❌ В системе нет зарегистрированных пользователей.", 
                           reply_markup=keyboard.as_markup(resize_keyboard=True))
        return

    response = "👥 <b>Список пользователей:</b>\n\n"
    
    # Сотрудники
    response += "👨‍💼 <b>СОТРУДНИКИ:</b>\n"
    
    role_emojis = {
        "Суперадмин": "👑",
        "Леонидка": "⭐️",
        "Пользователь": "👤"
    }
    
    # Группируем сотрудников по ролям
    for role in ["Суперадмин", "Леонидка", "Пользователь"]:
        staff_in_role = [u for u in users if u[2] == role and u[3] == "Сотрудник"]
        if staff_in_role:
            response += f"   {role_emojis[role]} <b>{role}:</b>\n"
            for idx, (_, name, _, _) in enumerate(staff_in_role, 1):
                response += f"      {idx}. {name}\n"
            response += "\n"
    
    # Заказчики
    customers = [u for u in users if u[3] == "Заказчик"]
    if customers:
        response += "🤝 <b>ЗАКАЗЧИКИ:</b>\n"
        for idx, (_, name, _, _) in enumerate(customers, 1):
            response += f"   {idx}. {name}\n"

    await message.answer(response.strip(), parse_mode="HTML", 
                        reply_markup=keyboard.as_markup(resize_keyboard=True))
    await message.answer('🔧 Выберите действие:', 
                        reply_markup=keyboard.as_markup(resize_keyboard=True))

# ------------------------------------------------------------------------------

# Клавиатура управления компаниями
def companies_keyboard():
    keyboard = ReplyKeyboardBuilder()
    keyboard.add(types.KeyboardButton(text='Добавить проект'))
    keyboard.add(types.KeyboardButton(text='Удалить проект'))
    keyboard.add(types.KeyboardButton(text='На главную'))
    keyboard.adjust(1)
    return keyboard.as_markup(resize_keyboard=True)

def based_keyboard():
    keyboard = ReplyKeyboardBuilder()
    keyboard.add(types.KeyboardButton(text='Назад к управлению проектами'))  # Новая кнопка
    keyboard.add(types.KeyboardButton(text='На главную'))
    keyboard.adjust(1)
    return keyboard.as_markup(resize_keyboard=True)

def based_keyboard_2():
    keyboard = ReplyKeyboardBuilder()
    keyboard.add(types.KeyboardButton(text='Назад к управлению пользователями'))  # Новая кнопка
    keyboard.add(types.KeyboardButton(text='На главную'))
    keyboard.adjust(1)
    return keyboard.as_markup(resize_keyboard=True)

# Клавиатура с кнопками "Назад" и "На главную"
def based_keyboard_3():
    keyboard = ReplyKeyboardBuilder()
    keyboard.add(types.KeyboardButton(text='Назад'))
    keyboard.add(types.KeyboardButton(text='Назад к управлению пользователями'))  # Новая кнопка
    keyboard.add(types.KeyboardButton(text='На главную'))
    keyboard.adjust(1)
    return keyboard.as_markup(resize_keyboard=True)

# Обработчик "Управление компаниями"
@router.message(F.text == 'Управление проектами')
async def project_management(message: Message):
    cur = conn.cursor()
    cur.execute("SELECT role FROM users WHERE key = %s", (message.from_user.id,))
    user = cur.fetchone()
    
    if not user or user[0] not in ["Суперадмин", "Леонидка"]:
        await message.answer("❌ У вас нет доступа к этому разделу.")
        return
    
    keyboard = ReplyKeyboardBuilder()
    keyboard.add(types.KeyboardButton(text='Добавить проект'))
    keyboard.add(types.KeyboardButton(text='Удалить проект'))
    keyboard.add(types.KeyboardButton(text='На главную'))
    keyboard.adjust(1)
    
    cur.execute('SELECT id, name FROM projects ORDER BY name')
    projects = cur.fetchall()
    
    if not projects:
        await message.answer(
            "❌ В системе нет добавленных проектов.", 
            reply_markup=keyboard.as_markup(resize_keyboard=True)
        )
        return

    response = "📋 <b>Список проектов:</b>\n\n"
    for idx, (project_id, name) in enumerate(projects, 1):
        response += f"{idx}. 🏢 {name} (ID: {project_id})\n"

    await message.answer(
        response, 
        parse_mode="HTML", 
        reply_markup=keyboard.as_markup(resize_keyboard=True)
    )


# ------------------------------ ДОБАВЛЕНИЕ ПРОЕКТА -----------------------------------

def get_ads_accounts():
    url = "https://api.vk.com/method/ads.getAccounts"
    params = {
        "access_token": ACCESS_TOKEN,
        "v": API_VERSION
    }
    
    response = requests.get(url, params=params).json()
    
    if "response" in response:
        return [account["account_id"] for account in response["response"]]
    else:
        print("Ошибка:", response)
        return []
    

@router.message(F.text == 'Добавить проект')
async def add_project_start(message: Message, state: FSMContext):
    cur = conn.cursor()
    cur.execute("SELECT role FROM users WHERE key = %s", (message.from_user.id,))
    user = cur.fetchone()

    if not user or user[0] not in ["Суперадмин", "Леонидка"]:
        await message.answer("❌ У вас нет доступа к этому разделу.")
        return

    await state.set_state(Dialog.addProjectId)
    await message.answer(
        "Введите ID проекта (только цифры):", 
        reply_markup=based_keyboard()
    )

@router.message(Dialog.addProjectId)
async def add_project_id(message: Message, state: FSMContext):
    if not message.text.isdigit():
        await message.answer("❌ Ошибка! ID проекта должен содержать только цифры.", 
                           reply_markup=based_keyboard())
        return

    project_id = int(message.text)
    
    # Проверяем существование проекта в базе
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM projects WHERE id = %s", (str(project_id),))
    (count,) = cur.fetchone()

    if count > 0:
        await message.answer(f"⚠️ Проект с ID {project_id} уже существует!", 
                           reply_markup=based_keyboard())
        return

    # Проверяем наличие ID в рекламных кабинетах VK
    ads_accounts = get_ads_accounts()
    if project_id not in ads_accounts:
        await message.answer("❌ Ошибка! Данный ID отсутствует среди ваших рекламных кабинетов VK.", 
                           reply_markup=based_keyboard())
        return

    await state.update_data(project_id=project_id)
    await state.set_state(Dialog.addProjectName)
    await message.answer("Введите название проекта:", reply_markup=based_keyboard_3())

@router.message(Dialog.addProjectName)
async def add_project_name(message: Message, state: FSMContext):
    if message.text == 'Назад':
        await state.set_state(Dialog.addProjectId)
        await message.answer("Введите ID проекта (только цифры):", 
                           reply_markup=based_keyboard())
        return

    project_name = message.text.strip()
    if not project_name:
        await message.answer("❌ Ошибка! Название проекта не может быть пустым.", 
                           reply_markup=based_keyboard_3())
        return

    state_data = await state.get_data()
    project_id = state_data['project_id']

    cur = conn.cursor()
    cur.execute("INSERT INTO projects (id, name) VALUES (%s, %s)", 
                (str(project_id), project_name))
    conn.commit()

    await state.clear()
    await message.answer(
        f"✅ Проект <b>{project_name}</b> (ID: {project_id}) успешно добавлен!", 
        parse_mode="HTML", 
        reply_markup=based_keyboard()
    )


# ------------------------------ УДАЛЕНИЕ ПРОЕКТА -----------------------------------

@router.message(F.text == 'Удалить проект')
async def delete_project_start(message: Message, state: FSMContext):
    cur = conn.cursor()
    cur.execute("SELECT role FROM users WHERE key = %s", (message.from_user.id,))
    user = cur.fetchone()

    if not user or user[0] not in ["Суперадмин", "Леонидка"]:
        await message.answer("❌ У вас нет доступа к этому разделу.")
        return

    cur.execute('SELECT id, name FROM projects ORDER BY name')
    projects = cur.fetchall()
    
    if not projects:
        await message.answer(
            "❌ В системе нет проектов для удаления.", 
            reply_markup=based_keyboard()
        )
        return

    response = "🗑 <b>Выберите проект для удаления:</b>\n\n"
    projects_dict = {}
    for idx, (project_id, name) in enumerate(projects, 1):
        response += f"{idx}. 🏢 {name} (ID: {project_id})\n"
        projects_dict[idx] = project_id

    await state.update_data(projects_dict=projects_dict)
    await state.set_state(Dialog.deleteProject)
    await message.answer(
        response, 
        parse_mode="HTML", 
        reply_markup=based_keyboard()
    )
    await message.answer("✏️ Введите номер проекта для удаления:")

@router.message(Dialog.deleteProject)
async def confirm_project_deletion(message: Message, state: FSMContext):
    user_input = message.text.strip()
    
    if not user_input.isdigit():
        await message.answer("❌ Ошибка! Введите число, соответствующее проекту.", reply_markup=based_keyboard())
        return
    
    project_number = int(user_input)
    state_data = await state.get_data()
    projects_dict = state_data.get("projects_dict", {})
    
    if project_number not in projects_dict:
        await message.answer("❌ Ошибка! Проект с таким номером не найден.", reply_markup=based_keyboard())
        return
    
    project_id = projects_dict[project_number]
    
    confirm_markup = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="✅ Удалить", callback_data=f"confirm_delete:{project_id}")
    ], [
        InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_delete")
    ]])
    
    await state.update_data(project_id=project_id)
    await message.answer(f"⚠️ Вы уверены, что хотите удалить проект?", parse_mode="HTML", reply_markup=confirm_markup)

@router.callback_query(F.data.startswith("confirm_delete:"))
async def delete_project_callback(callback: CallbackQuery, state: FSMContext):
    project_id = callback.data.split(":")[1]
    
    cur = conn.cursor()
    cur.execute("DELETE FROM projects WHERE id = %s", (project_id,))
    conn.commit()
    
    await state.clear()
    await callback.message.edit_text("✅ Проект успешно удалён!")
    await callback.answer()

@router.callback_query(F.data == "cancel_delete")
async def cancel_project_deletion(callback: CallbackQuery, state: FSMContext):
    try:
        await callback.message.delete()
    except Exception as e:
        print(f"Ошибка при удалении сообщения: {e}")

    await state.clear()
    
    cur = conn.cursor()
    cur.execute('SELECT id, name FROM projects')
    projects = cur.fetchall()

    if not projects:
        await callback.message.answer("❌ В базе данных нет проектов для удаления.", reply_markup=based_keyboard())
        return

    response_text = "🗑 <b>Выберите проект для удаления:</b>\n\n"
    projects_dict = {}
    for idx, (project_id, project_name) in enumerate(projects, start=1):
        response_text += f"{idx}. 🏢 <b>{project_name}</b> (ID: {project_id})\n"
        projects_dict[idx] = project_id

    await state.update_data(projects_dict=projects_dict)
    await state.set_state(Dialog.deleteProject)

    await callback.message.answer(response_text.strip(), parse_mode="HTML", reply_markup=based_keyboard())
    await callback.message.answer("✏️ Введите порядковый номер проекта для удаления.")


#---------------------------------------------------------------------------------------------------------------------------
# Управление пользователями
@router.message(F.text == 'Управление пользователями')
async def user_management(message: Message, state: FSMContext):
    cur = conn.cursor()
    cur.execute("SELECT role FROM users WHERE key = %s", (message.from_user.id,))
    user = cur.fetchone()
    
    if not user or user[0] != "Суперадмин":
        await message.answer("❌ У вас нет доступа к этому разделу.")
        return
    
    keyboard = ReplyKeyboardBuilder()
    keyboard.add(types.KeyboardButton(text='Добавить пользователя'))
    keyboard.add(types.KeyboardButton(text='Удалить пользователя'))
    keyboard.add(types.KeyboardButton(text='Назначить проекты'))
    keyboard.add(types.KeyboardButton(text='Просмотр назначенных проектов'))  # Новая кнопка
    keyboard.add(types.KeyboardButton(text='На главную'))
    keyboard.adjust(1)

    cur.execute("SELECT key, name, role, chapter FROM users ORDER BY chapter, role")
    users = cur.fetchall()
    
    if not users:
        await message.answer("❌ В системе нет зарегистрированных пользователей.", 
                           reply_markup=keyboard.as_markup(resize_keyboard=True))
        return

    response = "👥 <b>Список пользователей:</b>\n\n"
    
    # Сотрудники
    response += "👨‍💼 <b>СОТРУДНИКИ:</b>\n"
    
    role_emojis = {
        "Суперадмин": "👑",
        "Леонидка": "⭐️",
        "Пользователь": "👤"
    }
    
    # Группируем сотрудников по ролям
    for role in ["Суперадмин", "Леонидка", "Пользователь"]:
        staff_in_role = [u for u in users if u[2] == role and u[3] == "Сотрудник"]
        if staff_in_role:
            response += f"   {role_emojis[role]} <b>{role}:</b>\n"
            for idx, (_, name, _, _) in enumerate(staff_in_role, 1):
                response += f"      {idx}. {name}\n"
            response += "\n"
    
    # Заказчики
    customers = [u for u in users if u[3] == "Заказчик"]
    if customers:
        response += "🤝 <b>ЗАКАЗЧИКИ:</b>\n\n"
        for idx, (_, name, _, _) in enumerate(customers, 1):
            response += f"   {idx}. {name}\n"

    await message.answer(response.strip(), parse_mode="HTML", 
                        reply_markup=keyboard.as_markup(resize_keyboard=True))
    await message.answer('🔧 Выберите действие:', 
                        reply_markup=keyboard.as_markup(resize_keyboard=True))

@router.message(F.text == 'Просмотр назначенных проектов')
async def view_assigned_projects(message: Message):
    cur = conn.cursor()
    cur.execute("SELECT role FROM users WHERE key = %s", (message.from_user.id,))
    user = cur.fetchone()
    
    if not user or user[0] != "Суперадмин":
        await message.answer("❌ У вас нет доступа к этому разделу.")
        return

    # Получаем всех заказчиков и их проекты
    cur.execute("""
        SELECT u.name, u.project, u.key 
        FROM users u 
        WHERE u.chapter = 'Заказчик' 
        ORDER BY u.name
    """)
    customers = cur.fetchall()

    if not customers:
        await message.answer(
            "❌ В системе нет зарегистрированных заказчиков.",
            reply_markup=main_keyboard("Суперадмин")
        )
        return

    response = "📋 <b>Назначенные проекты заказчиков:</b>\n\n"
    
    for customer_name, project_ids, customer_key in customers:
        response += f"👤 <b>{customer_name}</b>\n"
        
        if not project_ids:
            response += "   ❌ Нет назначенных проектов\n"
        else:
            # Получаем информацию о проектах
            project_id_list = project_ids.split(',')
            cur.execute(
                "SELECT id, name FROM projects WHERE id = ANY(%s) ORDER BY name",
                (project_id_list,)
            )
            projects = cur.fetchall()
            
            if not projects:
                response += "   ❌ Нет активных проектов\n"
            else:
                for idx, (project_id, project_name) in enumerate(projects, 1):
                    response += f"   {idx}. 🏢 {project_name} (ID: {project_id})\n"
        
        response += "\n"

    keyboard = ReplyKeyboardBuilder()
    keyboard.add(types.KeyboardButton(text='Назад к управлению пользователями'))
    keyboard.add(types.KeyboardButton(text='На главную'))
    keyboard.adjust(1)

    # Если сообщение слишком длинное, разбиваем его на части
    if len(response) > 4096:
        parts = [response[i:i+4096] for i in range(0, len(response), 4096)]
        for part in parts[:-1]:  # Отправляем все части кроме последней
            await message.answer(part, parse_mode="HTML")
        # Отправляем последнюю часть с клавиатурой
        await message.answer(
            parts[-1], 
            parse_mode="HTML",
            reply_markup=keyboard.as_markup(resize_keyboard=True)
        )
    else:
        await message.answer(
            response, 
            parse_mode="HTML",
            reply_markup=keyboard.as_markup(resize_keyboard=True)
        )

# Добавление пользователя
class AddUser(StatesGroup):
    chapter = State()  # Новое состояние для выбора типа пользователя
    key = State()
    name = State()
    role = State()

@router.message(F.text == 'Добавить пользователя')
async def add_user_start(message: Message, state: FSMContext):
    cur = conn.cursor()
    cur.execute("SELECT role FROM users WHERE key = %s", (message.from_user.id,))
    user = cur.fetchone()

    if not user or user[0] != "Суперадмин":
        await message.answer("❌ У вас нет доступа к этому разделу.", reply_markup=based_keyboard_2())
        return

    keyboard = ReplyKeyboardBuilder()
    keyboard.add(types.KeyboardButton(text='Заказчик'))
    keyboard.add(types.KeyboardButton(text='Сотрудник'))
    keyboard.add(types.KeyboardButton(text='Назад к управлению пользователями'))

    keyboard.adjust(1)

    await state.set_state(AddUser.chapter)
    await message.answer("👥 Выберите тип пользователя:", reply_markup=keyboard.as_markup(resize_keyboard=True))

@router.message(AddUser.chapter)
async def add_user_chapter(message: Message, state: FSMContext):
    if message.text not in ['Заказчик', 'Сотрудник']:
        await message.answer("❌ Пожалуйста, выберите тип пользователя из предложенных вариантов.")
        return

    await state.update_data(chapter=message.text)
    await state.set_state(AddUser.key)
    await message.answer("🔑 Введите ключ (ID) нового пользователя:", reply_markup=based_keyboard_3())

@router.message(AddUser.key)
async def add_user_key(message: Message, state: FSMContext):
    if message.text == 'Назад':
        await state.set_state(AddUser.chapter)  # Вернуться на шаг выбора типа пользователя
        keyboard = ReplyKeyboardBuilder()
        keyboard.add(types.KeyboardButton(text='Заказчик'))
        keyboard.add(types.KeyboardButton(text='Сотрудник'))
        keyboard.add(types.KeyboardButton(text='Назад к управлению пользователями'))
        keyboard.adjust(1)

        await message.answer("👥 Выберите тип пользователя:", reply_markup=keyboard.as_markup(resize_keyboard=True))
        return

    elif not message.text.isdigit():
        await message.answer("❌ Ошибка! ID должен быть числом.", reply_markup=based_keyboard_3())
        return
    else:
        await state.update_data(key=int(message.text))
        await state.set_state(AddUser.name)
        await message.answer("📝 Введите имя нового пользователя:", reply_markup=based_keyboard_3())

@router.message(AddUser.name)
async def add_user_name(message: Message, state: FSMContext):
    if message.text == 'Назад':
        await state.set_state(AddUser.key)  # Вернуться на шаг ввода ключа
        await message.answer("🔑 Введите ключ (ID) нового пользователя:", reply_markup=based_keyboard_3())
        return

    user_data = await state.get_data()
    await state.update_data(name=message.text.strip())

    # Если это заказчик, сразу добавляем в базу без выбора роли
    if user_data.get('chapter') == 'Заказчик':
        cur = conn.cursor()
        cur.execute("INSERT INTO users (key, name, role, chapter) VALUES (%s, %s, %s, %s)", 
                    (user_data['key'], message.text.strip(), 'Пользователь', 'Заказчик'))
        conn.commit()
        
        await state.clear()
        await message.answer(
            f"✅ Заказчик <b>{message.text.strip()}</b> успешно добавлен!", 
            parse_mode="HTML", 
            reply_markup=based_keyboard_2()
        )
        return

    # Если это сотрудник, предлагаем выбрать роль
    await state.set_state(AddUser.role)
    keyboard = ReplyKeyboardBuilder()
    keyboard.add(types.KeyboardButton(text='Суперадмин'))
    keyboard.add(types.KeyboardButton(text='Леонидка'))
    keyboard.add(types.KeyboardButton(text='Пользователь'))
    keyboard.add(types.KeyboardButton(text='Назад'))
    keyboard.add(types.KeyboardButton(text='На главную'))
    keyboard.adjust(1)
    
    await message.answer("🎭 Выберите роль пользователя:", reply_markup=keyboard.as_markup(resize_keyboard=True))

@router.message(AddUser.role)
async def add_user_role(message: Message, state: FSMContext):
    if message.text == 'Назад':
        await state.set_state(AddUser.name)
        await message.answer("📝 Введите имя нового пользователя:", reply_markup=based_keyboard_3())
        return

    if message.text not in ['Суперадмин', 'Леонидка', 'Пользователь']:
        await message.answer("❌ Ошибка! Выберите роль из списка.")
        return
    
    user_data = await state.get_data()
    cur = conn.cursor()
    cur.execute("INSERT INTO users (key, name, role, chapter) VALUES (%s, %s, %s, %s)", 
                (user_data['key'], user_data['name'], message.text, user_data['chapter']))
    conn.commit()
    
    await state.clear()
    await message.answer(
        f"✅ Сотрудник <b>{user_data['name']}</b> "
        f"с ролью <b>{message.text}</b> успешно добавлен!", 
        parse_mode="HTML", 
        reply_markup=based_keyboard_2()
    )

# Удаление пользователя
@router.message(F.text == 'Удалить пользователя')
async def delete_user_list(message: Message, state: FSMContext):
    cur = conn.cursor()
    cur.execute("SELECT role FROM users WHERE key = %s", (message.from_user.id,))

    user = cur.fetchone()

    if not user or user[0] != "Суперадмин":
        await message.answer("❌ У вас нет доступа к этому разделу.")
        return
    
    cur.execute("SELECT key, name, role, chapter FROM users ORDER BY chapter, role")
    users = cur.fetchall()
    
    if not users:
        await message.answer("❌ В системе нет пользователей.", 
                           reply_markup=based_keyboard_2())
        return
    
    response = "🗑 <b>Выберите пользователя для удаления:</b>\n\n"
    users_dict = {}
    counter = 1

    role_emojis = {
        "Суперадмин": "👑",
        "Леонидка": "⭐️",
        "Пользователь": "👤"
    }

    # Сотрудники
    response += "👨‍💼 <b>СОТРУДНИКИ:</b>\n\n"
    
    # Группируем сотрудников по ролям
    for role in ["Суперадмин", "Леонидка", "Пользователь"]:
        staff_in_role = [u for u in users if u[2] == role and u[3] == "Сотрудник"]
        if staff_in_role:
            response += f"   {role_emojis[role]} <b>{role}:</b>\n"
            for user_key, name, _, _ in staff_in_role:
                response += f"      {counter}. {name}\n"
                users_dict[counter] = user_key
                counter += 1
            response += "\n"
    
    # Заказчики
    customers = [u for u in users if u[3] == "Заказчик"]
    if customers:
        response += "🤝 <b>ЗАКАЗЧИКИ:</b>\n\n"
        for user_key, name, _, _ in customers:
            response += f"   {counter}. {name}\n"
            users_dict[counter] = user_key
            counter += 1
    
    await state.update_data(users_dict=users_dict)
    await state.set_state(Dialog.deleteUser)
    await message.answer(response.strip(), parse_mode="HTML")
    await message.answer("✏️ Введите порядковый номер пользователя для удаления:", 
                        reply_markup=based_keyboard_2())

@router.message(Dialog.deleteUser)
async def delete_user(message: Message, state: FSMContext):
    user_input = message.text.strip()
    if not user_input.isdigit():
        await message.answer("❌ Ошибка! Введите число.")
        return
    
    user_number = int(user_input)
    state_data = await state.get_data()
    users_dict = state_data.get("users_dict", {})
    
    if user_number not in users_dict:
        await message.answer("❌ Ошибка! Пользователь не найден.")
        return
    
    user_key = users_dict[user_number]
    cur = conn.cursor()
    
    # Подтверждение удаления
    confirm_markup = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="✅ Удалить", callback_data=f"confirm_delete_user:{user_key}")
    ], [
        InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_delete_user")
    ]])
    
    cur.execute("SELECT name FROM users WHERE key = %s", (user_key,))
    user_name = cur.fetchone()[0]
    
    await message.answer(f"⚠️ Вы уверены, что хотите удалить пользователя <b>{user_name}</b>?", parse_mode="HTML", reply_markup=confirm_markup)

@router.callback_query(F.data.startswith("confirm_delete_user:"))
async def confirm_delete_user(callback: CallbackQuery, state: FSMContext):
    user_key = callback.data.split(":")[1]
    
    cur = conn.cursor()
    cur.execute("DELETE FROM users WHERE key = %s", (user_key,))
    conn.commit()
    
    await state.clear()
    await callback.message.edit_text("✅ Пользователь успешно удалён!")
    await callback.answer()

@router.callback_query(F.data == "cancel_delete_user")
async def cancel_delete_user(callback: CallbackQuery, state: FSMContext):
    await callback.message.delete()
    
    cur = conn.cursor()
    cur.execute("SELECT key, name FROM users")
    users = cur.fetchall()
    
    if not users:
        await callback.message.answer("❌ В системе нет пользователей.", reply_markup=companies_keyboard())
        return
    
    response = "🗑 <b>Выберите пользователя для удаления:</b>\n\n"
    users_dict = {}
    for idx, (user_key, user_name) in enumerate(users, start=1):
        response += f"{idx}. 👤 <b>{user_name}</b> (ID: {user_key})\n"
        users_dict[idx] = user_key
    
    await state.update_data(users_dict=users_dict)
    await state.set_state(Dialog.deleteUser)  # Устанавливаем состояние для удаления пользователей
    await callback.message.answer(response.strip(), parse_mode="HTML")
    await callback.message.answer("✏️ Введите порядковыйномер пользователя для удаления:", reply_markup=based_keyboard_2())

    await callback.answer()

# Обработчик раздела статистики
@router.message(F.text == 'Статистика')
async def show_statistics_projects(message: Message, state: FSMContext):
    cur = conn.cursor()
    cur.execute('SELECT role, chapter, project FROM users WHERE key = %s', 
                (message.from_user.id,))
    user = cur.fetchone()

    if not user:
        await message.answer("❌ У вас нет доступа к боту.")
        return

    role, chapter, user_projects = user

    # Получаем список проектов в зависимости от роли пользователя
    if chapter == "Заказчик":
        if not user_projects:
            await message.answer("❌ К вашему аккаунту не привязано ни одного проекта.", 
                               reply_markup=main_keyboard())
            return
        
        # Разбиваем строку с проектами на список ID
        project_ids = [pid.strip() for pid in user_projects.split(',')]
        # Получаем информацию только о доступных проектах
        cur.execute(
            'SELECT id, name FROM projects WHERE id = ANY(%s) ORDER BY name',
            (project_ids,)
        )
    else:
        # Для сотрудников показываем все проекты
        cur.execute('SELECT id, name FROM projects ORDER BY name')

    projects = cur.fetchall()

    if not projects:
        await message.answer("❌ Нет доступных проектов.", 
                           reply_markup=main_keyboard())
        return

    response_text = "<b>📊 Выберите проект для просмотра статистики:</b>\n\n"
    projects_dict = {}
    
    for idx, (project_id, project_name) in enumerate(projects, start=1):
        response_text += f"{idx}. 🏢 {project_name} (ID: {project_id})\n"
        projects_dict[idx] = (project_id, project_name)

    await state.update_data(projects_dict=projects_dict)
    await state.set_state(Dialog.selectProject)
    
    keyboard = ReplyKeyboardBuilder()
    keyboard.add(types.KeyboardButton(text='На главную'))
    keyboard.adjust(1)
    
    await message.answer(response_text, parse_mode="HTML", 
                        reply_markup=keyboard.as_markup(resize_keyboard=True))
    await message.answer("✏️ Введите номер проекта:")

@router.message(Dialog.selectProject)
async def process_project_selection(message: Message, state: FSMContext):
    if not message.text.isdigit():
        await message.answer("❌ Пожалуйста, введите число.")
        return

    project_number = int(message.text)
    state_data = await state.get_data()
    projects_dict = state_data.get('projects_dict', {})

    if project_number not in projects_dict:
        await message.answer("❌ Проект с таким номером не найден.")
        return

    # Проверяем доступ к проекту для заказчика
    cur = conn.cursor()
    cur.execute('SELECT chapter, project FROM users WHERE key = %s', 
                (message.from_user.id,))
    user = cur.fetchone()
    
    if user[0] == "Заказчик":
        project_id = str(projects_dict[project_number][0])
        user_projects = [pid.strip() for pid in (user[1] or '').split(',')]
        
        if project_id not in user_projects:
            await message.answer("❌ У вас нет доступа к этому проекту.")
            return

    project_id, project_name = projects_dict[project_number]
    await state.update_data(selected_project_id=project_id, 
                           selected_project_name=project_name)
    await state.set_state(Dialog.startDate)
    
    keyboard = ReplyKeyboardBuilder()
    keyboard.add(types.KeyboardButton(text='Назад к выбору проекта'))
    keyboard.add(types.KeyboardButton(text='На главную'))
    keyboard.adjust(1)
    
    await message.answer(
        "📅 Введите начальную дату в формате ДД.ММ.ГГГГ (например, 01.01.2025):",
        reply_markup=keyboard.as_markup(resize_keyboard=True)
    )

@router.message(Dialog.startDate)
async def process_start_date(message: Message, state: FSMContext):
    if message.text == 'Назад к выбору проекта':
        await show_statistics_projects(message, state)
        return

    try:
        # Преобразуем дату из формата DD.MM.YYYY в YYYY-MM-DD для API
        start_date = datetime.strptime(message.text, '%d.%m.%Y')
        if start_date > datetime.now():
            await message.answer("❌ Дата не может быть в будущем.")
            return
        api_date = start_date.strftime('%Y-%m-%d')  # Формат для API
    except ValueError:
        await message.answer("❌ Неверный формат даты. Используйте формат ДД.ММ.ГГГГ (например, 01.01.2025)")
        return

    await state.update_data(start_date=api_date)
    await state.set_state(Dialog.endDate)
    
    keyboard = ReplyKeyboardBuilder()
    keyboard.add(types.KeyboardButton(text='Назад к начальной дате'))
    keyboard.add(types.KeyboardButton(text='На главную'))
    keyboard.adjust(1)
    
    await message.answer(
        "📅 Введите конечную дату в формате ДД.ММ.ГГГГ:",
        reply_markup=keyboard.as_markup(resize_keyboard=True)
    )

@router.message(Dialog.endDate)
async def process_end_date(message: Message, state: FSMContext):
    if message.text == 'Назад к начальной дате':
        state_data = await state.get_data()
        await state.set_state(Dialog.startDate)
        keyboard = ReplyKeyboardBuilder()
        keyboard.add(types.KeyboardButton(text='Назад к выбору проекта'))
        keyboard.add(types.KeyboardButton(text='На главную'))
        keyboard.adjust(1)
        await message.answer(
            "📅 Введите начальную дату в формате ДД.ММ.ГГГГ:",
            reply_markup=keyboard.as_markup(resize_keyboard=True)
        )
        return

    state_data = await state.get_data()
    try:
        start_date = datetime.strptime(state_data['start_date'], '%Y-%m-%d')
        # Преобразуем введенную конечную дату
        end_date = datetime.strptime(message.text, '%d.%m.%Y')
        api_end_date = end_date.strftime('%Y-%m-%d')  # Формат для API
        
        if end_date < start_date:
            await message.answer("❌ Конечная дата не может быть раньше начальной.")
            return
        if end_date > datetime.now():
            await message.answer("❌ Конечная дата не может быть в будущем.")
            return
    except ValueError:
        await message.answer("❌ Неверный формат даты. Используйте формат ДД.ММ.ГГГГ")
        return

    # Получаем статистику из VK API
    project_id = state_data['selected_project_id']
    project_name = state_data['selected_project_name']
    
    await message.answer("⏳ Получаем статистику...")
    
    # Получаем статистику кампаний
    campaigns_stats = get_campaigns_stats(
        account_id=project_id,
        start_date=state_data['start_date'],
        end_date=api_end_date
    )
    
    if not campaigns_stats:
        keyboard = ReplyKeyboardBuilder()
        keyboard.add(types.KeyboardButton(text='Назад к статистике'))
        keyboard.add(types.KeyboardButton(text='На главную'))
        keyboard.adjust(1)
        
        await message.answer(
            "❌ Не удалось получить статистику или нет кампаний с расходами за указанный период.",
            reply_markup=keyboard.as_markup(resize_keyboard=True)
        )
        return

    # Форматируем даты для вывода
    display_start_date = datetime.strptime(state_data['start_date'], '%Y-%m-%d').strftime('%d.%m.%Y')
    display_end_date = end_date.strftime('%d.%m.%Y')

    # Формируем ответ
    response = f"📊 Статистика по проекту <b>{project_name}</b>\n"
    response += f"За период: {display_start_date} - {display_end_date}\n\n"
    
    total_spent = 0
    for idx, (name, spent) in enumerate(campaigns_stats, 1):
        response += f"{idx}. {name} - {spent:.2f}₽\n"
        total_spent += spent

    if len(campaigns_stats) > 2:
        response += f"\nИтого: {total_spent:.2f}₽"

    keyboard = ReplyKeyboardBuilder()
    keyboard.add(types.KeyboardButton(text='Назад к статистике'))
    keyboard.add(types.KeyboardButton(text='На главную'))
    keyboard.adjust(1)

    await state.clear()
    await message.answer(
        response, 
        parse_mode="HTML", 
        reply_markup=keyboard.as_markup(resize_keyboard=True)
    )

# Добавляем обработчик для кнопки "Назад к статистике"
@router.message(F.text == 'Назад к статистике')
async def back_to_statistics(message: Message, state: FSMContext):
    await show_statistics_projects(message, state)

def get_campaigns_stats(account_id: int, start_date: str, end_date: str) -> List[Tuple[str, float]]:
    """Получение статистики кампаний из VK API"""
    url = "https://api.vk.com/method/ads.getStatistics"
    
    # Получаем список кампаний
    campaigns_response = requests.get(
        "https://api.vk.com/method/ads.getCampaigns",
        params={
            "account_id": account_id, 
            "access_token": ACCESS_TOKEN, 
            "v": API_VERSION,
            "include_deleted": 0
        }
    ).json()
    
    if "response" not in campaigns_response:
        print(f"Ошибка получения кампаний: {campaigns_response}")
        return []
    
    campaign_ids = [camp["id"] for camp in campaigns_response["response"]]
    if not campaign_ids:
        print("Нет активных кампаний")
        return []
    
    # Параметры для получения статистики
    params = {
        "account_id": account_id,
        "ids_type": "campaign",
        "period": "day",
        "date_from": start_date,
        "date_to": end_date,
        "access_token": ACCESS_TOKEN,
        "v": API_VERSION,
        "ids": ",".join(map(str, campaign_ids))
    }
    
    # Получаем статистику
    stats_response = requests.get(url, params=params).json()
    print(f"Ответ API статистики: {stats_response}")
    
    if "response" not in stats_response:
        print(f"Ошибка получения статистики: {stats_response}")
        return []
    
    # Фильтруем кампании с расходами > 0
    campaigns_with_spent = []
    campaigns_dict = {camp["id"]: camp["name"] for camp in campaigns_response["response"]}
    
    for stat in stats_response["response"]:
        total_spent = 0
        if stat.get("stats"):
            for day in stat["stats"]:
                spent = float(day.get("spent", 0))
                total_spent += spent
        
        if total_spent > 0:
            campaign_name = campaigns_dict.get(stat["id"], f"Кампания {stat['id']}")
            campaigns_with_spent.append((campaign_name, total_spent))
    
    print(f"Найдено кампаний с расходами: {len(campaigns_with_spent)}")
    return sorted(campaigns_with_spent, key=lambda x: x[1], reverse=True)  # Сортируем по убыванию расходов

@router.message(F.text == 'Назначить проекты')
async def assign_projects_start(message: Message, state: FSMContext):
    cur = conn.cursor()
    cur.execute("SELECT role FROM users WHERE key = %s", (message.from_user.id,))
    user = cur.fetchone()
    
    if not user or user[0] != "Суперадмин":
        await message.answer("❌ У вас нет доступа к этому разделу.")
        return
    
    # Получаем список заказчиков
    cur.execute("SELECT key, name FROM users WHERE chapter = 'Заказчик' ORDER BY name")
    customers = cur.fetchall()
    
    if not customers:
        await message.answer("❌ В системе нет зарегистрированных заказчиков.", 
                           reply_markup=main_keyboard(user[0]))
        return

    response = "👥 <b>Выберите заказчика для назначения проектов:</b>\n\n"
    customers_dict = {}
    
    for idx, (customer_key, name) in enumerate(customers, 1):
        response += f"{idx}. 👤 {name}\n"
        customers_dict[idx] = (customer_key, name)

    await state.update_data(customers_dict=customers_dict)
    await state.set_state(Dialog.selectCustomer)
    
    keyboard = ReplyKeyboardBuilder()
    keyboard.add(types.KeyboardButton(text='Назад к управлению пользователями'))
    keyboard.add(types.KeyboardButton(text='На главную'))
    keyboard.adjust(1)
    
    await message.answer(response, parse_mode="HTML", 
                        reply_markup=keyboard.as_markup(resize_keyboard=True))
    await message.answer("✏️ Введите номер заказчика:")

@router.message(Dialog.selectCustomer)
async def process_customer_selection(message: Message, state: FSMContext):
    if message.text == 'Назад к управлению пользователями':
        await user_management(message, state)
        return

    if not message.text.isdigit():
        await message.answer("❌ Пожалуйста, введите число.")
        return

    customer_number = int(message.text)
    state_data = await state.get_data()
    customers_dict = state_data.get('customers_dict', {})

    if customer_number not in customers_dict:
        await message.answer("❌ Заказчик с таким номером не найден.")
        return

    customer_key, customer_name = customers_dict[customer_number]
    await state.update_data(selected_customer_key=customer_key, 
                           selected_customer_name=customer_name)

    # Получаем список проектов
    cur = conn.cursor()
    cur.execute('SELECT id, name FROM projects ORDER BY name')
    projects = cur.fetchall()
    
    if not projects:
        await message.answer("❌ В системе нет проектов для назначения.")
        return

    # Получаем текущие проекты заказчика
    cur.execute('SELECT project FROM users WHERE key = %s', (customer_key,))
    current_projects = cur.fetchone()[0]
    current_projects = current_projects.split(',') if current_projects else []
    
    response = f"🏢 <b>Выберите проекты для заказчика {customer_name}:</b>\n"
    response += "Введите номера проектов через запятую (например: 1,3,5)\n\n"
    
    projects_dict = {}
    for idx, (project_id, name) in enumerate(projects, 1):
        marker = "✅" if str(project_id) in current_projects else "⚪️"
        response += f"{idx}. {marker} {name} (ID: {project_id})\n"
        projects_dict[idx] = (project_id, name)

    await state.update_data(projects_dict=projects_dict)
    await state.set_state(Dialog.assignProjects)
    
    keyboard = ReplyKeyboardBuilder()
    keyboard.add(types.KeyboardButton(text='Назад к выбору заказчика'))
    keyboard.add(types.KeyboardButton(text='На главную'))
    keyboard.adjust(1)
    
    await message.answer(response, parse_mode="HTML", 
                        reply_markup=keyboard.as_markup(resize_keyboard=True))

@router.message(Dialog.assignProjects)
async def process_projects_assignment(message: Message, state: FSMContext):
    if message.text == 'Назад к выбору заказчика':
        await assign_projects_start(message, state)
        return

    state_data = await state.get_data()
    projects_dict = state_data.get('projects_dict', {})
    customer_key = state_data.get('selected_customer_key')
    customer_name = state_data.get('selected_customer_name')

    try:
        # Разбираем введенные номера проектов
        selected_numbers = [int(num.strip()) for num in message.text.split(',')]
        
        # Проверяем корректность номеров
        if not all(num in projects_dict for num in selected_numbers):
            await message.answer("❌ Один или несколько номеров проектов некорректны.")
            return
        
        # Формируем список ID проектов
        project_ids = [str(projects_dict[num][0]) for num in selected_numbers]
        
        # Обновляем привязку проектов в базе данных
        cur = conn.cursor()
        cur.execute(
            "UPDATE users SET project = %s WHERE key = %s",
            (','.join(project_ids), customer_key)
        )
        conn.commit()

        # Формируем сообщение об успешном назначении
        project_names = [projects_dict[num][1] for num in selected_numbers]
        response = f"✅ Для заказчика <b>{customer_name}</b> назначены проекты:\n"
        for idx, name in enumerate(project_names, 1):
            response += f"{idx}. {name}\n"

        await state.clear()
        await message.answer(response, parse_mode="HTML", 
                           reply_markup=main_keyboard("Суперадмин"))

    except ValueError:
        await message.answer("❌ Неверный формат ввода. Введите номера через запятую.")
        return

# Запуск бота
async def main():
    dp = Dispatcher(storage=MemoryStorage())
    dp.include_router(router)
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())

if __name__ == "__main__":
    asyncio.run(main())