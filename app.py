from __future__ import annotations

from html import escape
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Dict, List
from urllib.parse import parse_qs

from logistics import LogisticsService, RouteSegment, SAMPLE_SEGMENTS

service = LogisticsService(SAMPLE_SEGMENTS)

MANIFEST_JSON = """{
  \"name\": \"Логистика перевозок\",
  \"short_name\": \"Логистика\",
  \"start_url\": \"/\",
  \"display\": \"standalone\",
  \"background_color\": \"#f4f7fb\",
  \"theme_color\": \"#2e6ee6\",
  \"description\": \"Маршруты, бронирования и передачки для водителей и пассажиров\",
  \"icons\": []
}"""

SERVICE_WORKER_JS = """
self.addEventListener('install', event => {
  event.waitUntil(self.skipWaiting());
});

self.addEventListener('activate', event => {
  event.waitUntil(self.clients.claim());
});

self.addEventListener('fetch', () => {
  // Network-first strategy for this lightweight app.
});
"""

STYLE = """
:root {
  color-scheme: light;
  --bg: #f4f7fb;
  --surface: #ffffff;
  --primary: #2e6ee6;
  --primary-dark: #205bd0;
  --text: #1b2a41;
  --muted: #566885;
}
* { box-sizing: border-box; }
html, body { margin: 0; padding: 0; font-family: Inter, Arial, sans-serif; background: var(--bg); color: var(--text); }
body { padding-bottom: 72px; }
header { background: linear-gradient(135deg, var(--primary), #5a8bf0); color: #fff; padding: 18px 16px; }
header h1 { margin: 0; font-size: 22px; }
header p { margin: 6px 0 0; font-size: 14px; opacity: 0.95; }
.container { max-width: 1200px; margin: 14px auto; padding: 0 12px; }
.grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 12px; }
.card { background: var(--surface); border-radius: 14px; padding: 14px; box-shadow: 0 4px 14px rgba(33, 70, 139, 0.1); }
h2 { margin-top: 0; font-size: 17px; }
label { display: block; margin: 8px 0 4px; font-size: 14px; }
input { width: 100%; padding: 10px; border: 1px solid #cfd8ea; border-radius: 10px; font-size: 16px; }
button { margin-top: 10px; width: 100%; padding: 12px; border: 0; border-radius: 10px; background: var(--primary); color: #fff; font-size: 15px; font-weight: 600; }
button:hover { background: var(--primary-dark); }
.notice { margin: 10px 0; padding: 10px 12px; border-radius: 10px; background: #e8f1ff; color: #214d96; }
.error { background: #ffeaea; color: #902323; }
.table-wrap { overflow-x: auto; }
.table { width: 100%; border-collapse: collapse; min-width: 640px; font-size: 14px; }
.table th, .table td { border-bottom: 1px solid #e4e8f2; text-align: left; padding: 8px; }
.small { font-size: 12px; color: var(--muted); }
.mobile-nav { position: fixed; bottom: 0; left: 0; right: 0; background: #fff; border-top: 1px solid #d9e2f2; display: none; gap: 6px; padding: 8px; }
.mobile-nav a { flex: 1; text-align: center; font-size: 12px; text-decoration: none; color: var(--text); background: #f3f6fc; padding: 8px 6px; border-radius: 8px; }
@media (max-width: 820px) {
  .grid { grid-template-columns: 1fr; }
  .card { padding: 12px; }
  .mobile-nav { display: flex; }
}
"""


def render_routes(routes: List[RouteSegment]) -> str:
    if not routes:
        return "<p class='small'>Нет найденных рейсов.</p>"

    rows = "".join(
        f"<tr><td>{escape(s.route_id)}</td><td>{escape(s.departure_city)} → {escape(s.arrival_city)}</td>"
        f"<td>{escape(s.departure_time)} - {escape(s.arrival_time)}</td><td>{escape(s.driver_name)}</td>"
        f"<td>{s.available_seats}</td></tr>"
        for s in routes
    )
    return (
        "<div class='table-wrap'><table class='table'><thead><tr><th>ID</th><th>Маршрут</th><th>Время</th><th>Водитель</th><th>Свободно мест</th>"
        f"</tr></thead><tbody>{rows}</tbody></table></div>"
    )


