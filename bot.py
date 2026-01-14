import asyncio
import requests
from aiogram import Bot, Dispatcher
from aiogram.filters import CommandStart, Command
from aiogram.types import Message

BOT_TOKEN = '8521003004:AAHnKttLruoGOpNWIcdZo3REfD4DUXUs-MY'
API_URL = "http://127.0.0.1:5000/"

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()


@dp.message(CommandStart())
async def send_welcome(message: Message):
    await message.reply("Привет! Я добавлю тебя в базу.")
    user_id = message.from_user.id
    first_name = message.from_user.first_name
    last_name = message.from_user.last_name
    username = message.from_user.username

    print(f"User ID: {user_id}, First name: {first_name}, Username: @{username}")

    # ===  Отправляем POST запрос на твой API ===
    user_data = {
        "user_id": user_id,
        "first_name": first_name,
        "last_name": last_name,
        "phone_number": "unknown"  # у телеграм бота нет доступа к номеру телефона
    }

    try:
        # Пытаемся создать пользователя
        response = requests.post(API_URL + 'users', json=user_data)

        # Если пользователь успешно создан → он в базе впервые
        if response.status_code == 201:
            await message.answer("Рад видеть тебя впервые!")

        # Иначе если сервер вернул ошибку уникальности → значит, он уже есть
        elif "UNIQUE constraint failed" in response.text:
            await message.answer("Рад видеть снова!")

        else:
            await message.answer("Произошла ошибка на сервере, попробуйте позже.")

    except Exception as e:
        print("Ошибка соединения с API:", e)

    # отвечает пользователю
    await message.answer(
        f"Ты написал: {message.text}\n"
        f"ID: {user_id}\n"
        f"Имя: {first_name}"
    )


@dp.message(Command("newtask"))
async def create_new_task(message: Message):
    user_id = message.from_user.id

    # Например, пользователь пишет: /newtask Помыть посуду
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        return await message.answer("Используй: /newtask <название задачи>")

    title = parts[1]

    task_data = {
        "title": title,
        "description": "",
        "status": "new",
        "done": False,
        "user_id": user_id
    }

    try:
        response = requests.post(API_URL + 'create_task', json=task_data)

        if response.status_code == 201:
            task = response.json()["user"]
            await message.answer(
                f"Задача создана!\n"
                f"ID: {task['id']}\n"
                f"Название: {task['title']}"
            )
        else:
            await message.answer("Ошибка при создании задачи: " + response.text)

    except Exception as e:
        await message.answer("Ошибка соединения с API: " + str(e))


@dp.message(Command("tasks"))
async def get_user_tasks(message: Message):
    user_id = message.from_user.id

    try:
        response = requests.get(f"{API_URL + 'tasks'}/{user_id}")

        if response.status_code != 200:
            return await message.answer("Ошибка получения задач: " + response.text)

        tasks = response.json()

        if not tasks:
            return await message.answer("У тебя пока нет задач.")

        text = "📋 Твои задачи:\n\n"
        for t in tasks:
            status = "✔️" if t["done"] else "❌"
            text += f"{status} *{t['title']}*\nID: {t['id']}\n\n"

        await message.answer(text, parse_mode="Markdown")

    except Exception as e:
        await message.answer("Ошибка соединения с API: " + str(e))


@dp.message(Command("task"))
async def get_task_by_id(message: Message):
    user_id = message.from_user.id
    parts = message.text.split()

    # Проверяем, что ID указан
    if len(parts) < 2:
        return await message.answer("Используй: /task <id задачи>")

    try:
        task_id = int(parts[1])
    except ValueError:
        return await message.answer("ID задачи должен быть числом.")

    # Запрос к API
    try:
        response = requests.get(f"{API_URL + 'get_task'}/{task_id}")
        data = response.json()

        if response.status_code != 200:
            return await message.answer("Ошибка: " + data.get("error", "неизвестная ошибка"))

        task = data["task"]

        # Проверяем принадлежность пользователю
        if task["user_id"] != user_id:
            return await message.answer("Эта задача не принадлежит тебе.")

        # Формируем ответ
        text = (
            f"📝 *Задача {task['id']}*\n"
            f"*Название:* {task['title']}\n"
            f"*Описание:* {task['description']}\n"
            f"*Статус:* {task['status']}\n"
            f"*Выполнена:* {'✔️' if task['done'] else '❌'}\n"
        )

        await message.answer(text, parse_mode="Markdown")

    except Exception as e:
        await message.answer("Ошибка соединения с API: " + str(e))


