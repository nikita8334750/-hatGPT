"""Personal smart assistant bot (CLI)."""

from __future__ import annotations

import json
import re
import sqlite3
import shlex
from dataclasses import dataclass, field
from datetime import datetime, timedelta, time
from pathlib import Path
from typing import Callable

DATE_FMT = "%Y-%m-%d %H:%M"


@dataclass
class Task:
    title: str
    created_at: str
    done: bool = False
    priority: str = "средний"
    due_date: str | None = None


@dataclass
class Note:
    title: str
    body: str
    created_at: str


@dataclass
class AssistantState:
    tasks: list[Task] = field(default_factory=list)
    notes: list[Note] = field(default_factory=list)
    habits: list[dict] = field(default_factory=list)
    shopping: list[dict] = field(default_factory=list)
    reminders: list[dict] = field(default_factory=list)
    quick_answers: dict[str, str] = field(default_factory=dict)
    profile: dict[str, str] = field(default_factory=dict)
    response_settings: dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "tasks": [task.__dict__ for task in self.tasks],
            "notes": [note.__dict__ for note in self.notes],
            "habits": self.habits,
            "shopping": self.shopping,
            "reminders": self.reminders,
            "quick_answers": self.quick_answers,
            "profile": self.profile,
            "response_settings": self.response_settings,
        }

    @classmethod
    def from_dict(cls, payload: dict) -> "AssistantState":
        tasks = [Task(**item) for item in payload.get("tasks", [])]
        notes = [Note(**item) for item in payload.get("notes", [])]
        return cls(
            tasks=tasks,
            notes=notes,
            habits=payload.get("habits", []),
            shopping=payload.get("shopping", []),
            reminders=payload.get("reminders", []),
            quick_answers=payload.get("quick_answers", {}),
            profile=payload.get("profile", {}),
            response_settings=payload.get("response_settings", {}),
        )