def render_page(message: str = "", error: bool = False, results_html: str = "") -> str:
    msg_block = f"<div class='notice {'error' if error else ''}'>{escape(message)}</div>" if message else ""
    all_routes = render_routes(list(service.segments.values()))
    return f"""<!doctype html>
<html lang='ru'>
<head>
  <meta charset='utf-8'>
  <meta name='viewport' content='width=device-width, initial-scale=1, viewport-fit=cover'>
  <meta name='theme-color' content='#2e6ee6'>
  <meta name='apple-mobile-web-app-capable' content='yes'>
  <meta name='apple-mobile-web-app-status-bar-style' content='default'>
  <meta name='apple-mobile-web-app-title' content='Логистика'>
  <link rel='manifest' href='/manifest.webmanifest'>
  <title>Логистика перевозок</title>
  <style>{STYLE}</style>
</head>
<body>
<header>
  <h1>Логистика перевозок</h1>
  <p>Мобильная версия для iOS и Android: маршруты, расписание, бронь и передачки.</p>
</header>
<div class='container'>
  {msg_block}

  <div id='routes' class='card'><h2>Доступные рейсы</h2>{all_routes}</div>

  <div class='grid'>
    <form id='route' class='card' method='post'>
      <h2>Построить маршрут</h2>
      <input type='hidden' name='action' value='find_route'>
      <label>Откуда</label><input name='departure_city' required>
      <label>Куда</label><input name='arrival_city' required>
      <label>Не раньше (HH:MM)</label><input name='earliest_departure' placeholder='08:00'>
      <button type='submit'>Найти путь</button>
    </form>

    <form id='driver' class='card' method='post'>
      <h2>Водитель</h2>
      <input type='hidden' name='action' value='driver_schedule'>
      <label>Имя водителя</label><input name='driver_name' required>
      <button type='submit'>Показать расписание</button>
    </form>

    <form id='passenger' class='card' method='post'>
      <h2>Пассажир</h2>
      <input type='hidden' name='action' value='city_schedule'>
      <label>Город</label><input name='city' required>
      <button type='submit'>Показать рейсы</button>
    </form>

    <form id='book' class='card' method='post'>
      <h2>Бронирование</h2>
      <input type='hidden' name='action' value='book'>
      <label>ID маршрута</label><input name='route_id' required>
      <label>ФИО пассажира</label><input name='passenger_name' required>
      <label>Мест</label><input name='seats' type='number' min='1' required>
      <button type='submit'>Забронировать</button>
    </form>

    <form id='parcel' class='card' method='post'>
      <h2>Передачка</h2>
      <input type='hidden' name='action' value='parcel'>
      <label>ID маршрута</label><input name='route_id' required>
      <label>Отправитель</label><input name='sender_name' required>
      <label>Получатель</label><input name='recipient_name' required>
      <label>Описание</label><input name='description' required>
      <button type='submit'>Оформить</button>
    </form>
  </div>

  <div id='result' class='card'>
    <h2>Результат</h2>
    {results_html or "<p class='small'>Выберите действие выше.</p>"}
  </div>
</div>

<nav class='mobile-nav'>
  <a href='#route'>Маршрут</a>
  <a href='#driver'>Водитель</a>
  <a href='#book'>Бронь</a>
  <a href='#result'>Итог</a>
</nav>

<script>
if ('serviceWorker' in navigator) {{
  navigator.serviceWorker.register('/service-worker.js').catch(() => null);
}}
</script>
</body>
</html>"""


class LogisticsHandler(BaseHTTPRequestHandler):
    def _send_html(self, html: str) -> None:
        body = html.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_text(self, body: str, content_type: str) -> None:
        data = body.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _handle_action(self, data: Dict[str, str]) -> str:
        action = data.get("action", "")
        if action == "find_route":
            routes = service.find_route_sequence(
                data.get("departure_city", ""),
                data.get("arrival_city", ""),
                data.get("earliest_departure") or None,
            )
            return render_page("Маршрут построен", results_html=render_routes(routes))

        if action == "driver_schedule":
            routes = service.schedule_for_driver(data.get("driver_name", ""))
            return render_page("Расписание водителя", results_html=render_routes(routes))

        if action == "city_schedule":
            routes = service.schedule_for_passenger(data.get("city", ""))
            return render_page("Расписание по городу", results_html=render_routes(routes))

        if action == "book":
            booking = service.book_seats(
                data.get("route_id", ""),
                data.get("passenger_name", ""),
                int(data.get("seats", "0")),
            )
            return render_page(f"Бронь #{booking.booking_id} успешно создана")

        if action == "parcel":
            parcel = service.register_parcel(
                data.get("route_id", ""),
                data.get("sender_name", ""),
                data.get("recipient_name", ""),
                data.get("description", ""),
            )
            return render_page(f"Передачка #{parcel.parcel_id} успешно оформлена")

        return render_page("Неизвестное действие", error=True)

    def do_GET(self) -> None:  # noqa: N802
        if self.path == "/manifest.webmanifest":
            self._send_text(MANIFEST_JSON, "application/manifest+json; charset=utf-8")
            return
        if self.path == "/service-worker.js":
            self._send_text(SERVICE_WORKER_JS, "application/javascript; charset=utf-8")
            return
        self._send_html(render_page())

    def do_POST(self) -> None:  # noqa: N802
        length = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(length).decode("utf-8")
        data = {k: v[0] for k, v in parse_qs(raw).items()}

        try:
            self._send_html(self._handle_action(data))
        except ValueError as exc:
            self._send_html(render_page(f"Ошибка: {exc}", error=True))


def run() -> None:
    host, port = "0.0.0.0", 8080
    server = HTTPServer((host, port), LogisticsHandler)
    print(f"Сервер запущен: http://{host}:{port}")
    server.serve_forever()


if __name__ == "__main__":
    run()
