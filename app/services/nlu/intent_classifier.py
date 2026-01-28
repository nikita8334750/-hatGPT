from __future__ import annotations

from dataclasses import dataclass


@dataclass
class IntentScore:
    intent: str
    score: float


class IntentClassifier:
    def __init__(self) -> None:
        self.rules: dict[str, list[tuple[list[str], float]]] = {
            "create_task": [
                (["напомни", "поставь", "создай", "сделай", "добавь задачу"], 0.6),
                (["надо", "нужно"], 0.4),
            ],
            "list_tasks": [(["что у меня", "список задач", "мои задачи"], 0.7)],
            "complete_task": [(["сделано", "готово", "выполнил"], 0.7)],
            "delete_task": [(["удали", "убери", "удалить"], 0.6)],
            "postpone_task": [(["перенеси", "позже", "отложи"], 0.6)],
            "set_settings": [(["настройки", "тихий режим", "dnd", "часовой пояс"], 0.6)],
            "create_note": [(["заметка", "запиши"], 0.6)],
            "search": [(["найди", "поиск", "искать"], 0.6)],
            "summarize": [(["суммаризируй", "резюме", "кратко"], 0.6)],
            "plan_day": [(["план на сегодня", "что сегодня"], 0.7)],
        }

    def classify(self, text: str) -> list[IntentScore]:
        normalized = text.lower()
        results: list[IntentScore] = []
        for intent, patterns in self.rules.items():
            score = 0.0
            for keywords, weight in patterns:
                if any(word in normalized for word in keywords):
                    score += weight
            if score > 0:
                results.append(IntentScore(intent=intent, score=score))
        results.sort(key=lambda item: item.score, reverse=True)
        return results
