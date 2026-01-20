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

    def add_task(self, title: str) -> str:
        task = Task(title=title, created_at=self._now())
        self.state.tasks.append(task)
        self._save_state()
        return f"Задача добавлена: {title}"

    def list_tasks(self) -> str:
        if not self.state.tasks:
            return "Список задач пуст."
        lines = ["Задачи:"]
        for index, task in enumerate(self.state.tasks, start=1):
            status = "✅" if task.done else "🟡"
            lines.append(f"{index}. {status} {task.title} (создано {task.created_at})")
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
            "  exit                          - выйти\n"
        )


def parse_command(raw: str) -> tuple[str, list[str]]:
    parts = shlex.split(raw)
    if not parts:
        return "", []
    return parts[0], parts[1:]


CommandHandler = Callable[[SmartAssistant, list[str]], str]


def handle_add_task(bot: SmartAssistant, args: list[str]) -> str:
    if not args:
        return "Укажите текст задачи."
    return bot.add_task(" ".join(args))


def handle_list_tasks(bot: SmartAssistant, args: list[str]) -> str:
    return bot.list_tasks()


def handle_done(bot: SmartAssistant, args: list[str]) -> str:
    if not args or not args[0].isdigit():
        return "Укажите номер задачи."
    return bot.complete_task(int(args[0]))


def handle_add_note(bot: SmartAssistant, args: list[str]) -> str:
    raw = " ".join(args)
    if "::" not in raw:
        return "Формат: add-note <заголовок> :: <тело>"
    title, body = [part.strip() for part in raw.split("::", 1)]
    if not title or not body:
        return "Заполните и заголовок, и тело заметки."
    return bot.add_note(title, body)


def handle_list_notes(bot: SmartAssistant, args: list[str]) -> str:
    return bot.list_notes()


def handle_add_habit(bot: SmartAssistant, args: list[str]) -> str:
    raw = " ".join(args)
    if "::" not in raw:
        return "Формат: add-habit <название> :: <частота>"
    title, frequency = [part.strip() for part in raw.split("::", 1)]
    if not title or not frequency:
        return "Заполните и название, и частоту."
    return bot.add_habit(title, frequency)


def handle_list_habits(bot: SmartAssistant, args: list[str]) -> str:
    return bot.list_habits()


def handle_habit_done(bot: SmartAssistant, args: list[str]) -> str:
    if not args or not args[0].isdigit():
        return "Укажите номер привычки."
    return bot.complete_habit(int(args[0]))


def handle_add_buy(bot: SmartAssistant, args: list[str]) -> str:
    if not args:
        return "Укажите название покупки."
    return bot.add_shopping_item(" ".join(args))


def handle_list_buys(bot: SmartAssistant, args: list[str]) -> str:
    return bot.list_shopping()


def handle_buy(bot: SmartAssistant, args: list[str]) -> str:
    if not args or not args[0].isdigit():
        return "Укажите номер покупки."
    return bot.mark_shopping_item(int(args[0]))


def handle_remind(bot: SmartAssistant, args: list[str]) -> str:
    raw = " ".join(args)
    if "::" not in raw:
        return "Формат: remind <текст> :: <минуты>"
    title, minutes_raw = [part.strip() for part in raw.split("::", 1)]
    if not title or not minutes_raw.isdigit():
        return "Укажите текст и количество минут."
    return bot.add_reminder(title, int(minutes_raw))


def handle_list_reminders(bot: SmartAssistant, args: list[str]) -> str:
    return bot.list_reminders()


def handle_remind_done(bot: SmartAssistant, args: list[str]) -> str:
    if not args or not args[0].isdigit():
        return "Укажите номер напоминания."
    return bot.mark_reminder(int(args[0]))


def handle_add_template(bot: SmartAssistant, args: list[str]) -> str:
    raw = " ".join(args)
    if "::" not in raw:
        return "Формат: add-template <ключ> :: <текст>"
    key, value = [part.strip() for part in raw.split("::", 1)]
    if not key or not value:
        return "Укажите ключ и текст шаблона."
    return bot.add_quick_answer(key, value)