@dp.message(Command("delete"))
async def delete_task(message: Message):
    user_id = message.from_user.id
    parts = message.text.split()

    # Проверяем, что пользователь указал ID
    if len(parts) < 2:
        return await message.answer("Используй: /delete <id задачи>")

    # Проверяем, что ID — число
    try:
        task_id = int(parts[1])
    except ValueError:
        return await message.answer("ID задачи должен быть числом.")

    # Формируем JSON
    payload = {
        "user_id": user_id
    }

    try:
        response = requests.delete(f"{API_URL + 'delete_task'}/{task_id}", json=payload)
        data = response.json()

        # Если ошибка — выводим её
        if response.status_code != 200:
            return await message.answer("Ошибка: " + data.get("error", "Неизвестная ошибка."))

        # Успешное удаление
        await message.answer(f"🗑 Задача {task_id} успешно удалена!")

    except Exception as e:
        await message.answer("Ошибка соединения с API: " + str(e))



@dp.message(Command("gettaskname"))
async def get_task_by_title(message: Message):
    user_id = message.from_user.id
    parts = message.text.split(maxsplit=1)

    # Проверяем, что пользователь ввёл название
    if len(parts) < 2:
        return await message.answer("Использование: /gettaskname <название задачи>")

    title = parts[1]

    try:
        # Отправляем GET запрос в твой API
        response = requests.get(f"{API_URL + 'get_task'}/{title}")
        data = response.json()

        # Если API вернул ошибку
        if response.status_code != 200:
            return await message.answer("Ошибка: " + data.get("error", "Неизвестная ошибка"))

        task = data["task"]

        # Проверяем принадлежность задачи пользователю
        if task["user_id"] != user_id:
            return await message.answer("Эта задача не принадлежит тебе!")

        # Красивый ответ с информацией о задаче
        text = (
            f"📝 *Задача {task['id']}*\n"
            f"*Название:* {task['title']}\n"
            f"*Описание:* {task['description']}\n"
            f"*Статус:* {task['status']}\n"
            f"*Выполнено:* {'✔️ Да' if task['done'] else '❌ Нет'}\n"
        )

        await message.answer(text, parse_mode="Markdown")

    except Exception as e:
        await message.answer("Ошибка соединения с API: " + str(e))



@dp.message(Command("updatetask"))
async def update_task(message: Message):
    user_id = message.from_user.id
    parts = message.text.split(maxsplit=2)

    if len(parts) < 3:
        return await message.answer(
            "Использование:\n"
            "/updatetask <id> <field1>=<value1> [<field2>=<value2> ...]\n"
            "Пример:\n"
            "/updatetask 12 title=Купить хлеб done=true"
        )

    try:
        task_id = int(parts[1])
    except ValueError:
        return await message.answer("ID задачи должен быть числом.")

    # Парсим поля обновления из строки parts[2]
    updates = {}
    fields_str = parts[2]
    for pair in fields_str.split():
        if '=' not in pair:
            return await message.answer("Ошибка в формате. Используйте field=value.")
        key, value = pair.split('=', 1)
        # Преобразуем done в bool
        if key == "done":
            if value.lower() in ['true', '1', 'да', 'yes']:
                value = True
            elif value.lower() in ['false', '0', 'нет', 'no']:
                value = False
            else:
                return await message.answer("Поле done должно быть true или false.")
        updates[key] = value

    # Добавляем user_id в данные
    updates["user_id"] = user_id

    try:
        response = requests.put(f"{API_URL + 'update_task'}/{task_id}", json=updates)
        data = response.json()

        if response.status_code != 200:
            return await message.answer("Ошибка: " + data.get("error", "Неизвестная ошибка"))

        task = data["task"]
        await message.answer(f"✅ Задача обновлена!\nНазвание: {task['title']}\nСтатус: {task['status']}\nВыполнена: {'✔️' if task['done'] else '❌'}")

    except Exception as e:
        await message.answer("Ошибка соединения с API: " + str(e))

@dp.message()
async def echo(message: Message):
    user_id = message.from_user.id
    first_name = message.from_user.first_name
    username = message.from_user.username # Печатаем информацию о пользователе в консоль
    print(f"User ID: {user_id}, First name: {first_name}, Username: @{username}")
    await message.answer(f"Ты написал: {message.text}, User ID: {user_id}, First name: {first_name}, Username: @{username}")

async def main():
    await dp.start_polling(bot)


if __name__ == '__main__':
    asyncio.run(main())
