import json
import logging
import asyncio  # Добавьте этот импорт
from datetime import datetime, date
from typing import Dict, List
from random import shuffle

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ConversationHandler,
    filters,
    ContextTypes
)
from apscheduler.schedulers.asyncio import AsyncIOScheduler


# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Константы для состояний разговора
NAME, COURSE, GROUP, WISHES = range(4)
EDIT_NAME, EDIT_COURSE, EDIT_GROUP, EDIT_WISHES = range(10, 14)


# Имя файла для хранения данных
DATA_FILE = "users_data.json"
ASSIGNMENTS_FILE = "assignments.json"

# Дата жеребьёвки (год, месяц, день)
DRAW_DATE = date(2025, 12, 25)  # Измените на нужную дату


class SecretSantaBot:
    def __init__(self, token: str):
        self.token = token
        self.application = Application.builder().token(token).build()
        self.scheduler = AsyncIOScheduler()

        # Загрузка данных
        self.users_data = self.load_data(DATA_FILE)
        self.assignments = self.load_data(ASSIGNMENTS_FILE)

        # Настройка обработчиков
        self.setup_handlers()

    def load_data(self, filename: str) -> Dict:
        """Загружает данные из JSON файла."""
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            return {}
        except json.JSONDecodeError:
            return {}

    def save_data(self, filename: str, data: Dict):
        """Сохраняет данные в JSON файл."""
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Начало диалога, запрос имени."""
        user_id = str(update.effective_user.id)

        # Проверяем, не зарегистрирован ли уже пользователь
        if user_id in self.users_data:
            keyboard = [
                [InlineKeyboardButton("Изменить данные", callback_data='change_data')],
                [InlineKeyboardButton("Просмотреть мои данные", callback_data='view_data')]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.message.reply_text(
                "Вы уже зарегистрированы! Что хотите сделать?",
                reply_markup=reply_markup
            )
            return ConversationHandler.END

        await update.message.reply_text(
            "Добро пожаловать в Тайного санту! 🎅\n"
            "Для регистрации введите ваше имя:"
        )
        return NAME

    async def get_name(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Получаем имя пользователя."""
        context.user_data['name'] = update.message.text
        await update.message.reply_text("Отлично! Теперь введите ваш курс (например, '1' или '2'):")
        return COURSE

    async def get_course(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Получаем курс."""
        context.user_data['course'] = update.message.text
        await update.message.reply_text("Хорошо! Теперь введите вашу группу (например, 'C10124-31.05.01(6)'):")
        return GROUP

    async def get_group(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Получаем группу."""
        context.user_data['group'] = update.message.text
        await update.message.reply_text(
            "Почти готово! Напишите ваши пожелания для подарка "
            "(что вам нравится, хобби, размер одежды и т.д.):"
        )
        return WISHES

    async def get_wishes(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Получаем пожелания и сохраняем все данные."""
        user_id = str(update.effective_user.id)
        wishes = update.message.text

        # Сохраняем данные пользователя
        self.users_data[user_id] = {
            'name': context.user_data['name'],
            'course': context.user_data['course'],
            'group': context.user_data['group'],
            'wishes': wishes,
            'registration_date': datetime.now().isoformat(),
            'username': update.effective_user.username
        }

        # Сохраняем в файл
        self.save_data(DATA_FILE, self.users_data)

        keyboard = [
            [InlineKeyboardButton("Изменить данные", callback_data='change_data')],
            [InlineKeyboardButton("Просмотреть мои данные", callback_data='view_data')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            "✅ Регистрация завершена!\n\n"
            f"Ваши данные:\n"
            f"Имя: {context.user_data['name']}\n"
            f"Курс: {context.user_data['course']}\n"
            f"Группа: {context.user_data['group']}\n"
            f"Пожелания: {wishes}\n\n"
            f"Жеребьёвка состоится {DRAW_DATE.strftime('%d.%m.%Y')}",
            reply_markup=reply_markup
        )


        return ConversationHandler.END

    async def cancel(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Отмена регистрации."""
        await update.message.reply_text("Регистрация отменена.")
        context.user_data.clear()
        return ConversationHandler.END

    async def view_data(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Просмотр своих данных."""
        query = update.callback_query
        await query.answer()

        user_id = str(query.from_user.id)
        if user_id in self.users_data:
            data = self.users_data[user_id]
            keyboard = [
                [InlineKeyboardButton("Изменить данные", callback_data='change_data')]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            message = (
                f"📋 Ваши данные:\n\n"
                f"Имя: {data['name']}\n"
                f"Курс: {data['course']}\n"
                f"Группа: {data['group']}\n"
                f"Пожелания: {data['wishes']}\n"
                f"Дата регистрации: {datetime.fromisoformat(data['registration_date']).strftime('%d.%m.%Y %H:%M')}"
            )
            await query.edit_message_text(message, reply_markup=reply_markup)

        else:
            message = "Вы еще не зарегистрированы! Используйте /start для регистрации."
            await query.edit_message_text(message)

    async def stats(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показывает статистику по зарегистрированным участникам."""
        count = len(self.users_data)

        if count == 0:
            await update.message.reply_text("Пока нет зарегистрированных участников.")
            return

        # Группировка по курсам
        courses = {}
        for data in self.users_data.values():
            course = data['course']
            courses[course] = courses.get(course, 0) + 1

        stats_text = f"📊 Статистика:\n\nВсего участников: {count}\n\nПо курсам:\n"
        for course, num in sorted(courses.items()):
            stats_text += f"Курс {course}: {num} чел.\n"

        await update.message.reply_text(stats_text)

    def perform_draw(self):
        """Проводит жеребьёвку (без повторов)."""
        user_ids = list(self.users_data.keys())

        if len(user_ids) < 2:
            logger.warning("Недостаточно участников для жеребьёвки")
            return

        # Перемешиваем список
        shuffle(user_ids)

        # Создаём пары (каждый дарит следующему, последний дарит первому)
        assignments = {}
        for i in range(len(user_ids)):
            giver = user_ids[i]
            receiver = user_ids[(i + 1) % len(user_ids)]
            assignments[giver] = receiver

        self.assignments = assignments
        self.save_data(ASSIGNMENTS_FILE, assignments)
        logger.info(f"Проведена жеребьёвка для {len(user_ids)} участника(ов)")

        return assignments

    async def send_assignments(self):
        """Рассылает результаты жеребьёвки участникам."""
        if not self.assignments:
            logger.warning("Жеребьёвка еще не проводилась")
            return

        for giver_id, receiver_id in self.assignments.items():
            try:
                giver_data = self.users_data.get(giver_id)
                receiver_data = self.users_data.get(receiver_id)

                if not giver_data or not receiver_data:
                    continue

                message = (
                    "🎄 Результаты жеребьёвки Тайного Санты! 🎄\n\n"
                    f"Вы дарите подарок:\n"
                    f"👤 {receiver_data['name']}\n"
                    f"📚 Курс: {receiver_data['course']}\n"
                    f"👥 Группа: {receiver_data['group']}\n"
                    f"🎁 Пожелания: {receiver_data['wishes']}\n\n"
                    "💰 Рекомендуемая стоимость подарка: 500-1000 руб.\n"
                    "📅 Доставка подарков до 25 декабря!\n\n"
                    "Счастливых праздников! 🎅"
                )

                await self.application.bot.send_message(
                    chat_id=int(giver_id),
                    text=message
                )
                logger.info(f"Сообщение отправлено пользователю {giver_id}")

            except Exception as e:
                logger.error(f"Ошибка отправки пользователю {giver_id}: {e}")

    async def manual_draw(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Ручной запуск жеребьёвки (только для админа)."""
        user_id = str(update.effective_user.id)

        # Проверка прав администратора (добавьте свои user_id)
        ADMINS = ['851720410']  # Замените на ваш ID

        if user_id not in ADMINS:
            await update.message.reply_text("Эта команда только для администраторов.")
            return

        assignments = self.perform_draw()
        count = len(assignments)

        await update.message.reply_text(
            f"✅ Жеребьёвка проведена!\n"
            f"Участников: {count}\n\n"
            f"Для рассылки результатов используйте /send_results"
        )

    async def clear_all(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        ADMINS = ['851720410']  # твой ID
        user_id = str(update.effective_user.id)
        if user_id not in ADMINS:
            await update.message.reply_text("Только для администраторов!")
            return

        self.users_data = {}
        self.assignments = {}
        self.save_data(DATA_FILE, self.users_data)
        self.save_data(ASSIGNMENTS_FILE, self.assignments)

        await update.message.reply_text("✅ Список участников и жеребьёвка очищены!")

    async def delete_my_profile(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Позволяет пользователю удалить свою анкету."""

        user_id = str(update.effective_user.id)

        if user_id not in self.users_data:
            await update.message.reply_text("Вы ещё не зарегистрированы, нечего удалять.")
            return

        # Удаляем данные пользователя
        del self.users_data[user_id]
        self.save_data(DATA_FILE, self.users_data)

        # Удаляем пользователя из жеребьёвки (если уже проводилась)
        if user_id in self.assignments:
            del self.assignments[user_id]

        # Удаляем его как получателя, если кто-то ему дарит подарок
        self.assignments = {giver: receiver for giver, receiver in self.assignments.items() if receiver != user_id}
        self.save_data(ASSIGNMENTS_FILE, self.assignments)

        await update.message.reply_text("✅ Ваша анкета успешно удалена.")


    async def send_results(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Ручная рассылка результатов (только для админа)."""
        user_id = str(update.effective_user.id)
        ADMINS = ['851720410']  # Замените на ваш ID

        if user_id not in ADMINS:
            await update.message.reply_text("Эта команда только для администраторов.")
            return

        await update.message.reply_text("Начинаю рассылку результатов...")
        await self.send_assignments()
        await update.message.reply_text("Рассылка завершена!")

    async def check_draw_date(self):
        """Проверяет, наступила ли дата жеребьёвки."""
        if date.today() >= DRAW_DATE:
            logger.info("Дата жеребьёвки наступила!")
            self.perform_draw()
            await self.send_assignments()

    def setup_scheduler(self):
        """Настройка планировщика для проверки даты жеребьёвки."""
        # Проверяем каждый день в 10:00
        self.scheduler.add_job(
            self.check_draw_date,
            'cron',
            hour=10,
            minute=0,
            timezone='Europe/Moscow'
        )
        self.scheduler.start()  # стартуем сразу
        logger.info("Планировщик настроен на ежедневную проверку в 10:00")

    def setup_handlers(self):
        """Настройка всех обработчиков команд."""
        # Обработчик регистрации

        conv_handler = ConversationHandler(
            entry_points=[CommandHandler('start', self.start),
                          CallbackQueryHandler(self.edit_field, pattern="^edit_")],
            states={
                NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.get_name)],
                COURSE: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.get_course)],
                GROUP: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.get_group)],
                WISHES: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.get_wishes)],
                EDIT_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.save_edit)],
                EDIT_COURSE: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.save_edit)],
                EDIT_GROUP: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.save_edit)],
                EDIT_WISHES: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.save_edit)],
            },
            fallbacks=[CommandHandler("cancel", self.cancel)]
        )
        self.application.add_handler(conv_handler)
        self.application.add_handler(CallbackQueryHandler(self.view_data, pattern='^view_data$'))
        self.application.add_handler(CallbackQueryHandler(self.edit_menu, pattern='^change_data$'))
        self.application.add_handler(CommandHandler('stats', self.stats))
        self.application.add_handler(CommandHandler('draw', self.manual_draw))
        self.application.add_handler(CommandHandler('send_results', self.send_results))
        self.application.add_handler(CommandHandler('clear_all', self.clear_all))
        self.application.add_handler(CommandHandler('delete_profile', self.delete_my_profile))

        # Обработчик для кнопки отмены в разговоре

    async def edit_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Меню редактирования данных."""
        query = update.callback_query
        await query.answer()

        keyboard = [
            [InlineKeyboardButton("Имя", callback_data="edit_name")],
            [InlineKeyboardButton("Курс", callback_data="edit_course")],
            [InlineKeyboardButton("Группа", callback_data="edit_group")],
            [InlineKeyboardButton("Пожелания", callback_data="edit_wishes")],
        ]

        await query.edit_message_text(
            "✏ Что вы хотите изменить?",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    async def edit_field(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()

        user_id = str(query.from_user.id)

        if user_id not in self.users_data:
            await query.edit_message_text("Вы не зарегистрированы.")
            return

        field_map = {
            "edit_name": ("Введите новое имя:", EDIT_NAME),
            "edit_course": ("Введите новый курс:", EDIT_COURSE),
            "edit_group": ("Введите новую группу:", EDIT_GROUP),
            "edit_wishes": ("Введите новые пожелания:", EDIT_WISHES)
        }

        action = query.data
        prompt, next_state = field_map[action]

        context.user_data["edit_field"] = action

        await query.edit_message_text(prompt)
        return next_state

    async def save_edit(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = str(update.effective_user.id)
        field = context.user_data.get("edit_field")
        value = update.message.text

        mapping = {
            "edit_name": "name",
            "edit_course": "course",
            "edit_group": "group",
            "edit_wishes": "wishes"
        }

        real_field = mapping[field]
        self.users_data[user_id][real_field] = value

        self.save_data(DATA_FILE, self.users_data)

        keyboard = [
            [InlineKeyboardButton("Изменить данные", callback_data='change_data')],
            [InlineKeyboardButton("Просмотреть мои данные", callback_data='view_data')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            "✅ Изменения сохранены!", reply_markup=reply_markup
        )

        return ConversationHandler.END


def main():
    TOKEN = "8339086357:AAGhmIqtHKBhZ2qt7wtKmV0Q0sB890dCjG8"

    bot = SecretSantaBot(TOKEN)

    # Запуск бота (не через asyncio.run)
    bot.application.run_polling()

if __name__ == '__main__':
    main()