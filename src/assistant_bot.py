"""Personal smart assistant bot (CLI)."""

from __future__ import annotations

import json
import shlex
from dataclasses import dataclass, field
from datetime import datetime, timedelta
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

    def to_dict(self) -> dict:
        return {
            "tasks": [task.__dict__ for task in self.tasks],
            "notes": [note.__dict__ for note in self.notes],
            "habits": self.habits,
            "shopping": self.shopping,
            "reminders": self.reminders,
            "quick_answers": self.quick_answers,
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
        )


class SmartAssistant:
    def __init__(self, storage_path: Path) -> None:
        self.storage_path = storage_path
        self.state = self._load_state()

    def _load_state(self) -> AssistantState:
        if not self.storage_path.exists():
            return AssistantState()
        payload = json.loads(self.storage_path.read_text(encoding="utf-8"))
        return AssistantState.from_dict(payload)

    def _save_state(self) -> None:
        self.storage_path.write_text(
            json.dumps(self.state.to_dict(), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

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
        reminder = {
            "title": title,
            "remind_at": remind_at.strftime(DATE_FMT),
            "created_at": self._now(),
            "done": False,
        }
        self.state.reminders.append(reminder)
        self._save_state()
        return f"Напоминание установлено на {reminder['remind_at']}"

    def list_reminders(self) -> str:
        if not self.state.reminders:
            return "Напоминаний пока нет."
        lines = ["Напоминания:"]
        for index, reminder in enumerate(self.state.reminders, start=1):
            status = "✅" if reminder.get("done") else "⏰"
            lines.append(
                f"{index}. {status} {reminder['title']} (к {reminder['remind_at']})"
            )
        return "\n".join(lines)

    def mark_reminder(self, index: int) -> str:
        if index < 1 or index > len(self.state.reminders):
            return "Неверный номер напоминания."
        self.state.reminders[index - 1]["done"] = True
        self._save_state()
        return "Напоминание отмечено."

    def add_quick_answer(self, key: str, value: str) -> str:
        self.state.quick_answers[key] = value
        self._save_state()
        return f"Шаблон ответа сохранён: {key}"

    def get_quick_answer(self, key: str) -> str:
        answer = self.state.quick_answers.get(key)
        if not answer:
            return "Шаблон не найден."
        return answer

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
                print("Неизвестная команда. Введите help.")


def run_cli(storage_path: Path) -> None:
    cli = AssistantCLI(storage_path)
    cli.run()


if __name__ == "__main__":
    data_path = Path(__file__).with_name("assistant_state.json")
    run_cli(data_path)