def handle_template(bot: SmartAssistant, args: list[str]) -> str:
    if not args:
        return "Укажите ключ шаблона."
    return bot.get_quick_answer(" ".join(args))


def handle_ideate(bot: SmartAssistant, args: list[str]) -> str:
    if not args:
        return "Укажите тему для генерации идей."
    topic = " ".join(args)
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


def handle_reframe(bot: SmartAssistant, args: list[str]) -> str:
    if not args:
        return "Опишите ситуацию, которую нужно переформулировать."
    situation = " ".join(args)
    lines = [
        "Варианты переформулирования:",
        f"- Это не проблема, а возможность улучшить: {situation}.",
        f"- Сфокусируйся на том, что под контролем: {situation}.",
        f"- Какой урок можно вынести из: {situation}?",
        f"- Как это может быть полезно через месяц: {situation}?",
    ]
    return "\n".join(lines)


def handle_constraints(bot: SmartAssistant, args: list[str]) -> str:
    if not args:
        return "Укажите тему для переосмысления."
    topic = " ".join(args)
    lines = [
        "Идеи с ограничениями:",
        f"- Если есть только 15 минут на «{topic}», что сделать?",
        f"- Если бюджет нулевой, как продвинуть «{topic}»?",
        f"- Что можно вычеркнуть, чтобы упростить «{topic}»?",
        f"- Как бы выглядело решение без технологий для «{topic}»?",
        f"- Если нужно уменьшить шаг в 2 раза, что поменяется в «{topic}»?",
    ]
    return "\n".join(lines)


def handle_perspective(bot: SmartAssistant, args: list[str]) -> str:
    if not args:
        return "Укажите тему для смены точки зрения."
    topic = " ".join(args)
    lines = [
        "Смена точки зрения:",
        f"- Как смотрит на «{topic}» клиент/пользователь?",
        f"- Как бы поступил новичок в теме «{topic}»?",
        f"- Что бы посоветовал наставник по «{topic}»?",
        f"- Какой самый смелый вариант для «{topic}»?",
        f"- Какое маленькое улучшение принесёт пользу в «{topic}»?",
    ]
    return "\n".join(lines)


def handle_combine(bot: SmartAssistant, args: list[str]) -> str:
    raw = " ".join(args)
    if "::" not in raw:
        return "Формат: combine <тема> :: <область>"
    topic, domain = [part.strip() for part in raw.split("::", 1)]
    if not topic or not domain:
        return "Укажите тему и область для объединения."
    lines = [
        "Комбинации идей:",
        f"- Какие приёмы из «{domain}» применимы к «{topic}»?",
        f"- Что можно позаимствовать у «{domain}» для «{topic}»?",
        f"- Какая метафора из «{domain}» поможет объяснить «{topic}»?",
        f"- Если бы «{topic}» был проектом в «{domain}», что изменится?",
    ]
    return "\n".join(lines)


def handle_invert(bot: SmartAssistant, args: list[str]) -> str:
    if not args:
        return "Укажите тему для обратного мышления."
    topic = " ".join(args)
    lines = [
        "Обратное мышление:",
        f"- Как гарантированно провалить «{topic}»?",
        f"- Что точно ухудшит результат в «{topic}»?",
        f"- Какие действия стоит исключить, чтобы защитить «{topic}»?",
        f"- Если перевернуть цель, что получится в «{topic}»?",
    ]
    return "\n".join(lines)


def handle_ladder(bot: SmartAssistant, args: list[str]) -> str:
    if not args:
        return "Укажите тему для расширения контекста."
    topic = " ".join(args)
    lines = [
        "Лестница контекста:",
        f"- Зачем это нужно в «{topic}»? (подняться на уровень выше)",
        f"- Как выглядит следующий шаг для «{topic}»? (уровень ниже)",
        f"- Какая основная цель стоит за «{topic}»?",
        f"- Какие побочные эффекты есть у «{topic}»?",
    ]
    return "\n".join(lines)


def handle_randomize(bot: SmartAssistant, args: list[str]) -> str:
    if not args:
        return "Укажите тему для случайных триггеров."
    topic = " ".join(args)
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