class SmartAssistant:
    RESPONSE_OPTIONS = {
        "tone": ["нейтральный", "деловой", "дружелюбный"],
        "detail": ["кратко", "средне", "подробно"],
        "format": ["список", "абзац"],
        "structure": ["свободная", "шаги", "чек-лист", "таблица"],
        "emoji": ["нет", "минимум", "акцент"],
        "style": ["лаконичный", "аналитический", "мотивационный", "техничный"],
    }
    INTENT_RESPONSES = [
        {"name": "приветствие", "keywords": ["привет", "здравств", "добрый", "hello"], "response": "Привет! Чем помочь?"},
        {"name": "помощь", "keywords": ["помощь", "help", "что умеешь"], "response": "Могу управлять задачами, заметками, привычками и давать стратегические ответы. Команда help покажет список."},
        {"name": "добавить задачу", "keywords": ["добавь задачу", "создай задачу", "новая задача"], "response": "Используйте: add-task <текст> (CLI) или /add_task <текст> (Telegram)."},
        {"name": "список задач", "keywords": ["список задач", "покажи задачи", "tasks"], "response": "Команда: list-tasks (CLI) или /tasks (Telegram)."},
        {"name": "закрыть задачу", "keywords": ["закрыть задачу", "выполнить задачу", "done"], "response": "Команда: done <номер> (CLI) или /done <номер> (Telegram)."},
        {"name": "удалить задачу", "keywords": ["удалить задачу", "remove task", "remove-task"], "response": "Команда: remove-task <номер> (CLI) или /remove_task <номер> (Telegram)."},
        {"name": "очистить выполненные", "keywords": ["очистить выполненные", "clear done", "clear-done"], "response": "Команда: clear-done (CLI) или /clear_done (Telegram)."},
        {"name": "добавить заметку", "keywords": ["добавь заметку", "новая заметка"], "response": "Команда: add-note <заголовок> :: <тело>."},
        {"name": "список заметок", "keywords": ["список заметок", "покажи заметки", "notes"], "response": "Команда: list-notes (CLI) или /notes (Telegram)."},
        {"name": "удалить заметку", "keywords": ["удалить заметку", "remove note"], "response": "Команда: remove-note <номер> (CLI) или /remove_note <номер> (Telegram)."},
        {"name": "добавить привычку", "keywords": ["добавь привычку", "новая привычка"], "response": "Команда: add-habit <название> :: <частота>."},
        {"name": "список привычек", "keywords": ["список привычек", "покажи привычки"], "response": "Команда: list-habits."},
        {"name": "отметить привычку", "keywords": ["отметь привычку", "habit done"], "response": "Команда: habit-done <номер>."},
        {"name": "покупки", "keywords": ["покупки", "список покупок", "buys"], "response": "Команды: add-buy, list-buys, buy."},
        {"name": "напоминания", "keywords": ["напоминани", "remind"], "response": "Команды: remind, list-reminders, remind-done."},
        {"name": "поиск", "keywords": ["поиск", "search"], "response": "Команда: search <запрос>."},
        {"name": "статистика", "keywords": ["статистика", "stats", "сводка"], "response": "Команда: stats."},
        {"name": "экспорт", "keywords": ["экспорт", "export"], "response": "Команда: export <путь>."},
        {"name": "импорт", "keywords": ["импорт", "import"], "response": "Команда: import <путь>."},
        {"name": "приоритет", "keywords": ["приоритет", "priority"], "response": "Команда: set-priority <номер> :: <уровень>."},
        {"name": "срок", "keywords": ["срок", "deadline", "due"], "response": "Команда: set-due <номер> :: <YYYY-MM-DD>."},
        {"name": "повестка", "keywords": ["повестка", "agenda"], "response": "Команда: agenda."},
        {"name": "вариативность", "keywords": ["вариатив", "варианты", "variations"], "response": "Команда: variations <тема>."},
        {"name": "анализ", "keywords": ["анализ", "analyze"], "response": "Команда: analyze <контекст>."},
        {"name": "план", "keywords": ["план", "plan"], "response": "Команда: plan <контекст>."},
        {"name": "питч", "keywords": ["питч", "pitch"], "response": "Команда: pitch <контекст>."},
        {"name": "оценка", "keywords": ["оценка", "estimate"], "response": "Команда: estimate <контекст>."},
        {"name": "техразбор", "keywords": ["технический", "tech", "архитектур"], "response": "Команда: tech <контекст>."},
        {"name": "профиль", "keywords": ["профиль", "profile"], "response": "Команды: set-profile и profile."},
        {"name": "параметры ответов", "keywords": ["параметры ответов", "response", "тон", "детальность", "формат"], "response": "Команды: set-response и response."},
        {"name": "варианты ответов", "keywords": ["варианты ответов", "response-variants", "set-response-variant"], "response": "Команды: response-variants и set-response-variant <номер>."},
        {"name": "telegram", "keywords": ["telegram", "телеграм"], "response": "Запуск: export TELEGRAM_BOT_TOKEN=...; python src/telegram_bot.py."},
        {"name": "запуск cli", "keywords": ["запуск", "cli", "терминал"], "response": "Запуск CLI: python src/assistant_bot.py."},
        {"name": "хранение", "keywords": ["где хран", "storage", "json", "db"], "response": "Состояние хранится локально в assistant_state.db рядом с кодом (SQLite)."},
        {"name": "безопасность", "keywords": ["безопасность", "privacy", "приватность"], "response": "Данные хранятся локально, без внешних сервисов (кроме Telegram при использовании)."},
        {"name": "интеграции", "keywords": ["интеграции", "api", "webhook"], "response": "Сейчас поддерживается Telegram и CLI. Другие интеграции не добавлены."},
        {"name": "ошибка", "keywords": ["ошибка", "bug", "не работает"], "response": "Опишите шаги и сообщение ошибки — помогу разобрать."},
        {"name": "предложения", "keywords": ["предложение", "идея", "улучшение"], "response": "Сформулируйте цель улучшения и ограничения — предложу план."},
        {"name": "стоимость", "keywords": ["стоимость", "цена", "price"], "response": "I don't have reliable information on this."},
        {"name": "дорожная карта", "keywords": ["roadmap", "дорожная карта"], "response": "I don't have reliable information on this."},
        {"name": "инструкции", "keywords": ["инструкция", "как пользоваться"], "response": "Используйте help для списка команд и README для примеров."},
        {"name": "время", "keywords": ["время", "time"], "response": "Команды с датой используют формат YYYY-MM-DD."},
        {"name": "экспорт бэкап", "keywords": ["бэкап", "backup"], "response": "Сделайте export в файл, затем сохраните его отдельно."},
        {"name": "скорость", "keywords": ["быстро", "скорость", "performance"], "response": "Оптимизации выполнены на уровне логики; критично влияет объём данных."},
        {"name": "роль", "keywords": ["роль", "role"], "response": "Задайте роль через set-profile, чтобы ответы были релевантнее."},
        {"name": "ограничения", "keywords": ["ограничения", "constraints"], "response": "Укажите ограничения в профиле или в запросе."},
        {"name": "метрики", "keywords": ["метрики", "kpi"], "response": "В анализе используйте KPI: активация, конверсия, ROI."},
        {"name": "mvp", "keywords": ["mvp", "минимальный продукт"], "response": "Рекомендуется MVP с одной ключевой функцией для проверки спроса."},
        {"name": "клиенты", "keywords": ["клиент", "user", "пользователь"], "response": "Сфокусируйтесь на проблеме и ценности для пользователя."},
        {"name": "финансы", "keywords": ["бюджет", "fin", "финансы"], "response": "Зафиксируйте бюджет/сроки в профиле, затем планируйте шаги."},
        {"name": "риски", "keywords": ["риск", "risks"], "response": "Используйте premortem и second-order для оценки рисков."},
        {"name": "приоритизация", "keywords": ["приоритизация", "prioritize"], "response": "Команда: priority <тема>."},
        {"name": "чек-лист", "keywords": ["чек-лист", "checklist"], "response": "Команда: checklist <тема>."},
        {"name": "структура", "keywords": ["структура ответа", "формат ответа"], "response": "Параметры ответа задаются через set-response или set-response-variant."},
        {"name": "эмодзи", "keywords": ["эмодзи", "emoji"], "response": "Вариант эмодзи выбирается через set-response-variant."},
        {"name": "стиль", "keywords": ["стиль", "style"], "response": "Стиль ответа выбирается через set-response-variant."},
        {"name": "таблица", "keywords": ["таблица", "table"], "response": "Структура ответа может быть 'таблица' через set-response-variant."},
        {"name": "шаги", "keywords": ["шаги", "steps"], "response": "Структура 'шаги' доступна через set-response-variant."},
        {"name": "итог", "keywords": ["итог", "summary"], "response": "Могу дать краткий итог по запросу — уточните контекст."},
        {"name": "отчёт", "keywords": ["отчёт", "report"], "response": "Сформулируйте тему отчёта и критерии — подготовлю структуру."},
        {"name": "получить помощь", "keywords": ["что делать дальше", "next"], "response": "Опишите цель, ограничения и желаемый результат."},
        {"name": "поддержка", "keywords": ["support", "поддержка"], "response": "Опишите проблему — помогу диагностировать."},
        {"name": "разработка", "keywords": ["разработка", "dev"], "response": "Могу предложить план реализации и технический разбор."},
        {"name": "бизнес", "keywords": ["бизнес", "market"], "response": "Могу сделать анализ, питч и план."},
        {"name": "тесты", "keywords": ["тесты", "testing"], "response": "Тестирование включает unit, интеграционные и e2e."},
        {"name": "инструменты", "keywords": ["инструменты", "tools"], "response": "Сейчас доступны команды CLI/Telegram и стратегические модули."},
        {"name": "команды", "keywords": ["команды", "commands"], "response": "Введите help для списка команд."},
    ]
    def __init__(self, storage_path: Path) -> None:
        self.storage_path = storage_path
        self.state = self._load_state()

    def _load_state(self) -> AssistantState:
        if self.storage_path.suffix == ".db":
            return self._load_state_from_db()
        if not self.storage_path.exists():
            return AssistantState()
        payload = json.loads(self.storage_path.read_text(encoding="utf-8"))
        return AssistantState.from_dict(payload)

    def _save_state(self) -> None:
        if self.storage_path.suffix == ".db":
            self._save_state_to_db()
            return
        self.storage_path.write_text(
            json.dumps(self.state.to_dict(), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def _init_db(self, connection: sqlite3.Connection) -> None:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS assistant_state (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                payload TEXT NOT NULL
            )
            """
        )
        connection.commit()

    def _load_state_from_db(self) -> AssistantState:
        connection = sqlite3.connect(self.storage_path)
        try:
            self._init_db(connection)
            cursor = connection.execute(
                "SELECT payload FROM assistant_state WHERE id = 1"
            )
            row = cursor.fetchone()
            if row is None:
                state = AssistantState()
                payload = json.dumps(
                    state.to_dict(), ensure_ascii=False, indent=2
                )
                connection.execute(
                    "INSERT INTO assistant_state (id, payload) VALUES (1, ?)",
                    (payload,),
                )
                connection.commit()
                return state
            payload = json.loads(row[0])
            return AssistantState.from_dict(payload)
        finally:
            connection.close()

    def _save_state_to_db(self) -> None:
        connection = sqlite3.connect(self.storage_path)
        try:
            self._init_db(connection)
            payload = json.dumps(
                self.state.to_dict(), ensure_ascii=False, indent=2
            )
            connection.execute(
                """
                INSERT INTO assistant_state (id, payload)
                VALUES (1, ?)
                ON CONFLICT(id) DO UPDATE SET payload = excluded.payload
                """,
                (payload,),
            )
            connection.commit()
        finally:
            connection.close()

    def _now(self) -> str:
        return datetime.now().strftime(DATE_FMT)

    def _today(self) -> str:
        return datetime.now().strftime("%Y-%m-%d")

    def add_task(self, title: str) -> str:
        task = Task(title=title, created_at=self._now())
        self.state.tasks.append(task)
        self._save_state()
        return f"Задача добавлена: {title}"

    def set_task_priority(self, index: int, priority: str) -> str:
        if index < 1 or index > len(self.state.tasks):
            return "Неверный номер задачи."
        normalized = priority.strip().lower()
        allowed = {"низкий", "средний", "высокий"}
        if normalized not in allowed:
            return "Приоритет должен быть: низкий, средний или высокий."
        self.state.tasks[index - 1].priority = normalized
        self._save_state()
        return "Приоритет обновлён."

    def set_task_due_date(self, index: int, due_date: str) -> str:
        if index < 1 or index > len(self.state.tasks):
            return "Неверный номер задачи."
        try:
            datetime.strptime(due_date, "%Y-%m-%d")
        except ValueError:
            return "Формат даты: YYYY-MM-DD."
        self.state.tasks[index - 1].due_date = due_date
        self._save_state()
        return "Срок задачи обновлён."

    def remove_task(self, index: int) -> str:
        if index < 1 or index > len(self.state.tasks):
            return "Неверный номер задачи."
        removed = self.state.tasks.pop(index - 1)
        self._save_state()
        return f"Задача удалена: {removed.title}"

    def clear_completed_tasks(self) -> str:
        before = len(self.state.tasks)
        self.state.tasks = [task for task in self.state.tasks if not task.done]
        removed = before - len(self.state.tasks)
        self._save_state()
        return f"Удалено выполненных задач: {removed}"

    def list_tasks(self) -> str:
        if not self.state.tasks:
            return "Список задач пуст."
        lines = ["Задачи:"]
        for index, task in enumerate(self.state.tasks, start=1):
            status = "✅" if task.done else "🟡"
            due = f", срок {task.due_date}" if task.due_date else ""
            lines.append(
                f"{index}. {status} {task.title} "
                f"(создано {task.created_at}, приоритет {task.priority}{due})"
            )
        return "\n".join(lines)

    def complete_task(self, index: int) -> str:
        if index < 1 or index > len(self.state.tasks):
            return "Неверный номер задачи."
        self.state.tasks[index - 1].done = True
        self._save_state()
        return "Задача отмечена выполненной."

    def add_note(self, title: str, body: str) -> str:
        note = Note(title=title, body=body, created_at=self._now())
        self.state.notes.append(note)
        self._save_state()
        return f"Заметка сохранена: {title}"

    def remove_note(self, index: int) -> str:
        if index < 1 or index > len(self.state.notes):
            return "Неверный номер заметки."
        removed = self.state.notes.pop(index - 1)
        self._save_state()
        return f"Заметка удалена: {removed.title}"

    def list_notes(self) -> str:
        if not self.state.notes:
            return "Заметок пока нет."
        lines = ["Заметки:"]
        for index, note in enumerate(self.state.notes, start=1):
            lines.append(
                f"{index}. {note.title} (создано {note.created_at})\n   {note.body}"
            )
        return "\n".join(lines)

    def add_habit(self, title: str, frequency: str) -> str:
        habit = {
            "title": title,
            "frequency": frequency,
            "created_at": self._now(),
            "last_done": None,
            "streak": 0,
        }
        self.state.habits.append(habit)
        self._save_state()
        return f"Привычка добавлена: {title}"

    def list_habits(self) -> str:
        if not self.state.habits:
            return "Привычек пока нет."
        lines = ["Привычки:"]
        for index, habit in enumerate(self.state.habits, start=1):
            streak = habit.get("streak", 0)
            last_done = habit.get("last_done") or "ещё не отмечалось"
            lines.append(
                f"{index}. {habit['title']} ({habit['frequency']}) | серия: {streak} | "
                f"последний раз: {last_done}"
            )
        return "\n".join(lines)

    def complete_habit(self, index: int) -> str:
        if index < 1 or index > len(self.state.habits):
            return "Неверный номер привычки."
        habit = self.state.habits[index - 1]
        habit["streak"] = habit.get("streak", 0) + 1
        habit["last_done"] = self._now()
        self._save_state()
        return "Привычка отмечена."

    def add_shopping_item(self, title: str) -> str:
        self.state.shopping.append(
            {"title": title, "added_at": self._now(), "purchased": False}
        )
        self._save_state()
        return f"Добавлено в список покупок: {title}"

    def list_shopping(self) -> str:
        if not self.state.shopping:
            return "Список покупок пуст."
        lines = ["Покупки:"]
        for index, item in enumerate(self.state.shopping, start=1):
            status = "✅" if item.get("purchased") else "🛒"
            lines.append(f"{index}. {status} {item['title']} (добавлено {item['added_at']})")
        return "\n".join(lines)

    def mark_shopping_item(self, index: int) -> str:
        if index < 1 or index > len(self.state.shopping):
            return "Неверный номер покупки."
        self.state.shopping[index - 1]["purchased"] = True
        self._save_state()
        return "Покупка отмечена."

    def add_reminder(self, title: str, minutes: int) -> str:
        remind_at = datetime.now() + timedelta(minutes=minutes)
        reminder = self._build_reminder(title, remind_at)
        self.state.reminders.append(reminder)
        self._save_state()
        return f"Напоминание установлено на {reminder['remind_at']}"

    def add_reminder_at(
        self, title: str, remind_at: datetime, repeat: str | None = None
    ) -> str:
        reminder = self._build_reminder(title, remind_at, repeat)
        self.state.reminders.append(reminder)
        self._save_state()
        repeat_note = f" (повтор: {repeat})" if repeat else ""
        return f"Напоминание установлено на {reminder['remind_at']}{repeat_note}"

    def _build_reminder(
        self, title: str, remind_at: datetime, repeat: str | None = None
    ) -> dict:
        reminder = {
            "title": title,
            "remind_at": remind_at.strftime(DATE_FMT),
            "created_at": self._now(),
            "done": False,
        }
        if repeat:
            reminder["repeat"] = repeat
        return reminder

    def list_reminders(self) -> str:
        if not self.state.reminders:
            return "Напоминаний пока нет."
        lines = ["Напоминания:"]
        for index, reminder in enumerate(self.state.reminders, start=1):
            status = "✅" if reminder.get("done") else "⏰"
            repeat = reminder.get("repeat")
            repeat_note = f", повтор: {repeat}" if repeat else ""
            lines.append(
                f"{index}. {status} {reminder['title']} (к {reminder['remind_at']}{repeat_note})"
            )
        return "\n".join(lines)

    def mark_reminder(self, index: int) -> str:
        if index < 1 or index > len(self.state.reminders):
            return "Неверный номер напоминания."
        reminder = self.state.reminders[index - 1]
        repeat = reminder.get("repeat")
        if repeat:
            current = datetime.strptime(reminder["remind_at"], DATE_FMT)
            next_at = self._next_repeat_datetime(current, repeat)
            reminder["remind_at"] = next_at.strftime(DATE_FMT)
            reminder["done"] = False
            self._save_state()
            return f"Напоминание перенесено на {reminder['remind_at']}."
        reminder["done"] = True
        self._save_state()
        return "Напоминание отмечено."

    def _next_repeat_datetime(self, current: datetime, repeat: str) -> datetime:
        if repeat == "daily":
            return current + timedelta(days=1)
        if repeat == "weekly":
            return current + timedelta(days=7)
        if repeat == "monthly":
            return current + timedelta(days=30)
        if repeat.startswith("weekly:"):
            weekday = int(repeat.split(":", 1)[1])
            days_ahead = (weekday - current.weekday() + 7) % 7
            if days_ahead == 0:
                days_ahead = 7
            return current + timedelta(days=days_ahead)
        return current + timedelta(days=1)

    def interpret_message(self, message: str) -> str | None:
        normalized = message.strip()
        if not normalized:
            return None
        lower = normalized.lower()
        if any(key in lower for key in ["что у меня на сегодня", "что на сегодня", "на сегодня"]):
            return self.agenda()
        if any(key in lower for key in ["список дел", "мои задачи", "задачи"]):
            return self.list_tasks()
        if any(key in lower for key in ["список покуп", "покупки"]):
            return self.list_shopping()
        if any(key in lower for key in ["заметки", "мои заметки"]):
            return self.list_notes()
        if any(word in lower for word in ["напомни", "напомнить", "remind"]):
            return self._handle_natural_reminder(normalized)
        if any(word in lower for word in ["купи", "купить", "добавь в список покупок"]):
            return self._handle_natural_buy(normalized)
        if any(word in lower for word in ["добавь задачу", "задача", "надо", "нужно", "сделай"]):
            return self._handle_natural_task(normalized)
        return None

    def _handle_natural_buy(self, message: str) -> str:
        title = self._strip_leading_phrases(
            message,
            [
                "купи",
                "купить",
                "добавь в список покупок",
                "добавь покупки",
            ],
        )
        title = title.strip()
        if not title:
            return "Уточните, что нужно купить."
        return self.add_shopping_item(title)

    def _handle_natural_task(self, message: str) -> str:
        date = self._parse_date_from_text(message)
        title = self._strip_leading_phrases(
            message,
            ["добавь задачу", "задача", "надо", "нужно", "сделай"],
        )
        title = self._strip_date_phrases(title).strip(" ,.")
        if not title:
            return "Уточните задачу."
        response = self.add_task(title)
        if date:
            self.set_task_due_date(len(self.state.tasks), date.strftime("%Y-%m-%d"))
            return f"{response} Срок: {date.strftime('%Y-%m-%d')}."
        return response

    def _handle_natural_reminder(self, message: str) -> str:
        parsed = self._parse_datetime_from_text(message)
        if parsed is None:
            return "Уточните дату и время для напоминания."
        remind_at, repeat = parsed
        title = self._strip_leading_phrases(
            message,
            ["напомни", "напомнить", "remind", "пожалуйста", "мне"],
        )
        title = self._strip_time_phrases(title).strip(" ,.")
        if not title:
            return "Уточните, о чём напомнить."
        return self.add_reminder_at(title, remind_at, repeat)

    def _parse_datetime_from_text(
        self, message: str
    ) -> tuple[datetime, str | None] | None:
        lower = message.lower()
        date = self._parse_date_from_text(lower)
        time = self._parse_time_from_text(lower)
        repeat = self._parse_repeat_from_text(lower)
        if date is None and time is None:
            return None
        if date is None:
            date = datetime.now()
        if time is None:
            return None
        remind_at = datetime.combine(date.date(), time)
        if remind_at < datetime.now():
            remind_at += timedelta(days=1)
        return remind_at, repeat

    def _parse_time_from_text(self, text: str) -> time | None:
        match = re.search(r"\b(\d{1,2})[:.](\d{2})\b", text)
        if match:
            hour = int(match.group(1))
            minute = int(match.group(2))
            if 0 <= hour < 24 and 0 <= minute < 60:
                return datetime.now().replace(hour=hour, minute=minute, second=0, microsecond=0).time()
        match = re.search(r"\b(\d{1,2})\s*(?:час|ч)\b", text)
        if match:
            hour = int(match.group(1))
            minute_match = re.search(r"\b(\d{1,2})\s*мин", text)
            minute = int(minute_match.group(1)) if minute_match else 0
            if 0 <= hour < 24 and 0 <= minute < 60:
                return datetime.now().replace(hour=hour, minute=minute, second=0, microsecond=0).time()
        return None

    def _parse_date_from_text(self, text: str) -> datetime | None:
        lower = text.lower()
        today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        if "сегодня" in lower:
            return today
        if "завтра" in lower:
            return today + timedelta(days=1)
        if "послезавтра" in lower:
            return today + timedelta(days=2)
        weekdays = {
            "понедельник": 0,
            "вторник": 1,
            "среду": 2,
            "среда": 2,
            "четверг": 3,
            "пятницу": 4,
            "пятница": 4,
            "субботу": 5,
            "суббота": 5,
            "воскресенье": 6,
        }
        for name, weekday in weekdays.items():
            if name in lower:
                days_ahead = (weekday - today.weekday() + 7) % 7
                if days_ahead == 0:
                    days_ahead = 7
                return today + timedelta(days=days_ahead)
        match = re.search(r"\b(\d{4})-(\d{2})-(\d{2})\b", lower)
        if match:
            year, month, day = map(int, match.groups())
            try:
                return datetime(year, month, day)
            except ValueError:
                return None
        return None

    def _parse_repeat_from_text(self, text: str) -> str | None:
        lower = text.lower()
        if "каждый день" in lower or "ежедневно" in lower:
            return "daily"
        if "каждую неделю" in lower or "еженедельно" in lower:
            return "weekly"
        if "каждый месяц" in lower or "ежемесячно" in lower:
            return "monthly"
        weekdays = {
            "понедельник": 0,
            "вторник": 1,
            "среду": 2,
            "среда": 2,
            "четверг": 3,
            "пятницу": 4,
            "пятница": 4,
            "субботу": 5,
            "суббота": 5,
            "воскресенье": 6,
        }
        for name, weekday in weekdays.items():
            if f"каждый {name}" in lower or f"каждую {name}" in lower:
                return f"weekly:{weekday}"
        return None

    def _strip_leading_phrases(self, text: str, phrases: list[str]) -> str:
        cleaned = text.strip()
        for phrase in phrases:
            pattern = re.compile(rf"^\s*{re.escape(phrase)}\s*", re.IGNORECASE)
            cleaned = pattern.sub("", cleaned)
        return cleaned

    def _strip_time_phrases(self, text: str) -> str:
        cleaned = re.sub(r"\b(сегодня|завтра|послезавтра)\b", "", text, flags=re.IGNORECASE)
        cleaned = re.sub(
            r"\b(в\s+\d{1,2}[:.]\d{2}|\d{1,2}\s*(?:час|ч)(?:\s*\d{1,2}\s*мин)?)\b",
            "",
            cleaned,
            flags=re.IGNORECASE,
        )
        cleaned = re.sub(
            r"\b(в\s+понедельник|во\s+вторник|в\s+среду|в\s+четверг|в\s+пятницу|в\s+субботу|в\s+воскресенье)\b",
            "",
            cleaned,
            flags=re.IGNORECASE,
        )
        cleaned = re.sub(r"\bкаждый\b|\bкаждую\b|\bежедневно\b|\bеженедельно\b|\bежемесячно\b", "", cleaned, flags=re.IGNORECASE)
        return cleaned

    def _strip_date_phrases(self, text: str) -> str:
        cleaned = self._strip_time_phrases(text)
        cleaned = re.sub(r"\bдо\b|\bк\b", "", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"\b\d{4}-\d{2}-\d{2}\b", "", cleaned)
        return cleaned

    def add_quick_answer(self, key: str, value: str) -> str:
        self.state.quick_answers[key] = value
        self._save_state()
        return f"Шаблон ответа сохранён: {key}"

    def get_quick_answer(self, key: str) -> str:
        answer = self.state.quick_answers.get(key)
        if not answer:
            return "Шаблон не найден."
        return answer

    def set_profile(self, role: str, goal: str, constraints: str) -> str:
        self.state.profile = {
            "role": role,
            "goal": goal,
            "constraints": constraints,
        }
        self._save_state()
        return "Профиль обновлён."

    def get_profile(self) -> str:
        if not self.state.profile:
            return "Профиль не задан."
        role = self.state.profile.get("role", "не указан")
        goal = self.state.profile.get("goal", "не указана")
        constraints = self.state.profile.get("constraints", "не указаны")
        return (
            "Профиль:\n"
            f"- Роль: {role}\n"
            f"- Цель: {goal}\n"
            f"- Ограничения: {constraints}"
        )

    def set_response_settings(self, tone: str, detail: str, format_style: str) -> str:
        normalized = self.normalize_response_settings(tone, detail, format_style)
        if normalized is None:
            return "Допустимо: тон=нейтральный/деловой/дружелюбный, детальность=кратко/средне/подробно, формат=список/абзац."
        self.state.response_settings = normalized
        self._save_state()
        return "Параметры ответов обновлены."

    def get_response_settings(self) -> dict[str, str]:
        defaults = {
            "tone": "нейтральный",
            "detail": "средне",
            "format": "список",
            "structure": "свободная",
            "emoji": "нет",
            "style": "лаконичный",
        }
        return {**defaults, **self.state.response_settings}

    def normalize_response_settings(
        self, tone: str, detail: str, format_style: str
    ) -> dict[str, str] | None:
        tone_map = {
            "нейтр": "нейтральный",
            "нейтральный": "нейтральный",
            "деловой": "деловой",
            "дружелюбный": "дружелюбный",
        }
        detail_map = {
            "кратко": "кратко",
            "средне": "средне",
            "подробно": "подробно",
            "детально": "подробно",
        }
        format_map = {
            "список": "список",
            "абзац": "абзац",
        }
        tone_norm = tone_map.get(tone.strip().lower())
        detail_norm = detail_map.get(detail.strip().lower())
        format_norm = format_map.get(format_style.strip().lower())
        if not tone_norm or not detail_norm or not format_norm:
            return None
        return {"tone": tone_norm, "detail": detail_norm, "format": format_norm}

    def response_variants_count(self) -> int:
        count = 1
        for values in self.RESPONSE_OPTIONS.values():
            count *= len(values)
        return count

    def response_variant(self, index: int) -> dict[str, str] | None:
        count = self.response_variants_count()
        if index < 1 or index > count:
            return None
        idx = index - 1
        settings: dict[str, str] = {}
        for key, values in self.RESPONSE_OPTIONS.items():
            base = len(values)
            settings[key] = values[idx % base]
            idx //= base
        return settings

    def set_response_variant(self, index: int) -> str:
        settings = self.response_variant(index)
        if settings is None:
            return f"Неверный индекс варианта. Допустимо: 1..{self.response_variants_count()}."
        self.state.response_settings = settings
        self._save_state()
        return f"Применён вариант #{index}."

    def search(self, query: str) -> str:
        query_lower = query.lower()
        lines = [f"Результаты поиска по запросу: {query}"]
        matches = 0

        for index, task in enumerate(self.state.tasks, start=1):
            if query_lower in task.title.lower():
                lines.append(f"Задача {index}: {task.title}")
                matches += 1

        for index, note in enumerate(self.state.notes, start=1):
            haystack = f"{note.title} {note.body}".lower()
            if query_lower in haystack:
                lines.append(f"Заметка {index}: {note.title}")
                matches += 1

        for index, habit in enumerate(self.state.habits, start=1):
            if query_lower in habit.get("title", "").lower():
                lines.append(f"Привычка {index}: {habit.get('title')}")
                matches += 1

        for index, item in enumerate(self.state.shopping, start=1):
            if query_lower in item.get("title", "").lower():
                lines.append(f"Покупка {index}: {item.get('title')}")
                matches += 1

        for index, reminder in enumerate(self.state.reminders, start=1):
            if query_lower in reminder.get("title", "").lower():
                lines.append(f"Напоминание {index}: {reminder.get('title')}")
                matches += 1

        if matches == 0:
            return "Ничего не найдено."
        return "\n".join(lines)

    def smart_answer(self, question: str) -> str:
        if not question.strip():
            return "Уточните вопрос."
        lower = question.lower()
        for intent in self.INTENT_RESPONSES:
            if any(keyword in lower for keyword in intent["keywords"]):
                return intent["response"]
        return "Не могу надёжно определить ответ. I don't have reliable information on this."

    def stats(self) -> str:
        total_tasks = len(self.state.tasks)
        done_tasks = sum(1 for task in self.state.tasks if task.done)
        habits = len(self.state.habits)
        notes = len(self.state.notes)
        shopping = len(self.state.shopping)
        reminders = len(self.state.reminders)
        templates = len(self.state.quick_answers)
        today = self._today()
        overdue = sum(
            1
            for task in self.state.tasks
            if task.due_date and not task.done and task.due_date < today
        )
        lines = [
            "Сводка:",
            f"- Задачи: {total_tasks} (выполнено {done_tasks})",
            f"- Просрочено: {overdue}",
            f"- Привычки: {habits}",
            f"- Заметки: {notes}",
            f"- Покупки: {shopping}",
            f"- Напоминания: {reminders}",
            f"- Шаблоны: {templates}",
        ]
        return "\n".join(lines)

    def agenda(self) -> str:
        today = self._today()
        overdue = []
        upcoming = []
        for index, task in enumerate(self.state.tasks, start=1):
            if task.done or not task.due_date:
                continue
            if task.due_date < today:
                overdue.append(f"{index}. {task.title} (срок {task.due_date})")
            elif task.due_date == today:
                upcoming.append(f"{index}. {task.title} (сегодня)")
        if not overdue and not upcoming:
            return "Срочных задач нет."
        lines = ["Актуальные задачи:"]
        if overdue:
            lines.append("Просроченные:")
            lines.extend(f"- {item}" for item in overdue)
        if upcoming:
            lines.append("На сегодня:")
            lines.extend(f"- {item}" for item in upcoming)
        return "\n".join(lines)

    def export_state(self, path: Path) -> str:
        path.write_text(
            json.dumps(self.state.to_dict(), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return f"Экспортировано в {path}"

    def import_state(self, path: Path) -> str:
        if not path.exists():
            return "Файл не найден."
        payload = json.loads(path.read_text(encoding="utf-8"))
        self.state = AssistantState.from_dict(payload)
        self._save_state()
        return f"Импортировано из {path}"


class ThinkingToolkit:
    @staticmethod
    def variations(topic: str) -> str:
        sections = [
            ("Идеи", ThinkingToolkit.ideate(topic)),
            ("Ограничения", ThinkingToolkit.constraints(topic)),
            ("Смена точки зрения", ThinkingToolkit.perspective(topic)),
            ("Обратное мышление", ThinkingToolkit.invert(topic)),
            ("Лестница контекста", ThinkingToolkit.ladder(topic)),
            ("Случайные триггеры", ThinkingToolkit.randomize(topic)),
            ("Последствия", ThinkingToolkit.second_order(topic)),
            ("Компромиссы", ThinkingToolkit.tradeoff(topic)),
        ]
        lines = ["Панорама вариантов:"]
        for title, block in sections:
            lines.append(f"\n{title}:")
            lines.append(block)
        return "\n".join(lines)
    @staticmethod
    def ideate(topic: str) -> str:
        prompts = [
            f"Какая самая простая версия решения для «{topic}»?",
            f"Как сделать это быстрее, дешевле или проще для «{topic}»?",
            f"Какой нестандартный ресурс можно использовать для «{topic}»?",
            f"Что бы сделал эксперт в теме «{topic}»?",
            f"Как можно объединить «{topic}» с другой областью?",
            f"Какой маленький эксперимент поможет продвинуть «{topic}» сегодня?",
        ]
        lines = ["Идеи для гибкости мышления:"]
        lines.extend(f"- {item}" for item in prompts)
        return "\n".join(lines)

    @staticmethod
    def reframe(situation: str) -> str:
        lines = [
            "Варианты переформулирования:",
            f"- Это не проблема, а возможность улучшить: {situation}.",
            f"- Сфокусируйся на том, что под контролем: {situation}.",
            f"- Какой урок можно вынести из: {situation}?",
            f"- Как это может быть полезно через месяц: {situation}?",
        ]
        return "\n".join(lines)

    @staticmethod
    def constraints(topic: str) -> str:
        lines = [
            "Идеи с ограничениями:",
            f"- Если есть только 15 минут на «{topic}», что сделать?",
            f"- Если бюджет нулевой, как продвинуть «{topic}»?",
            f"- Что можно вычеркнуть, чтобы упростить «{topic}»?",
            f"- Как бы выглядело решение без технологий для «{topic}»?",
            f"- Если нужно уменьшить шаг в 2 раза, что поменяется в «{topic}»?",
        ]
        return "\n".join(lines)

    @staticmethod
    def perspective(topic: str) -> str:
        lines = [
            "Смена точки зрения:",
            f"- Как смотрит на «{topic}» клиент/пользователь?",
            f"- Как бы поступил новичок в теме «{topic}»?",
            f"- Что бы посоветовал наставник по «{topic}»?",
            f"- Какой самый смелый вариант для «{topic}»?",
            f"- Какое маленькое улучшение принесёт пользу в «{topic}»?",
        ]
        return "\n".join(lines)

    @staticmethod
    def combine(topic: str, domain: str) -> str:
        lines = [
            "Комбинации идей:",
            f"- Какие приёмы из «{domain}» применимы к «{topic}»?",
            f"- Что можно позаимствовать у «{domain}» для «{topic}»?",
            f"- Какая метафора из «{domain}» поможет объяснить «{topic}»?",
            f"- Если бы «{topic}» был проектом в «{domain}», что изменится?",
        ]
        return "\n".join(lines)

    @staticmethod
    def invert(topic: str) -> str:
        lines = [
            "Обратное мышление:",
            f"- Как гарантированно провалить «{topic}»?",
            f"- Что точно ухудшит результат в «{topic}»?",
            f"- Какие действия стоит исключить, чтобы защитить «{topic}»?",
            f"- Если перевернуть цель, что получится в «{topic}»?",
        ]
        return "\n".join(lines)

    @staticmethod
    def ladder(topic: str) -> str:
        lines = [
            "Лестница контекста:",
            f"- Зачем это нужно в «{topic}»? (подняться на уровень выше)",
            f"- Как выглядит следующий шаг для «{topic}»? (уровень ниже)",
            f"- Какая основная цель стоит за «{topic}»?",
            f"- Какие побочные эффекты есть у «{topic}»?",
        ]
        return "\n".join(lines)

    @staticmethod
    def randomize(topic: str) -> str:
        prompts = [
            f"Добавь элемент неожиданности к «{topic}».",
            f"Как бы выглядело «{topic}», если убрать ключевой ресурс?",
            f"Представь «{topic}» как игру: что меняется?",
            f"Какой один необычный объект вдохновит «{topic}»?",
            f"Сделай «{topic}» для аудитории 10+ и 60+: чем отличаются решения?",
        ]
        lines = ["Случайные триггеры:"]
        lines.extend(f"- {item}" for item in prompts)
        return "\n".join(lines)

    @staticmethod
    def scenario(topic: str, count: int) -> str:
        count = min(count, 50)
        lines = [
            "Сценарии событий (шаблоны действий):",
            f"Тема: {topic}",
            f"Сгенерировано: {count} (максимум 50 за один запрос).",
        ]
        for index in range(1, count + 1):
            lines.append(
                f"{index}. Событие: {topic} (вариант {index}) → действие, запасной план, риск."
            )
        return "\n".join(lines)

    @staticmethod
    def premortem(topic: str) -> str:
        lines = [
            "Pre-mortem:",
            f"- Представь, что «{topic}» провалилось. Что пошло не так?",
            f"- Какие 3 наиболее вероятные причины провала в «{topic}»?",
            f"- Какие слабые места нужно укрепить в «{topic}» заранее?",
            f"- Что можно сделать сегодня, чтобы снизить риски «{topic}»?",
        ]
        return "\n".join(lines)

    @staticmethod
    def second_order(topic: str) -> str:
        lines = [
            "Последствия второго порядка:",
            f"- Что изменится сразу после «{topic}»?",
            f"- Что изменится через неделю/месяц после «{topic}»?",
            f"- Какие неожиданные эффекты даст «{topic}»?",
            f"- Что станет сложнее из-за «{topic}»?",
        ]
        return "\n".join(lines)

    @staticmethod
    def tradeoff(topic: str) -> str:
        lines = [
            "Карта компромиссов:",
            f"- Что выигрываем в «{topic}», а что теряем?",
            f"- Где баланс скорость/качество для «{topic}»?",
            f"- Что важнее: цена или эффект в «{topic}»?",
            f"- Какие 2 метрики в конфликте при «{topic}»?",
        ]
        return "\n".join(lines)

    @staticmethod
    def signal(topic: str) -> str:
        lines = [
            "Сигналы и триггеры:",
            f"- Какие ранние признаки успеха у «{topic}»?",
            f"- Какие сигналы укажут на риск в «{topic}»?",
            f"- Какие пороговые значения важны для «{topic}»?",
            f"- Когда нужно остановиться или пересмотреть «{topic}»?",
        ]
        return "\n".join(lines)

    @staticmethod
    def boundary(topic: str) -> str:
        lines = [
            "Границы и условия:",
            f"- Что точно нельзя делать в «{topic}»?",
            f"- Какие обязательные условия для «{topic}»?",
            f"- Где граница качества/сроков в «{topic}»?",
            f"- Какие ресурсы критичны для «{topic}»?",
        ]
        return "\n".join(lines)

    @staticmethod
    def options(topic: str) -> str:
        lines = [
            "Карта вариантов:",
            f"- Минимальный вариант для «{topic}».",
            f"- Оптимальный вариант для «{topic}».",
            f"- Максимальный вариант для «{topic}».",
            f"- Вариант с партнёром для «{topic}».",
            f"- Вариант с автоматизацией для «{topic}».",
        ]
        return "\n".join(lines)

    @staticmethod
    def priority(topic: str) -> str:
        lines = [
            "Приоритеты:",
            f"- Что даёт 80% эффекта в «{topic}»?",
            f"- Что можно отложить в «{topic}» без риска?",
            f"- Какие 3 шага критичны для «{topic}»?",
            f"- Что можно делегировать в «{topic}»?",
        ]
        return "\n".join(lines)

    @staticmethod
    def reverse_plan(topic: str) -> str:
        lines = [
            "План от цели назад:",
            f"- Конечный результат для «{topic}».",
            f"- Что должно быть готово за шаг до результата «{topic}»?",
            f"- Какие ресурсы нужны за два шага до «{topic}»?",
            f"- С чего начать уже сегодня для «{topic}»?",
        ]
        return "\n".join(lines)

    @staticmethod
    def checklist(topic: str) -> str:
        lines = [
            "Чек-лист:",
            f"- Цель «{topic}» сформулирована ясно?",
            f"- Есть план и сроки для «{topic}»?",
            f"- Риски и запасной план для «{topic}» учтены?",
            f"- Показатели успеха для «{topic}» определены?",
        ]
        return "\n".join(lines)


class StrategicToolkit:
    @staticmethod
    def _apply_settings(lines: list[str], settings: dict[str, str]) -> str:
        tone = settings.get("tone", "нейтральный")
        detail = settings.get("detail", "средне")
        format_style = settings.get("format", "список")
        structure = settings.get("structure", "свободная")
        emoji = settings.get("emoji", "нет")
        style = settings.get("style", "лаконичный")

        if detail == "кратко":
            trimmed = [lines[0]]
            for line in lines[1:]:
                if line.startswith("-") or line.endswith(":"):
                    trimmed.append(line)
                if len(trimmed) >= 8:
                    break
            lines = trimmed

        if tone == "деловой":
            lines.insert(1, "Тон: деловой.")
        elif tone == "дружелюбный":
            lines.insert(1, "Тон: дружелюбный.")

        if structure != "свободная":
            lines.insert(2, f"Структура: {structure}.")

        if style != "лаконичный":
            lines.insert(3, f"Стиль: {style}.")

        if format_style == "абзац":
            text = " ".join(line.lstrip("- ").strip() for line in lines)
            return text

        if emoji == "минимум":
            lines = [line.replace("- ", "• ") for line in lines]
        elif emoji == "акцент":
            lines = [line.replace("- ", "✅ ") for line in lines]

        return "\n".join(lines)

    @staticmethod
    def _profile_header(profile: dict[str, str]) -> str:
        if not profile:
            return "Профиль не задан — использую общие допущения."
        role = profile.get("role", "не указан")
        goal = profile.get("goal", "не указана")
        constraints = profile.get("constraints", "не указаны")
        return f"Профиль: роль={role} | цель={goal} | ограничения={constraints}"

    @staticmethod
    def analyze(context: str, profile: dict[str, str], settings: dict[str, str]) -> str:
        lines = [
            "Анализ (программист-бизнесмен):",
            StrategicToolkit._profile_header(profile),
            "Цель:",
            f"- {context}",
            "Ключевые допущения:",
            "- Ценность должна быть измеримой (метрики).",
            "- Решение должно быть технически реализуемым и окупаемым.",
            "Опции:",
            "- Быстрый MVP с ключевой функцией.",
            "- Полноценный релиз с интеграциями.",
            "Риски:",
            "- Низкий спрос.",
            "- Технический долг.",
            "Метрики успеха:",
            "- Пользовательская активация.",
            "- Конверсия в оплату/эффект.",
            "Следующие шаги:",
            "- Сформулировать гипотезы и проверить их.",
            "- Зафиксировать границы бюджета/сроков.",
        ]
        return StrategicToolkit._apply_settings(lines, settings)

    @staticmethod
    def plan(context: str, profile: dict[str, str], settings: dict[str, str]) -> str:
        lines = [
            "План действий:",
            StrategicToolkit._profile_header(profile),
            "Фаза 1 — Исследование:",
            f"- Уточнить цель: {context}",
            "- Собрать требования и ограничения.",
            "Фаза 2 — Проектирование:",
            "- Архитектура и ключевые компоненты.",
            "- Выбор технологий.",
            "Фаза 3 — Реализация:",
            "- MVP, затем улучшения.",
            "Фаза 4 — Запуск и измерение:",
            "- Метрики, обратная связь, итерации.",
        ]
        return StrategicToolkit._apply_settings(lines, settings)

    @staticmethod
    def pitch(context: str, profile: dict[str, str], settings: dict[str, str]) -> str:
        lines = [
            "Питч:",
            StrategicToolkit._profile_header(profile),
            f"Мы решаем проблему: {context}.",
            "Ценность: быстрее, дешевле, понятнее для пользователя.",
            "Монетизация/эффект: измеримые метрики эффективности.",
            "Стратегия: MVP → проверка спроса → масштабирование.",
        ]
        return StrategicToolkit._apply_settings(lines, settings)

    @staticmethod
    def estimate(context: str, settings: dict[str, str]) -> str:
        lines = [
            "Оценка (приблизительно):",
            f"Контекст: {context}",
            "- Объём работ: зависит от требований и интеграций.",
            "- Сроки: короткий цикл для MVP, затем итерации.",
            "- Риски: объём данных, интеграции, UX.",
        ]
        return StrategicToolkit._apply_settings(lines, settings)

    @staticmethod
    def tech(context: str, settings: dict[str, str]) -> str:
        lines = [
            "Технический разбор:",
            f"Задача: {context}",
            "Архитектура:",
            "- Слои: API, бизнес-логика, хранилище.",
            "Данные:",
            "- Сущности, связи, ограничения.",
            "Интеграции:",
            "- Внешние сервисы и API.",
            "Тестирование:",
            "- Unit, интеграционные, e2e.",
        ]
        return StrategicToolkit._apply_settings(lines, settings)


class AssistantCLI:
    def __init__(self, storage_path: Path) -> None:
        self.bot = SmartAssistant(storage_path)
        self.handlers: dict[str, Callable[[list[str]], str]] = {
            "help": self.handle_help,
            "add-task": self.handle_add_task,
            "list-tasks": self.handle_list_tasks,
            "done": self.handle_done,
            "remove-task": self.handle_remove_task,
            "clear-done": self.handle_clear_done,
            "add-note": self.handle_add_note,
            "list-notes": self.handle_list_notes,
            "remove-note": self.handle_remove_note,
            "add-habit": self.handle_add_habit,
            "list-habits": self.handle_list_habits,
            "habit-done": self.handle_habit_done,
            "add-buy": self.handle_add_buy,
            "list-buys": self.handle_list_buys,
            "buy": self.handle_buy,
            "remind": self.handle_remind,
            "list-reminders": self.handle_list_reminders,
            "remind-done": self.handle_remind_done,
            "add-template": self.handle_add_template,
            "template": self.handle_template,
            "search": self.handle_search,
            "stats": self.handle_stats,
            "export": self.handle_export,
            "import": self.handle_import,
            "set-priority": self.handle_set_priority,
            "set-due": self.handle_set_due,
            "agenda": self.handle_agenda,
            "ideate": self.handle_ideate,
            "reframe": self.handle_reframe,
            "constraints": self.handle_constraints,
            "perspective": self.handle_perspective,
            "combine": self.handle_combine,
            "invert": self.handle_invert,
            "ladder": self.handle_ladder,
            "randomize": self.handle_randomize,
            "scenario": self.handle_scenario,
            "premortem": self.handle_premortem,
            "second-order": self.handle_second_order,
            "tradeoff": self.handle_tradeoff,
            "signal": self.handle_signal,
            "boundary": self.handle_boundary,
            "options": self.handle_options,
            "priority": self.handle_priority,
            "reverse-plan": self.handle_reverse_plan,
            "checklist": self.handle_checklist,
            "variations": self.handle_variations,
            "analyze": self.handle_analyze,
            "plan": self.handle_plan,
            "pitch": self.handle_pitch,
            "estimate": self.handle_estimate,
            "tech": self.handle_tech,
            "set-profile": self.handle_set_profile,
            "profile": self.handle_profile,
            "set-response": self.handle_set_response,
            "response": self.handle_response,
            "response-variants": self.handle_response_variants,
            "set-response-variant": self.handle_set_response_variant,
            "ask": self.handle_ask,
        }

    @staticmethod
    def parse_command(raw: str) -> tuple[str, list[str]]:
        parts = shlex.split(raw)
        if not parts:
            return "", []
        return parts[0], parts[1:]

    @staticmethod
    def _parse_split_args(raw: str) -> tuple[str, str] | None:
        if "::" not in raw:
            return None
        left, right = [part.strip() for part in raw.split("::", 1)]
        if not left or not right:
            return None
        return left, right

    @staticmethod
    def _parse_split_parts(raw: str, expected: int) -> list[str] | None:
        parts = [part.strip() for part in raw.split("::")]
        if len(parts) != expected or any(not part for part in parts):
            return None
        return parts

    def help_text(self) -> str:
        return (
            "Доступные команды:\n"
            "  help                          - показать справку\n"
            "  add-task <текст>              - добавить задачу\n"
            "  list-tasks                     - показать задачи\n"
            "  done <номер>                   - отметить задачу выполненной\n"
            "  add-note <заголовок> :: <тело> - добавить заметку\n"
            "  list-notes                     - показать заметки\n"
            "  add-habit <название> :: <частота> - добавить привычку\n"
            "  list-habits                    - показать привычки\n"
            "  habit-done <номер>             - отметить привычку\n"
            "  add-buy <название>             - добавить покупку\n"
            "  list-buys                      - показать покупки\n"
            "  buy <номер>                    - отметить покупку\n"
            "  remind <текст> :: <минуты>     - напоминание через N минут\n"
            "  list-reminders                 - показать напоминания\n"
            "  remind-done <номер>            - отметить напоминание\n"
            "  add-template <ключ> :: <текст> - сохранить шаблон ответа\n"
            "  template <ключ>                - получить шаблон\n"
            "  ideate <тема>                  - идеи для гибкости мышления\n"
            "  reframe <ситуация>             - переформулировать ситуацию\n"
            "  constraints <тема>             - переосмыслить с ограничениями\n"
            "  perspective <тема>             - смена точки зрения\n"
            "  combine <тема> :: <область>     - объединить области\n"
            "  invert <тема>                  - подумать наоборот\n"
            "  ladder <тема>                  - расширить контекст\n"
            "  randomize <тема>               - случайные триггеры\n"
            "  scenario <тема> :: <N>         - сценарии событий (до 50)\n"
            "  premortem <тема>               - заранее найти сбои\n"
            "  second-order <тема>            - последствия второго порядка\n"
            "  tradeoff <тема>                - карта компромиссов\n"
            "  signal <тема>                  - сигналы и триггеры\n"
            "  boundary <тема>                - границы и условия\n"
            "  options <тема>                 - карта вариантов\n"
            "  priority <тема>                - расстановка приоритетов\n"
            "  reverse-plan <тема>            - план от цели назад\n"
            "  checklist <тема>               - проверочный список\n"
            "  remove-task <номер>            - удалить задачу\n"
            "  clear-done                     - удалить выполненные задачи\n"
            "  remove-note <номер>            - удалить заметку\n"
            "  search <запрос>                - поиск по данным\n"
            "  stats                          - сводка\n"
            "  export <путь>                   - экспорт в файл\n"
            "  import <путь>                   - импорт из файла\n"
            "  set-priority <номер> :: <уровень> - приоритет задачи\n"
            "  set-due <номер> :: <YYYY-MM-DD>   - срок задачи\n"
            "  agenda                         - задачи по срокам\n"
            "  variations <тема>              - панорама вариантов\n"
            "  analyze <контекст>             - анализ решения\n"
            "  plan <контекст>                - план реализации\n"
            "  pitch <контекст>               - краткий питч\n"
            "  estimate <контекст>            - оценка работ\n"
            "  tech <контекст>                - технический разбор\n"
            "  set-profile <роль> :: <цель> :: <ограничения> - профиль\n"
            "  profile                        - показать профиль\n"
            "  set-response <тон> :: <детальность> :: <формат> - ответы\n"
            "  response                       - показать параметры\n"
            "  response-variants              - число вариантов\n"
            "  set-response-variant <номер>   - применить вариант\n"
            "  ask <вопрос>                   - свободный вопрос\n"
            "  exit                          - выйти\n"
        )

    def handle_help(self, args: list[str]) -> str:
        return self.help_text()

    def handle_add_task(self, args: list[str]) -> str:
        if not args:
            return "Укажите текст задачи."
        return self.bot.add_task(" ".join(args))

    def handle_list_tasks(self, args: list[str]) -> str:
        return self.bot.list_tasks()

    def handle_done(self, args: list[str]) -> str:
        if not args or not args[0].isdigit():
            return "Укажите номер задачи."
        return self.bot.complete_task(int(args[0]))

    def handle_remove_task(self, args: list[str]) -> str:
        if not args or not args[0].isdigit():
            return "Укажите номер задачи."
        return self.bot.remove_task(int(args[0]))

    def handle_clear_done(self, args: list[str]) -> str:
        return self.bot.clear_completed_tasks()

    def handle_add_note(self, args: list[str]) -> str:
        raw = " ".join(args)
        parsed = self._parse_split_args(raw)
        if not parsed:
            return "Формат: add-note <заголовок> :: <тело>"
        title, body = parsed
        return self.bot.add_note(title, body)

    def handle_list_notes(self, args: list[str]) -> str:
        return self.bot.list_notes()

    def handle_remove_note(self, args: list[str]) -> str:
        if not args or not args[0].isdigit():
            return "Укажите номер заметки."
        return self.bot.remove_note(int(args[0]))

    def handle_add_habit(self, args: list[str]) -> str:
        raw = " ".join(args)
        parsed = self._parse_split_args(raw)
        if not parsed:
            return "Формат: add-habit <название> :: <частота>"
        title, frequency = parsed
        return self.bot.add_habit(title, frequency)

    def handle_list_habits(self, args: list[str]) -> str:
        return self.bot.list_habits()

    def handle_habit_done(self, args: list[str]) -> str:
        if not args or not args[0].isdigit():
            return "Укажите номер привычки."
        return self.bot.complete_habit(int(args[0]))

    def handle_add_buy(self, args: list[str]) -> str:
        if not args:
            return "Укажите название покупки."
        return self.bot.add_shopping_item(" ".join(args))

    def handle_list_buys(self, args: list[str]) -> str:
        return self.bot.list_shopping()

    def handle_buy(self, args: list[str]) -> str:
        if not args or not args[0].isdigit():
            return "Укажите номер покупки."
        return self.bot.mark_shopping_item(int(args[0]))

    def handle_remind(self, args: list[str]) -> str:
        raw = " ".join(args)
        parsed = self._parse_split_args(raw)
        if not parsed:
            return "Формат: remind <текст> :: <минуты>"
        title, minutes_raw = parsed
        if not minutes_raw.isdigit():
            return "Укажите текст и количество минут."
        return self.bot.add_reminder(title, int(minutes_raw))

    def handle_list_reminders(self, args: list[str]) -> str:
        return self.bot.list_reminders()

    def handle_remind_done(self, args: list[str]) -> str:
        if not args or not args[0].isdigit():
            return "Укажите номер напоминания."
        return self.bot.mark_reminder(int(args[0]))

    def handle_add_template(self, args: list[str]) -> str:
        raw = " ".join(args)
        parsed = self._parse_split_args(raw)
        if not parsed:
            return "Формат: add-template <ключ> :: <текст>"
        key, value = parsed
        return self.bot.add_quick_answer(key, value)

    def handle_template(self, args: list[str]) -> str:
        if not args:
            return "Укажите ключ шаблона."
        return self.bot.get_quick_answer(" ".join(args))

    def handle_search(self, args: list[str]) -> str:
        if not args:
            return "Укажите запрос для поиска."
        return self.bot.search(" ".join(args))

    def handle_stats(self, args: list[str]) -> str:
        return self.bot.stats()

    def handle_export(self, args: list[str]) -> str:
        if not args:
            return "Укажите путь для экспорта."
        return self.bot.export_state(Path(" ".join(args)))

    def handle_import(self, args: list[str]) -> str:
        if not args:
            return "Укажите путь для импорта."
        return self.bot.import_state(Path(" ".join(args)))

    def handle_set_priority(self, args: list[str]) -> str:
        raw = " ".join(args)
        parsed = self._parse_split_args(raw)
        if not parsed:
            return "Формат: set-priority <номер> :: <уровень>"
        index_raw, priority = parsed
        if not index_raw.isdigit():
            return "Укажите номер задачи."
        return self.bot.set_task_priority(int(index_raw), priority)

    def handle_set_due(self, args: list[str]) -> str:
        raw = " ".join(args)
        parsed = self._parse_split_args(raw)
        if not parsed:
            return "Формат: set-due <номер> :: <YYYY-MM-DD>"
        index_raw, due_date = parsed
        if not index_raw.isdigit():
            return "Укажите номер задачи."
        return self.bot.set_task_due_date(int(index_raw), due_date)

    def handle_agenda(self, args: list[str]) -> str:
        return self.bot.agenda()

    def handle_ideate(self, args: list[str]) -> str:
        if not args:
            return "Укажите тему для генерации идей."
        return ThinkingToolkit.ideate(" ".join(args))

    def handle_reframe(self, args: list[str]) -> str:
        if not args:
            return "Опишите ситуацию, которую нужно переформулировать."
        return ThinkingToolkit.reframe(" ".join(args))

    def handle_constraints(self, args: list[str]) -> str:
        if not args:
            return "Укажите тему для переосмысления."
        return ThinkingToolkit.constraints(" ".join(args))

    def handle_perspective(self, args: list[str]) -> str:
        if not args:
            return "Укажите тему для смены точки зрения."
        return ThinkingToolkit.perspective(" ".join(args))

    def handle_combine(self, args: list[str]) -> str:
        raw = " ".join(args)
        parsed = self._parse_split_args(raw)
        if not parsed:
            return "Формат: combine <тема> :: <область>"
        topic, domain = parsed
        return ThinkingToolkit.combine(topic, domain)

    def handle_invert(self, args: list[str]) -> str:
        if not args:
            return "Укажите тему для обратного мышления."
        return ThinkingToolkit.invert(" ".join(args))

    def handle_ladder(self, args: list[str]) -> str:
        if not args:
            return "Укажите тему для расширения контекста."
        return ThinkingToolkit.ladder(" ".join(args))

    def handle_randomize(self, args: list[str]) -> str:
        if not args:
            return "Укажите тему для случайных триггеров."
        return ThinkingToolkit.randomize(" ".join(args))

    def handle_scenario(self, args: list[str]) -> str:
        raw = " ".join(args)
        parsed = self._parse_split_args(raw)
        if not parsed:
            return "Формат: scenario <тема> :: <N>"
        topic, count_raw = parsed
        if not count_raw.isdigit():
            return "Укажите тему и число сценариев."
        return ThinkingToolkit.scenario(topic, int(count_raw))

    def handle_premortem(self, args: list[str]) -> str:
        if not args:
            return "Укажите тему для pre-mortem."
        return ThinkingToolkit.premortem(" ".join(args))

    def handle_second_order(self, args: list[str]) -> str:
        if not args:
            return "Укажите тему для анализа последствий."
        return ThinkingToolkit.second_order(" ".join(args))

    def handle_tradeoff(self, args: list[str]) -> str:
        if not args:
            return "Укажите тему для карты компромиссов."
        return ThinkingToolkit.tradeoff(" ".join(args))

    def handle_signal(self, args: list[str]) -> str:
        if not args:
            return "Укажите тему для сигналов."
        return ThinkingToolkit.signal(" ".join(args))

    def handle_boundary(self, args: list[str]) -> str:
        if not args:
            return "Укажите тему для определения границ."
        return ThinkingToolkit.boundary(" ".join(args))

    def handle_options(self, args: list[str]) -> str:
        if not args:
            return "Укажите тему для карты вариантов."
        return ThinkingToolkit.options(" ".join(args))

    def handle_priority(self, args: list[str]) -> str:
        if not args:
            return "Укажите тему для приоритизации."
        return ThinkingToolkit.priority(" ".join(args))

    def handle_reverse_plan(self, args: list[str]) -> str:
        if not args:
            return "Укажите тему для обратного планирования."
        return ThinkingToolkit.reverse_plan(" ".join(args))

    def handle_checklist(self, args: list[str]) -> str:
        if not args:
            return "Укажите тему для чек-листа."
        return ThinkingToolkit.checklist(" ".join(args))

    def handle_variations(self, args: list[str]) -> str:
        if not args:
            return "Укажите тему для вариативности."
        return ThinkingToolkit.variations(" ".join(args))

    def handle_analyze(self, args: list[str]) -> str:
        if not args:
            return "Укажите контекст для анализа."
        return StrategicToolkit.analyze(
            " ".join(args), self.bot.state.profile, self.bot.get_response_settings()
        )

    def handle_plan(self, args: list[str]) -> str:
        if not args:
            return "Укажите контекст для плана."
        return StrategicToolkit.plan(
            " ".join(args), self.bot.state.profile, self.bot.get_response_settings()
        )

    def handle_pitch(self, args: list[str]) -> str:
        if not args:
            return "Укажите контекст для питча."
        return StrategicToolkit.pitch(
            " ".join(args), self.bot.state.profile, self.bot.get_response_settings()
        )

    def handle_estimate(self, args: list[str]) -> str:
        if not args:
            return "Укажите контекст для оценки."
        return StrategicToolkit.estimate(
            " ".join(args), self.bot.get_response_settings()
        )

    def handle_tech(self, args: list[str]) -> str:
        if not args:
            return "Укажите контекст для технического разбора."
        return StrategicToolkit.tech(" ".join(args), self.bot.get_response_settings())

    def handle_set_profile(self, args: list[str]) -> str:
        raw = " ".join(args)
        parts = self._parse_split_parts(raw, 3)
        if not parts:
            return "Формат: set-profile <роль> :: <цель> :: <ограничения>"
        role, goal, constraints = parts
        return self.bot.set_profile(role, goal, constraints)

    def handle_profile(self, args: list[str]) -> str:
        return self.bot.get_profile()

    def handle_set_response(self, args: list[str]) -> str:
        raw = " ".join(args)
        parts = self._parse_split_parts(raw, 3)
        if not parts:
            return "Формат: set-response <тон> :: <детальность> :: <формат>"
        tone, detail, format_style = parts
        return self.bot.set_response_settings(tone, detail, format_style)

    def handle_response(self, args: list[str]) -> str:
        settings = self.bot.get_response_settings()
        return (
            "Параметры ответов:\n"
            f"- Тон: {settings['tone']}\n"
            f"- Детальность: {settings['detail']}\n"
            f"- Формат: {settings['format']}"
        )

    def handle_response_variants(self, args: list[str]) -> str:
        count = self.bot.response_variants_count()
        return f"Доступно вариантов: {count}."

    def handle_set_response_variant(self, args: list[str]) -> str:
        if not args or not args[0].isdigit():
            return "Укажите номер варианта."
        return self.bot.set_response_variant(int(args[0]))

    def handle_ask(self, args: list[str]) -> str:
        if not args:
            return "Уточните вопрос."
        return self.bot.smart_answer(" ".join(args))

    def run(self) -> None:
        print("Личный умный помощник. Введите help для списка команд.")
        while True:
            try:
                raw = input("> ").strip()
            except (EOFError, KeyboardInterrupt):
                print("\nДо встречи!")
                break
            if not raw:
                continue
            if raw in {"exit", "quit"}:
                print("До встречи!")
                break
            command, args = self.parse_command(raw)
            handler = self.handlers.get(command)
            if handler:
                print(handler(args))
            else:
                interpreted = self.bot.interpret_message(raw)
                if interpreted:
                    print(interpreted)
                else:
                    print(self.bot.smart_answer(raw))


def run_cli(storage_path: Path) -> None:
    cli = AssistantCLI(storage_path)
    cli.run()


if __name__ == "__main__":
    data_path = Path(__file__).with_name("assistant_state.db")
    run_cli(data_path)
