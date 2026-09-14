#!/usr/bin/env python3
"""Safe autonomous manager for the ANIMA TACTUS VK community.

The manager never calls destructive VK methods and never stores member or message data.
It uses a community token from the runtime environment.
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
import sys
import textwrap
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


API_VERSION = "5.199"
API_ORIGINS = ("https://api.vk.ru/method", "https://api.vk.com/method")
GROUP_ID_DEFAULT = 240179386
MESSAGE_LINK = "https://vk.me/club240179386"
MESSAGE_LINK_TEXT = "Начать — написать"

CANONICAL_NAME = "ANIMA TACTUS"
CANONICAL_STATUS = "Назвать чувства. Понять состояние. Выбрать следующий шаг."
CANONICAL_DESCRIPTION = (
    "ANIMA TACTUS — спокойное пространство для самонаблюдения. "
    "Здесь можно остановиться после значимой ситуации, назвать свои чувства "
    "без оценок и диагнозов, заметить их интенсивность и выбрать безопасный "
    "следующий шаг. В сообществе — практические материалы, новости приложения "
    "и авторских программ. Чтобы начать, нажмите «Написать» и отправьте слово "
    "«СТАРТ». ANIMA TACTUS не является диагностикой, лечением или экстренной помощью."
)
CANONICAL_WELCOME = """Добро пожаловать в ANIMA TACTUS

Это спокойное пространство, где можно остановиться после значимой ситуации, назвать свои чувства без оценок и диагнозов и выбрать безопасный следующий шаг.

Что здесь можно сделать
• понять, что происходит: ситуация → чувства → интенсивность;
• использовать короткие практики самонаблюдения и приватной разгрузки;
• следить за выходом приложения и авторских программ.

Что доступно
• практические материалы сообщества — уже здесь;
• приложение ANIMA TACTUS — готовится к публичному выпуску;
• «Семь встреч с собой» — готовится к выпуску;
• 14-дневная программа с рабочим названием «Точка роста» — в разработке, продажи не открыты.

Как начать
Нажмите «Написать» и отправьте слово «СТАРТ». В сообщениях вы получите навигацию по ближайшему доступному формату.

Важно: ANIMA TACTUS — образовательный инструмент самонаблюдения. Он не ставит диагнозы, не является лечением и не заменяет экстренную или профессиональную помощь. При угрозе жизни или безопасности обратитесь в местную экстренную службу."""

DESTRUCTIVE_METHODS = frozenset({
    "wall.delete",
    "video.delete",
    "photos.delete",
    "board.deleteTopic",
    "market.delete",
    "docs.delete",
    "groups.removeUser",
    "groups.leave",
    "groups.deleteCallbackServer",
})

NAVIGATION_REPLY = """Добро пожаловать в ANIMA TACTUS.

Выберите, что сейчас полезнее:
• «ЧУВСТВА» — спокойно назвать своё состояние;
• «ПАУЗА» — короткая практика перед следующим действием;
• «ПРИЛОЖЕНИЕ» — узнать о запуске приложения;
• «ПРОГРАММЫ» — посмотреть доступные форматы;
• «ЧЕЛОВЕК» — оставить сообщение администратору.

Это образовательный инструмент самонаблюдения, не диагностика и не экстренная помощь."""
FEELINGS_REPLY = """Попробуйте ответить тремя короткими строками:

1. Что произошло — только факты?
2. Какие чувства я замечаю?
3. Насколько сильно каждое чувство сейчас: от 0 до 10?

Не нужно искать «правильный» ответ. Можно написать сюда то, что получилось."""
PAUSE_REPLY = """Короткая пауза:

1. Поставьте обе стопы на опору.
2. Сделайте несколько спокойных выдохов без усилия.
3. Назовите: «Сейчас я чувствую…»
4. Выберите один безопасный шаг на ближайшие 10 минут.

Если есть угроза жизни или безопасности, обратитесь в местную экстренную службу."""
APP_REPLY = """Приложение ANIMA TACTUS готовится к публичному выпуску. Оно поможет пройти путь: ситуация → чувства → интенсивность → безопасный следующий шаг.