def handle_scenario(bot: SmartAssistant, args: list[str]) -> str:
    raw = " ".join(args)
    if "::" not in raw:
        return "Формат: scenario <тема> :: <N>"
    topic, count_raw = [part.strip() for part in raw.split("::", 1)]
    if not topic or not count_raw.isdigit():
        return "Укажите тему и число сценариев."
    count = min(int(count_raw), 50)
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


def handle_premortem(bot: SmartAssistant, args: list[str]) -> str:
    if not args:
        return "Укажите тему для pre-mortem."
    topic = " ".join(args)
    lines = [
        "Pre-mortem:",
        f"- Представь, что «{topic}» провалилось. Что пошло не так?",
        f"- Какие 3 наиболее вероятные причины провала в «{topic}»?",
        f"- Какие слабые места нужно укрепить в «{topic}» заранее?",
        f"- Что можно сделать сегодня, чтобы снизить риски «{topic}»?",
    ]
    return "\n".join(lines)


def handle_second_order(bot: SmartAssistant, args: list[str]) -> str:
    if not args:
        return "Укажите тему для анализа последствий."
    topic = " ".join(args)
    lines = [
        "Последствия второго порядка:",
        f"- Что изменится сразу после «{topic}»?",
        f"- Что изменится через неделю/месяц после «{topic}»?",
        f"- Какие неожиданные эффекты даст «{topic}»?",
        f"- Что станет сложнее из-за «{topic}»?",
    ]
    return "\n".join(lines)


def handle_tradeoff(bot: SmartAssistant, args: list[str]) -> str:
    if not args:
        return "Укажите тему для карты компромиссов."
    topic = " ".join(args)
    lines = [
        "Карта компромиссов:",
        f"- Что выигрываем в «{topic}», а что теряем?",
        f"- Где баланс скорость/качество для «{topic}»?",
        f"- Что важнее: цена или эффект в «{topic}»?",
        f"- Какие 2 метрики в конфликте при «{topic}»?",
    ]
    return "\n".join(lines)


def handle_signal(bot: SmartAssistant, args: list[str]) -> str:
    if not args:
        return "Укажите тему для сигналов."
    topic = " ".join(args)
    lines = [
        "Сигналы и триггеры:",
        f"- Какие ранние признаки успеха у «{topic}»?",
        f"- Какие сигналы укажут на риск в «{topic}»?",
        f"- Какие пороговые значения важны для «{topic}»?",
        f"- Когда нужно остановиться или пересмотреть «{topic}»?",
    ]
    return "\n".join(lines)


def run_cli(storage_path: Path) -> None:
    bot = SmartAssistant(storage_path)
    handlers: dict[str, CommandHandler] = {
        "help": lambda b, a: b.help_text(),
        "add-task": handle_add_task,
        "list-tasks": handle_list_tasks,
        "done": handle_done,
        "add-note": handle_add_note,
        "list-notes": handle_list_notes,
        "add-habit": handle_add_habit,
        "list-habits": handle_list_habits,
        "habit-done": handle_habit_done,
        "add-buy": handle_add_buy,
        "list-buys": handle_list_buys,
        "buy": handle_buy,
        "remind": handle_remind,
        "list-reminders": handle_list_reminders,
        "remind-done": handle_remind_done,
        "add-template": handle_add_template,
        "template": handle_template,
        "ideate": handle_ideate,
        "reframe": handle_reframe,
        "constraints": handle_constraints,
        "perspective": handle_perspective,
        "combine": handle_combine,
        "invert": handle_invert,
        "ladder": handle_ladder,
        "randomize": handle_randomize,
        "scenario": handle_scenario,
        "premortem": handle_premortem,
        "second-order": handle_second_order,
        "tradeoff": handle_tradeoff,
        "signal": handle_signal,
    }

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
        command, args = parse_command(raw)
        if command in handlers:
            print(handlers[command](bot, args))
        else:
            print("Неизвестная команда. Введите help.")


if __name__ == "__main__":
    data_path = Path(__file__).with_name("assistant_state.json")
    run_cli(data_path)
