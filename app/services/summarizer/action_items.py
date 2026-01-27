from __future__ import annotations

import re

ACTION_VERBS = [
    "сделать",
    "позвонить",
    "отправить",
    "проверить",
    "создать",
    "встретиться",
    "добавить",
]


def extract_action_items(text: str) -> list[str]:
    sentences = re.split(r"(?<=[.!?])\s+", text.strip())
    items: list[str] = []
    for sentence in sentences:
        lower = sentence.lower()
        if any(verb in lower for verb in ACTION_VERBS):
            items.append(sentence.strip())
    return items
