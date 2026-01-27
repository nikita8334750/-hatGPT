"""Telegram integration for the personal assistant."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Callable

from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from assistant_bot import AssistantCLI, SmartAssistant


class TelegramAssistant:
    def __init__(self, storage_path: Path) -> None:
        self.cli = AssistantCLI(storage_path)
        self.bot = self.cli.bot

    def _split_command(self, text: str) -> tuple[str, str]:
        if not text:
            return "", ""
        if text.startswith("/"):
            text = text[1:]
        if " " in text:
            command, rest = text.split(" ", 1)
            return command, rest.strip()
        return text, ""

    def handle_text(self, text: str) -> str:
        command, rest = self._split_command(text)
        if not command:
            return "Введите команду. Пример: /help"
        handler = TELEGRAM_COMMANDS.get(command)
        if not handler:
            return self.bot.smart_answer(text)
        return handler(self, rest)


def cmd_help(assistant: TelegramAssistant, rest: str) -> str:
    return assistant.cli.handle_help([])


def cmd_add_task(assistant: TelegramAssistant, rest: str) -> str:
    return assistant.bot.add_task(rest) if rest else "Укажите текст задачи."


def cmd_list_tasks(assistant: TelegramAssistant, rest: str) -> str:
    return assistant.bot.list_tasks()


def cmd_done(assistant: TelegramAssistant, rest: str) -> str:
    if not rest.isdigit():
        return "Укажите номер задачи."
    return assistant.bot.complete_task(int(rest))


def cmd_remove_task(assistant: TelegramAssistant, rest: str) -> str:
    if not rest.isdigit():
        return "Укажите номер задачи."
    return assistant.bot.remove_task(int(rest))


def cmd_clear_done(assistant: TelegramAssistant, rest: str) -> str:
    return assistant.bot.clear_completed_tasks()


def cmd_add_note(assistant: TelegramAssistant, rest: str) -> str:
    if "::" not in rest:
        return "Формат: /add_note <заголовок> :: <тело>"
    title, body = [part.strip() for part in rest.split("::", 1)]
    if not title or not body:
        return "Заполните и заголовок, и тело заметки."
    return assistant.bot.add_note(title, body)


def cmd_list_notes(assistant: TelegramAssistant, rest: str) -> str:
    return assistant.bot.list_notes()


def cmd_remove_note(assistant: TelegramAssistant, rest: str) -> str:
    if not rest.isdigit():
        return "Укажите номер заметки."
    return assistant.bot.remove_note(int(rest))


def cmd_search(assistant: TelegramAssistant, rest: str) -> str:
    return assistant.bot.search(rest) if rest else "Укажите запрос для поиска."


def cmd_stats(assistant: TelegramAssistant, rest: str) -> str:
    return assistant.bot.stats()


def cmd_agenda(assistant: TelegramAssistant, rest: str) -> str:
    return assistant.bot.agenda()


def cmd_set_priority(assistant: TelegramAssistant, rest: str) -> str:
    if "::" not in rest:
        return "Формат: /set_priority <номер> :: <уровень>"
    index_raw, priority = [part.strip() for part in rest.split("::", 1)]
    if not index_raw.isdigit():
        return "Укажите номер задачи."
    return assistant.bot.set_task_priority(int(index_raw), priority)


def cmd_set_due(assistant: TelegramAssistant, rest: str) -> str:
    if "::" not in rest:
        return "Формат: /set_due <номер> :: <YYYY-MM-DD>"
    index_raw, due_date = [part.strip() for part in rest.split("::", 1)]
    if not index_raw.isdigit():
        return "Укажите номер задачи."
    return assistant.bot.set_task_due_date(int(index_raw), due_date)


def cmd_variations(assistant: TelegramAssistant, rest: str) -> str:
    if not rest:
        return "Укажите тему для вариативности."
    return assistant.cli.handle_variations([rest])


def cmd_analyze(assistant: TelegramAssistant, rest: str) -> str:
    if not rest:
        return "Укажите контекст для анализа."
    return assistant.cli.handle_analyze([rest])


def cmd_plan(assistant: TelegramAssistant, rest: str) -> str:
    if not rest:
        return "Укажите контекст для плана."
    return assistant.cli.handle_plan([rest])


def cmd_pitch(assistant: TelegramAssistant, rest: str) -> str:
    if not rest:
        return "Укажите контекст для питча."
    return assistant.cli.handle_pitch([rest])


def cmd_estimate(assistant: TelegramAssistant, rest: str) -> str:
    if not rest:
        return "Укажите контекст для оценки."
    return assistant.cli.handle_estimate([rest])


def cmd_tech(assistant: TelegramAssistant, rest: str) -> str:
    if not rest:
        return "Укажите контекст для технического разбора."
    return assistant.cli.handle_tech([rest])


def cmd_set_profile(assistant: TelegramAssistant, rest: str) -> str:
    if "::" not in rest:
        return "Формат: /set_profile <роль> :: <цель> :: <ограничения>"
    parts = [part.strip() for part in rest.split("::")]
    if len(parts) != 3 or any(not part for part in parts):
        return "Формат: /set_profile <роль> :: <цель> :: <ограничения>"
    return assistant.bot.set_profile(parts[0], parts[1], parts[2])


def cmd_profile(assistant: TelegramAssistant, rest: str) -> str:
    return assistant.bot.get_profile()


def cmd_set_response(assistant: TelegramAssistant, rest: str) -> str:
    if "::" not in rest:
        return "Формат: /set_response <тон> :: <детальность> :: <формат>"
    parts = [part.strip() for part in rest.split("::")]
    if len(parts) != 3 or any(not part for part in parts):
        return "Формат: /set_response <тон> :: <детальность> :: <формат>"
    return assistant.bot.set_response_settings(parts[0], parts[1], parts[2])


def cmd_response(assistant: TelegramAssistant, rest: str) -> str:
    settings = assistant.bot.get_response_settings()
    return (
        "Параметры ответов:\n"
        f"- Тон: {settings['tone']}\n"
        f"- Детальность: {settings['detail']}\n"
        f"- Формат: {settings['format']}"
    )


def cmd_response_variants(assistant: TelegramAssistant, rest: str) -> str:
    return f"Доступно вариантов: {assistant.bot.response_variants_count()}."


def cmd_set_response_variant(assistant: TelegramAssistant, rest: str) -> str:
    if not rest.isdigit():
        return "Укажите номер варианта."
    return assistant.bot.set_response_variant(int(rest))


def cmd_ask(assistant: TelegramAssistant, rest: str) -> str:
    if not rest:
        return "Уточните вопрос."
    return assistant.bot.smart_answer(rest)


TELEGRAM_COMMANDS: dict[str, Callable[[TelegramAssistant, str], str]] = {
    "help": cmd_help,
    "add_task": cmd_add_task,
    "tasks": cmd_list_tasks,
    "done": cmd_done,
    "remove_task": cmd_remove_task,
    "clear_done": cmd_clear_done,
    "add_note": cmd_add_note,
    "notes": cmd_list_notes,
    "remove_note": cmd_remove_note,
    "search": cmd_search,
    "stats": cmd_stats,
    "agenda": cmd_agenda,
    "set_priority": cmd_set_priority,
    "set_due": cmd_set_due,
    "variations": cmd_variations,
    "analyze": cmd_analyze,
    "plan": cmd_plan,
    "pitch": cmd_pitch,
    "estimate": cmd_estimate,
    "tech": cmd_tech,
    "set_profile": cmd_set_profile,
    "profile": cmd_profile,
    "set_response": cmd_set_response,
    "response": cmd_response,
    "response_variants": cmd_response_variants,
    "set_response_variant": cmd_set_response_variant,
    "ask": cmd_ask,
}


async def on_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    assistant: TelegramAssistant = context.application.bot_data["assistant"]
    text = update.message.text if update.message else ""
    response = assistant.handle_text(text)
    await update.message.reply_text(response)


def main() -> None:
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        raise RuntimeError("TELEGRAM_BOT_TOKEN не задан")
    storage_path = Path(__file__).with_name("assistant_state.json")
    assistant = TelegramAssistant(storage_path)

    app = Application.builder().token(token).build()
    app.bot_data["assistant"] = assistant

    app.add_handler(CommandHandler("help", on_message))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, on_message))
    app.add_handler(MessageHandler(filters.COMMAND, on_message))

    app.run_polling()


if __name__ == "__main__":
    main()
