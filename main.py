import os
import tkinter as tk
from tkinter import messagebox, ttk
import asyncio
from telethon import TelegramClient
from telethon.errors import SessionPasswordNeededError

# Контекстное меню для вставки, копирования, вырезания
def add_context_menu(entry):
    menu = tk.Menu(entry, tearoff=0)
    menu.add_command(label="Вырезать", command=lambda: entry.event_generate("<<Cut>>"))
    menu.add_command(label="Копировать", command=lambda: entry.event_generate("<<Copy>>"))
    menu.add_command(label="Вставить", command=lambda: entry.event_generate("<<Paste>>"))

    def show_menu(event):
        menu.tk_popup(event.x_root, event.y_root)
    entry.bind("<Button-3>", show_menu)  # ПКМ

# Загрузка api_id и hash
def load_config(filename="config.txt"):
    config = {}
    if os.path.exists(filename):
        with open(filename, "r", encoding="utf-8") as f:
            for line in f:
                if '=' in line:
                    key, value = line.strip().split("=", 1)
                    config[key.strip()] = value.strip()
    return config

# Загрузка сообщений
def load_messages(folder="message"):
    messages = []
    for i in range(1, 6):
        file_path = os.path.join(folder, f"msg{i}.txt")
        if os.path.exists(file_path):
            with open(file_path, "r", encoding="utf-8") as f:
                messages.append(f.read())
        else:
            messages.append(f"[Файл msg{i}.txt не найден]")
    return messages

class TelegramGUIApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Telegram Рассылка")
        self.root.geometry("420x480")

        self.config = load_config()
        self.api_id = int(self.config.get("api_id", 0))
        self.api_hash = self.config.get("api_hash", "")
        self.session_name = "tg_session"

        self.client = TelegramClient(self.session_name, self.api_id, self.api_hash)
        self.loop = asyncio.get_event_loop()

        self.me = None
        self.messages = load_messages()

        session_exists = os.path.exists(f"{self.session_name}.session")
        if session_exists:
            self.loop.run_until_complete(self.login_via_session())

        if self.me:
            self.create_main_frame()
        else:
            self.create_login_frame()

        self.root.after(100, self.run_async_loop)

    async def login_via_session(self):
        await self.client.connect()
        if not await self.client.is_user_authorized():
            return
        self.me = await self.client.get_me()

    def run_async_loop(self):
        self.loop.call_soon(self.loop.stop)
        self.loop.run_forever()
        self.root.after(100, self.run_async_loop)

    def create_login_frame(self):
        self.login_frame = tk.Frame(self.root)
        self.login_frame.pack()

        tk.Label(self.login_frame, text="Введите номер телефона:").pack(pady=5)
        self.phone_entry = tk.Entry(self.login_frame)
        self.phone_entry.pack(pady=5)
        add_context_menu(self.phone_entry)

        tk.Button(self.login_frame, text="Получить код", command=self.on_get_code).pack(pady=10)

        tk.Label(self.login_frame, text="Код подтверждения (из Telegram):").pack()
        self.code_entry = tk.Entry(self.login_frame)
        self.code_entry.pack(pady=5)
        add_context_menu(self.code_entry)

        tk.Label(self.login_frame, text="Пароль 2FA (если есть):").pack()
        self.password_entry = tk.Entry(self.login_frame, show="*")
        self.password_entry.pack(pady=5)
        add_context_menu(self.password_entry)

        self.login_status = tk.Label(self.login_frame, text="", fg="blue")
        self.login_status.pack(pady=10)

        tk.Button(self.login_frame, text="Войти", command=self.on_sign_in).pack(pady=10)

    def create_main_frame(self):
        self.main_frame = tk.Frame(self.root)
        self.main_frame.pack()

        username = self.me.username if self.me.username else "без username"
        tk.Label(self.main_frame, text=f"Аккаунт: {self.me.first_name} (@{username})").pack(pady=10)

        tk.Label(self.main_frame, text="Введите username (@username):").pack()
        self.username_entry = tk.Entry(self.main_frame)
        self.username_entry.pack(pady=5)
        add_context_menu(self.username_entry)

        tk.Label(self.main_frame, text="Выберите сообщение:").pack()
        self.message_combo = ttk.Combobox(self.main_frame, values=[f"Сообщение {i+1}" for i in range(5)])
        self.message_combo.current(0)
        self.message_combo.pack(pady=5)

        tk.Button(self.main_frame, text="Отправить", command=self.on_send).pack(pady=15)

        self.status_label = tk.Label(self.main_frame, text="", fg="blue")
        self.status_label.pack(pady=10)

    def on_get_code(self):
        phone = self.phone_entry.get().strip()
        if not phone.startswith("+"):
            self.login_status.config(text="Номер должен начинаться с +", fg="red")
            return

        async def request_code():
            try:
                await self.client.connect()
                await self.client.send_code_request(phone)
                self.login_status.config(text="✅ Код отправлен. Введите его ниже.", fg="green")
            except Exception as e:
                self.login_status.config(text=f"❌ Ошибка: {str(e)}", fg="red")

        self.loop.create_task(request_code())

    def on_sign_in(self):
        phone = self.phone_entry.get().strip()
        code = self.code_entry.get().strip()
        password = self.password_entry.get().strip()

        async def sign_in():
            try:
                await self.client.sign_in(phone, code)
                self.me = await self.client.get_me()
                self.login_frame.destroy()
                self.create_main_frame()
            except SessionPasswordNeededError:
                try:
                    await self.client.sign_in(password=password)
                    self.me = await self.client.get_me()
                    self.login_frame.destroy()
                    self.create_main_frame()
                except Exception as e:
                    self.login_status.config(text=f"❌ Неверный пароль 2FA: {str(e)}", fg="red")
            except Exception as e:
                self.login_status.config(text=f"❌ Ошибка входа: {str(e)}", fg="red")

        self.loop.create_task(sign_in())

    def on_send(self):
        username = self.username_entry.get().strip()
        if not username.startswith("@"):
            self.status_label.config(text="❌ Username должен начинаться с @", fg="red")
            return

        index = self.message_combo.current()
        text = self.messages[index]

        self.status_label.config(text="⏳ Отправка...", fg="black")
        self.loop.create_task(self.send_message(username, text))

    async def send_message(self, username, text):
        try:
            await self.client.send_message(username, text)
            self.status_label.config(text=f"✅ Сообщение отправлено {username}", fg="green")
        except Exception as e:
            self.status_label.config(text=f"❌ Ошибка: {str(e)}", fg="red")

if __name__ == "__main__":
    root = tk.Tk()
    app = TelegramGUIApp(root)
    root.mainloop()
