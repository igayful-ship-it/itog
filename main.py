import tkinter as tk
from tkinter import ttk, messagebox
import requests
import json
import os
from datetime import datetime
from threading import Thread

# ---------- Конфигурация ----------
FAVORITES_FILE = "favorites.json"
GITHUB_API_SEARCH = "https://api.github.com/search/users"

class GitHubUserFinder:
    def __init__(self, root):
        self.root = root
        self.root.title("GitHub User Finder")
        self.root.geometry("800x600")
        self.root.resizable(True, True)

        # Загрузка избранных
        self.favorites = self.load_favorites()

        # Создание GUI
        self.create_widgets()

        # Обновление списка избранных при старте
        self.update_favorites_list()

    def create_widgets(self):
        # Верхняя панель: поле поиска + кнопка
        top_frame = ttk.Frame(self.root, padding=10)
        top_frame.pack(fill=tk.X)

        ttk.Label(top_frame, text="Введите имя пользователя GitHub:").pack(side=tk.LEFT, padx=5)
        self.search_entry = ttk.Entry(top_frame, width=30)
        self.search_entry.pack(side=tk.LEFT, padx=5)
        self.search_btn = ttk.Button(top_frame, text="Поиск", command=self.search_users)
        self.search_btn.pack(side=tk.LEFT, padx=5)

        # Панель с результатами поиска
        search_frame = ttk.LabelFrame(self.root, text="Результаты поиска", padding=10)
        search_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        # Таблица результатов
        self.result_tree = ttk.Treeview(search_frame, columns=("login", "id", "url"), show="headings", height=10)
        self.result_tree.heading("login", text="Логин")
        self.result_tree.heading("id", text="ID")
        self.result_tree.heading("url", text="URL профиля")
        self.result_tree.column("login", width=150)
        self.result_tree.column("id", width=80)
        self.result_tree.column("url", width=300)
        self.result_tree.pack(fill=tk.BOTH, expand=True)

        # Кнопка "Добавить в избранное" под таблицей
        btn_frame = ttk.Frame(search_frame)
        btn_frame.pack(fill=tk.X, pady=5)
        ttk.Button(btn_frame, text="★ Добавить выбранного в избранное", command=self.add_to_favorites).pack()

        # Панель избранного
        fav_frame = ttk.LabelFrame(self.root, text="Избранные пользователи", padding=10)
        fav_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        self.fav_listbox = tk.Listbox(fav_frame, height=6)
        self.fav_listbox.pack(fill=tk.BOTH, expand=True, side=tk.LEFT)

        scrollbar = ttk.Scrollbar(fav_frame, orient=tk.VERTICAL, command=self.fav_listbox.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.fav_listbox.config(yscrollcommand=scrollbar.set)

        # Кнопки управления избранным
        fav_btn_frame = ttk.Frame(fav_frame)
        fav_btn_frame.pack(side=tk.RIGHT, fill=tk.Y, padx=5)
        ttk.Button(fav_btn_frame, text="Удалить из избранного", command=self.remove_from_favorites).pack(pady=2)
        ttk.Button(fav_btn_frame, text="Очистить избранное", command=self.clear_favorites).pack(pady=2)

        # Статусная строка
        self.status_var = tk.StringVar()
        self.status_var.set("Готов. Введите имя для поиска.")
        status_bar = ttk.Label(self.root, textvariable=self.status_var, relief=tk.SUNKEN, anchor=tk.W)
        status_bar.pack(side=tk.BOTTOM, fill=tk.X)

    # ---------- Работа с избранными (JSON) ----------
    def load_favorites(self):
        if os.path.exists(FAVORITES_FILE):
            try:
                with open(FAVORITES_FILE, "r", encoding="utf-8") as f:
                    return json.load(f)
            except:
                return []
        return []

    def save_favorites(self):
        with open(FAVORITES_FILE, "w", encoding="utf-8") as f:
            json.dump(self.favorites, f, indent=4, ensure_ascii=False)

    def update_favorites_list(self):
        """Обновляет отображение списка избранных"""
        self.fav_listbox.delete(0, tk.END)
        for user in self.favorites:
            self.fav_listbox.insert(tk.END, f"{user['login']} (ID: {user['id']})")

    # ---------- Поиск через GitHub API ----------
    def search_users(self):
        # Проверка на пустое поле
        query = self.search_entry.get().strip()
        if not query:
            messagebox.showwarning("Внимание", "Поле поиска не должно быть пустым!")
            return

        # Отключаем кнопку на время запроса
        self.search_btn.config(state=tk.DISABLED)
        self.status_var.set("Поиск...")
        self.result_tree.delete(*self.result_tree.get_children())

        # Запрос в отдельном потоке, чтобы не блокировать GUI
        Thread(target=self.perform_search, args=(query,), daemon=True).start()

    def perform_search(self, query):
        try:
            url = f"{GITHUB_API_SEARCH}?q={query}&per_page=30"
            response = requests.get(url, headers={"Accept": "application/vnd.github.v3+json"})
            if response.status_code == 200:
                data = response.json()
                users = data.get("items", [])
                if not users:
                    self.root.after(0, lambda: messagebox.showinfo("Результат", "Пользователи не найдены."))
                    self.root.after(0, self.clear_search_results)
                else:
                    for user in users:
                        self.root.after(0, lambda u=user: self.add_search_result(u))
                    self.root.after(0, lambda: self.status_var.set(f"Найдено {len(users)} пользователей."))
            else:
                self.root.after(0, lambda: messagebox.showerror("Ошибка API", f"Код {response.status_code}\n{response.text}"))
                self.root.after(0, self.clear_search_results)
        except Exception as e:
            self.root.after(0, lambda: messagebox.showerror("Ошибка", str(e)))
            self.root.after(0, self.clear_search_results)
        finally:
            self.root.after(0, lambda: self.search_btn.config(state=tk.NORMAL))

    def add_search_result(self, user):
        self.result_tree.insert("", tk.END, values=(user["login"], user["id"], user["html_url"]))

    def clear_search_results(self):
        self.result_tree.delete(*self.result_tree.get_children())
        self.status_var.set("Готов.")

    # ---------- Добавление в избранное ----------
    def add_to_favorites(self):
        selected = self.result_tree.selection()
        if not selected:
            messagebox.showinfo("Информация", "Сначала выберите пользователя из результатов поиска.")
            return

        values = self.result_tree.item(selected[0])["values"]
        login, user_id, url = values

        # Проверяем, есть ли уже в избранном
        for fav in self.favorites:
            if fav["id"] == user_id:
                messagebox.showwarning("Уже в избранном", f"Пользователь {login} уже добавлен.")
                return

        new_fav = {
            "login": login,
            "id": user_id,
            "url": url,
            "added_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        self.favorites.append(new_fav)
        self.save_favorites()
        self.update_favorites_list()
        self.status_var.set(f"Пользователь {login} добавлен в избранное.")

    # ---------- Удаление из избранного ----------
    def remove_from_favorites(self):
        selection = self.fav_listbox.curselection()
        if not selection:
            messagebox.showinfo("Информация", "Выберите пользователя в списке избранных.")
            return
        index = selection[0]
        removed = self.favorites.pop(index)
        self.save_favorites()
        self.update_favorites_list()
        self.status_var.set(f"Пользователь {removed['login']} удалён из избранного.")

    def clear_favorites(self):
        if messagebox.askyesno("Подтверждение", "Удалить всех избранных пользователей?"):
            self.favorites.clear()
            self.save_favorites()
            self.update_favorites_list()
            self.status_var.set("Избранное очищено.")

if __name__ == "__main__":
    root = tk.Tk()
    app = GitHubUserFinder(root)
    root.mainloop()