Следите за новостями здесь. Когда появится проверенная ссылка на установку, мы опубликуем её в закреплённой навигации."""
PROGRAMS_REPLY = """Сейчас доступны практические материалы сообщества.

Готовятся:
• «Семь встреч с собой»;
• 14-дневная программа с рабочим названием «Точка роста»;
• приложение ANIMA TACTUS.

Продажи пока не открыты. Здесь появятся условия и точные ссылки, когда материалы будут готовы."""
HUMAN_REPLY = """Напишите одним сообщением, что вам нужно. Администратор увидит обращение и ответит, когда будет на связи.

Не отправляйте пароли, данные банковских карт и другие секреты. При угрозе жизни или безопасности обращайтесь в местную экстренную службу."""


class VKError(RuntimeError):
    def __init__(self, method: str, message: str, code: int | None = None) -> None:
        self.method = method
        self.code = code
        label = f"код {code}: " if code is not None else ""
        super().__init__(f"{method}: {label}{message}")


class VKClient:
    def __init__(self, token: str, group_id: int, timeout: int = 30) -> None:
        if not token.strip():
            raise ValueError("VK_COMMUNITY_TOKEN is empty")
        self._token = token.strip()
        self.group_id = group_id
        self.owner_id = -group_id
        self.timeout = timeout

    def call(self, method: str, **params: Any) -> Any:
        import requests

        if method in DESTRUCTIVE_METHODS:
            raise VKError(method, "destructive method is blocked")
        payload = {
            **{key: value for key, value in params.items() if value is not None},
            "access_token": self._token,
            "v": API_VERSION,
        }
        last_network_error: Exception | None = None
        for origin in API_ORIGINS:
            try:
                response = requests.post(
                    f"{origin}/{method}",
                    data=payload,
                    timeout=self.timeout,
                    headers={"User-Agent": "ANIMA-TACTUS-safe-manager/1.0"},
                )
                response.raise_for_status()
                data = response.json()
            except (requests.RequestException, ValueError) as exc:
                last_network_error = exc
                continue
            if "error" in data:
                error = data["error"]
                raise VKError(
                    method,
                    str(error.get("error_msg", "ошибка VK")),
                    int(error["error_code"]) if "error_code" in error else None,
                )
            if "response" not in data:
                raise VKError(method, "VK returned an empty response")
            return data["response"]
        raise VKError(method, f"network error ({type(last_network_error).__name__})")

    def optional(self, method: str, **params: Any) -> dict[str, Any]:
        try:
            return {"ok": True, "value": self.call(method, **params)}
        except VKError as exc:
            return {"ok": False, "error": str(exc), "code": exc.code}


def items_of(value: Any) -> list[dict[str, Any]]:
    if isinstance(value, list):
        return [item for item in value if isinstance(item, dict)]
    if isinstance(value, dict):
        for key in ("items", "groups"):
            if isinstance(value.get(key), list):
                return [item for item in value[key] if isinstance(item, dict)]
    return []


def count_of(call: dict[str, Any] | None) -> int | None:
    if not call or not call.get("ok"):
        return None
    value = call.get("value")
    if isinstance(value, dict) and isinstance(value.get("count"), int):
        return value["count"]
    if isinstance(value, list):
        return len(value)
    return None


def group_of(call: dict[str, Any] | None) -> dict[str, Any]:
    if not call or not call.get("ok"):
        return {}
    values = items_of(call.get("value"))
    if values:
        return values[0]
    return call.get("value") if isinstance(call.get("value"), dict) else {}


def normalize_url(value: Any) -> str:
    return str(value or "").strip().rstrip("/").replace("http://", "https://", 1)


def parse_time(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)


def validate_plan(plan: dict[str, Any]) -> None:
    posts = plan.get("posts")
    if not isinstance(posts, list) or len(posts) < 12:
        raise ValueError("Content plan must contain at least 12 posts")
    ids: set[str] = set()
    previous: datetime | None = None
    for item in posts:
        content_id = str(item.get("id", "")).strip()
        text = str(item.get("text", "")).strip()
        publish_at = parse_time(str(item.get("publish_at", "")))
        if not content_id or content_id in ids:
            raise ValueError(f"Invalid or duplicate content id: {content_id!r}")
        if len(text) < 80:
            raise ValueError(f"Post {content_id} is too short")
        if previous and publish_at < previous:
            raise ValueError("Posts must be ordered by publish_at")
        ids.add(content_id)
        previous = publish_at


def audit_community(client: VKClient) -> dict[str, dict[str, Any]]:
    gid = client.group_id
    owner = client.owner_id
    return {
        "group": client.optional(
            "groups.getById",
            group_id=gid,
            fields="description,status,activity,site,contacts,links,counters,cover,can_message,can_post,members_count",
        ),
        "settings": client.optional("groups.getSettings", group_id=gid),
        "wall": client.optional("wall.get", owner_id=owner, count=100, filter="owner"),
        "videos": client.optional("video.get", owner_id=owner, count=200, extended=1),
        "photos": client.optional("photos.getAll", owner_id=owner, count=200),
        "topics": client.optional("board.getTopics", group_id=gid, count=100),
        "market": client.optional("market.get", owner_id=owner, count=200),
        "docs": client.optional("docs.get", owner_id=owner, count=200),
        "addresses": client.optional("groups.getAddresses", group_id=gid, count=100),
    }


def font(size: int, bold: bool = False) -> Any:
    from PIL import ImageFont

    choices = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold
        else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf" if bold
        else "/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf",
    ]
    for path in choices:
        if Path(path).exists():
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()


def wrap_pixels(draw: Any, text: str, chosen_font: Any, width: int) -> list[str]:
    lines: list[str] = []
    for paragraph in text.splitlines() or [""]:
        words = paragraph.split()
        current = ""
        for word in words:
            candidate = f"{current} {word}".strip()
            box = draw.textbbox((0, 0), candidate, font=chosen_font)
            if current and box[2] - box[0] > width:
                lines.append(current)
                current = word
            else:
                current = candidate
        if current:
            lines.append(current)
    return lines


def render_card(spec: dict[str, Any]) -> bytes:
    from PIL import Image, ImageDraw

    width, height = 1080, 1350
    image = Image.new("RGB", (width, height), "#F4F6FF")
    draw = ImageDraw.Draw(image)
    top = (35, 42, 92)
    bottom = (111, 86, 190)
    for y in range(height):
        ratio = y / max(1, height - 1)
        color = tuple(int(top[i] * (1 - ratio) + bottom[i] * ratio) for i in range(3))
        draw.line((0, y, width, y), fill=color)
    draw.ellipse((720, -160, 1210, 330), fill=(62, 196, 181))
    draw.ellipse((-210, 970, 310, 1490), fill=(233, 111, 128))
    draw.rounded_rectangle((70, 75, 1010, 1275), radius=54, fill=(255, 255, 255))

    eyebrow = str(spec.get("eyebrow", "ПРАКТИКА САМОНАБЛЮДЕНИЯ")).upper()
    title = str(spec.get("title", "Остановиться и заметить"))
    subtitle = str(spec.get("subtitle", "Один спокойный шаг за раз"))

    draw.text((125, 145), eyebrow, font=font(30, True), fill="#6750A4")
    title_font = font(72, True)
    title_lines = wrap_pixels(draw, title, title_font, 820)
    y = 300
    for line in title_lines[:5]:
        draw.text((125, y), line, font=title_font, fill="#172033")
        y += 92

    draw.rounded_rectangle((125, y + 45, 860, y + 55), radius=5, fill="#3EC4B5")
    y += 105
    subtitle_font = font(38, False)
    for line in wrap_pixels(draw, subtitle, subtitle_font, 800)[:4]:
        draw.text((125, y), line, font=subtitle_font, fill="#48536B")
        y += 56

    draw.text((125, 1160), "ANIMA TACTUS", font=font(34, True), fill="#172033")
    draw.text((125, 1210), "Назвать • понять • выбрать", font=font(25), fill="#697386")

    output = io.BytesIO()
    image.save(output, format="PNG", optimize=True)
    return output.getvalue()


def upload_wall_photo(client: VKClient, image_bytes: bytes) -> str:
    import requests

    server = client.call("photos.getWallUploadServer", group_id=client.group_id)
    upload_url = str(server.get("upload_url", ""))
    if not upload_url.startswith("https://"):
        raise VKError("photos.getWallUploadServer", "invalid upload URL")
    try:
        response = requests.post(
            upload_url,
            files={"photo": ("anima-tactus-card.png", image_bytes, "image/png")},
            timeout=60,
            headers={"User-Agent": "ANIMA-TACTUS-safe-manager/1.0"},
        )
        response.raise_for_status()
        uploaded = response.json()
    except (requests.RequestException, ValueError) as exc:
        raise VKError("photo.upload", f"network error ({type(exc).__name__})") from exc
    saved = client.call(
        "photos.saveWallPhoto",
        group_id=client.group_id,
        photo=uploaded.get("photo"),
        server=uploaded.get("server"),
        hash=uploaded.get("hash"),
    )
    photos = items_of(saved)
    if not photos and isinstance(saved, list):
        photos = [item for item in saved if isinstance(item, dict)]
    if not photos:
        raise VKError("photos.saveWallPhoto", "VK did not return a photo")
    photo = photos[0]
    return f"photo{photo['owner_id']}_{photo['id']}"


def safe_attempt(label: str, operation: Any, operations: list[str], failures: list[str]) -> Any:
    try:
        result = operation()
        operations.append(label)
        return result
    except (VKError, ValueError, KeyError) as exc:
        failures.append(str(exc))
        return None


def build_group_settings(audit: dict[str, dict[str, Any]], group_id: int) -> tuple[dict[str, Any], list[str]]:
    settings: dict[str, Any] = {
        "group_id": group_id,
        "title": CANONICAL_NAME,
        "description": CANONICAL_DESCRIPTION,
        "messages": 1,
        "links": 1,
        "photos": 1,
    }
    hidden: list[str] = []
    candidates = [
        ("topics", "topics", "Обсуждения"),
        ("video", "videos", "Видео"),
        ("docs", "docs", "Документы"),
        ("market", "market", "Товары"),
        ("addresses", "addresses", "Адреса"),
    ]
    for parameter, audit_key, label in candidates:
        if count_of(audit.get(audit_key)) == 0:
            settings[parameter] = 0
            hidden.append(label)
    return settings, hidden


def ensure_message_link(client: VKClient, group: dict[str, Any]) -> str:
    links = group.get("links") if isinstance(group.get("links"), list) else []
    existing = next(
        (item for item in links if normalize_url(item.get("url")) == normalize_url(MESSAGE_LINK)),
        None,
    )
    if existing:
        current = str(existing.get("name") or existing.get("desc") or "")
        if current != MESSAGE_LINK_TEXT and isinstance(existing.get("id"), int):
            client.call(
                "groups.editLink",
                group_id=client.group_id,
                link_id=existing["id"],
                text=MESSAGE_LINK_TEXT,
            )
            return "Подпись ссылки на сообщения обновлена"
        return "Ссылка на сообщения уже настроена"
    client.call(
        "groups.addLink",
        group_id=client.group_id,
        link=MESSAGE_LINK,
        text=MESSAGE_LINK_TEXT,
    )
    return "Ссылка «Начать — написать» добавлена"


def existing_wall_posts(client: VKClient) -> list[dict[str, Any]]:
    return items_of(client.call("wall.get", owner_id=client.owner_id, count=100, filter="owner"))


def publish_post(client: VKClient, item: dict[str, Any], operations: list[str], failures: list[str]) -> int | None:
    text = str(item["text"]).strip()
    posts = existing_wall_posts(client)
    existing = next((post for post in posts if str(post.get("text", "")).strip() == text), None)
    if existing:
        post_id = int(existing["id"])
        operations.append(f"Публикация {item['id']} уже существует")
    else:
        attachment = None
        card = item.get("card")
        if isinstance(card, dict):
            try:
                attachment = upload_wall_photo(client, render_card(card))
            except (VKError, ValueError, KeyError) as exc:
                failures.append(f"Карточка {item['id']}: {exc}; текст будет опубликован без изображения")
        response = client.call(
            "wall.post",
            owner_id=client.owner_id,
            from_group=1,
            message=text,
            attachments=attachment,
            guid=f"anima-tactus-{item['id']}"[:64],
        )
        post_id = int(response.get("post_id") if isinstance(response, dict) else response)
        operations.append(f"Опубликован материал {item['id']}")
    if item.get("pin"):
        client.call("wall.pin", owner_id=client.owner_id, post_id=post_id)
        operations.append(f"Материал {item['id']} закреплён; прежний пост сохранён")
    return post_id


def apply_safe_packaging(
    client: VKClient,
    audit: dict[str, dict[str, Any]],
    welcome_item: dict[str, Any],
) -> tuple[list[str], list[str], list[str]]:
    operations: list[str] = []
    failures: list[str] = []
    settings, hidden = build_group_settings(audit, client.group_id)

    safe_attempt(
        "Название, описание, сообщения и разделы синхронизированы",
        lambda: client.call("groups.edit", **settings),
        operations,
        failures,
    )
    safe_attempt(
        "Статус сообщества синхронизирован",
        lambda: client.call("status.set", group_id=client.group_id, text=CANONICAL_STATUS),
        operations,
        failures,
    )
    group = group_of(audit.get("group"))
    link_result = safe_attempt(
        "Ссылка на сообщения проверена",
        lambda: ensure_message_link(client, group),
        operations,
        failures,
    )
    if isinstance(link_result, str):
        operations.append(link_result)

    safe_attempt(
        "Приветственный маршрут проверен",
        lambda: publish_post(client, welcome_item, operations, failures),
        operations,
        failures,
    )
    return operations, failures, hidden


def normalize_command(text: str) -> str:
    return " ".join(text.casefold().replace("ё", "е").split()).strip(" .,!?:;—-«»\"'")


def reply_for(text: str) -> str | None:
    command = normalize_command(text)
    routes = {
        "старт": NAVIGATION_REPLY,
        "start": NAVIGATION_REPLY,
        "начать": NAVIGATION_REPLY,
        "чувства": FEELINGS_REPLY,
        "эмоции": FEELINGS_REPLY,
        "пауза": PAUSE_REPLY,
        "приложение": APP_REPLY,
        "программы": PROGRAMS_REPLY,
        "человек": HUMAN_REPLY,
        "оператор": HUMAN_REPLY,
        "администратор": HUMAN_REPLY,
    }
    return routes.get(command)


def stable_random_id(peer_id: int, message_id: int) -> int:
    digest = hashlib.sha256(f"{peer_id}:{message_id}:anima-tactus".encode()).digest()
    value = int.from_bytes(digest[:4], "big") & 0x7FFFFFFF
    return value or 1


def process_messages(client: VKClient) -> tuple[int, list[str]]:
    failures: list[str] = []
    sent = 0
    try:
        conversations = client.call(
            "messages.getConversations",
            filter="unread",
            count=100,
            extended=0,
        )
    except VKError as exc:
        return 0, [str(exc)]

    for item in items_of(conversations):
        conversation = item.get("conversation") or {}
        last_message = item.get("last_message") or {}
        peer = conversation.get("peer") or {}
        if last_message.get("out") == 1:
            continue
        reply = reply_for(str(last_message.get("text") or ""))
        peer_id = peer.get("id")
        message_id = last_message.get("id")
        if not reply or not isinstance(peer_id, int) or not isinstance(message_id, int):
            continue
        try:
            client.call(
                "messages.send",
                peer_id=peer_id,
                random_id=stable_random_id(peer_id, message_id),
                message=reply,
            )
            client.call("messages.markAsRead", peer_id=peer_id)
            sent += 1
        except VKError as exc:
            failures.append(str(exc))
    return sent, failures


def collect_delete_candidates(audit: dict[str, dict[str, Any]]) -> list[str]:
    candidates: list[str] = []
    group = group_of(audit.get("group"))
    links = group.get("links") if isinstance(group.get("links"), list) else []
    grouped_links: dict[str, list[dict[str, Any]]] = {}
    for item in links:
        url = normalize_url(item.get("url"))
        if url:
            grouped_links.setdefault(url, []).append(item)
    for url, items in grouped_links.items():
        if len(items) > 1:
            candidates.append(f"Дубли ссылок ({len(items)}): {url}")

    grouped_titles: dict[str, list[dict[str, Any]]] = {}
    for item in items_of(audit.get("videos", {}).get("value")):
        title = str(item.get("title") or "").strip().casefold()
        if not title:
            candidates.append(f"Видео без названия: ID {item.get('id', 'неизвестен')}")
        else:
            grouped_titles.setdefault(title, []).append(item)
    for title, items in grouped_titles.items():
        if len(items) > 1:
            candidates.append(f"Видео с одинаковым названием ({len(items)}): «{title}»")
    return candidates


def public_snapshot(audit: dict[str, dict[str, Any]]) -> dict[str, Any]:
    group = group_of(audit.get("group"))
    return {
        "name": group.get("name"),
        "status": group.get("status"),
        "members_count": group.get("members_count"),
        "wall_count": count_of(audit.get("wall")),
        "video_count": count_of(audit.get("videos")),
        "photo_count": count_of(audit.get("photos")),
        "topic_count": count_of(audit.get("topics")),
        "market_count": count_of(audit.get("market")),
        "document_count": count_of(audit.get("docs")),
        "address_count": count_of(audit.get("addresses")),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument("--report", type=Path, default=Path("vk-anima-report/report.json"))
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    plan = json.loads(args.plan.read_text(encoding="utf-8"))
    validate_plan(plan)
    if args.dry_run:
        print(json.dumps({
            "status": "PASS",
            "posts": len(plan["posts"]),
            "destructive_methods_enabled": False,
            "personal_data_persisted": False,
        }, ensure_ascii=False))
        return 0

    token = os.environ.get("VK_COMMUNITY_TOKEN", "")
    group_id = int(os.environ.get("VK_GROUP_ID", str(GROUP_ID_DEFAULT)))
    client = VKClient(token, group_id)
    now = datetime.now(timezone.utc)

    initial = audit_community(client)
    welcome = next(item for item in plan["posts"] if item.get("pin"))
    operations, failures, hidden = apply_safe_packaging(client, initial, welcome)

    for item in plan["posts"]:
        if item.get("pin") or parse_time(item["publish_at"]) > now:
            continue
        safe_attempt(
            f"Материал {item['id']} обработан",
            lambda item=item: publish_post(client, item, operations, failures),
            operations,
            failures,
        )

    replies_sent, message_failures = process_messages(client)
    failures.extend(message_failures)
    final = audit_community(client)

    audit_errors = {
        key: value.get("error")
        for key, value in final.items()
        if not value.get("ok")
    }
    report = {
        "schema_version": 1,
        "generated_at": now.isoformat(),
        "community_id": group_id,
        "initial": public_snapshot(initial),
        "final": public_snapshot(final),
        "operations": operations,
        "failures": failures,
        "hidden_confirmed_empty_sections": hidden,
        "message_replies_sent": replies_sent,
        "deletion_candidates_for_owner_approval": collect_delete_candidates(final),
        "api_limitations": audit_errors,
        "safety": {
            "destructive_actions_performed": False,
            "avatar_changed": False,
            "cover_changed": False,
            "member_or_message_data_persisted": False,
            "token_persisted": False,
        },
    }
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "status": "COMPLETED",
        "operations": len(operations),
        "failures": len(failures),
        "message_replies_sent": replies_sent,
        "deletion_candidates": len(report["deletion_candidates_for_owner_approval"]),
    }, ensure_ascii=False))

    group_error_code = initial.get("group", {}).get("code")
    if group_error_code == 5:
        print("VK community token is invalid or revoked.", file=sys.stderr)
        return 3
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
