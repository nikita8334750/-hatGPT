from __future__ import annotations

from html import escape
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import List
from urllib.parse import parse_qs

from logistics import LogisticsService, RouteSegment, SAMPLE_SEGMENTS

service = LogisticsService(SAMPLE_SEGMENTS)


STYLE = """
:root { color-scheme: light; }
body { font-family: Inter, Arial, sans-serif; margin: 0; background: #f4f7fb; color: #1b2a41; }
header { background: linear-gradient(135deg, #2e6ee6, #5a8bf0); color: #fff; padding: 24px; }
.container { max-width: 1200px; margin: 20px auto; padding: 0 16px; }
.grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(290px, 1fr)); gap: 16px; }
.card { background: #fff; border-radius: 12px; padding: 16px; box-shadow: 0 4px 14px rgba(33, 70, 139, 0.1); }
h2 { margin-top: 0; font-size: 18px; }
label { display: block; margin: 8px 0 4px; font-size: 14px; }
input { width: 100%; box-sizing: border-box; padding: 10px; border: 1px solid #cfd8ea; border-radius: 8px; }
button { margin-top: 10px; width: 100%; padding: 10px; border: 0; border-radius: 8px; background: #2e6ee6; color: #fff; font-weight: 600; cursor: pointer; }
button:hover { background: #205bd0; }
.notice { margin: 12px 0; padding: 10px 12px; border-radius: 8px; background: #e8f1ff; color: #214d96; }
.error { background: #ffeaea; color: #902323; }
.table { width: 100%; border-collapse: collapse; font-size: 14px; }
.table th, .table td { border-bottom: 1px solid #e4e8f2; text-align: left; padding: 8px; }
.small { font-size: 12px; color: #566885; }
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
        "<table class='table'><thead><tr><th>ID</th><th>Маршрут</th><th>Время</th><th>Водитель</th><th>Свободно мест</th>"
        f"</tr></thead><tbody>{rows}</tbody></table>"
    )


def render_page(message: str = "", error: bool = False, results_html: str = "") -> str:
    msg_block = f"<div class='notice {'error' if error else ''}'>{escape(message)}</div>" if message else ""
    all_routes = render_routes(list(service.segments.values()))
    return f"""<!doctype html>
<html lang='ru'>
<head>
  <meta charset='utf-8'>
  <meta name='viewport' content='width=device-width, initial-scale=1'>
  <title>Логистика перевозок</title>
  <style>{STYLE}</style>
</head>
<body>
<header>
  <h1>Логистическая программа перевозок</h1>
  <p>Для водителей и пассажиров: маршруты, расписание, бронирование и передачки.</p>
</header>
<div class='container'>
  {msg_block}
  <div class='card'><h2>Доступные рейсы</h2>{all_routes}</div>
  <div class='grid'>
    <form class='card' method='post'>
      <h2>Найти последовательность маршрута</h2>
      <input type='hidden' name='action' value='find_route'>
      <label>Город отправления</label><input name='departure_city' required>
      <label>Город назначения</label><input name='arrival_city' required>
      <label>Не раньше времени (HH:MM)</label><input name='earliest_departure' placeholder='например 08:00'>
      <button type='submit'>Построить маршрут</button>
    </form>

    <form class='card' method='post'>
      <h2>Расписание водителя</h2>
      <input type='hidden' name='action' value='driver_schedule'>
      <label>Имя водителя</label><input name='driver_name' required>
      <button type='submit'>Показать</button>
    </form>

    <form class='card' method='post'>
      <h2>Расписание по городу</h2>
      <input type='hidden' name='action' value='city_schedule'>
      <label>Город</label><input name='city' required>
      <button type='submit'>Показать</button>
    </form>

    <form class='card' method='post'>
      <h2>Забронировать места</h2>
      <input type='hidden' name='action' value='book'>
      <label>ID маршрута</label><input name='route_id' required>
      <label>ФИО пассажира</label><input name='passenger_name' required>
      <label>Количество мест</label><input name='seats' type='number' min='1' required>
      <button type='submit'>Забронировать</button>
    </form>

    <form class='card' method='post'>
      <h2>Оформить передачку</h2>
      <input type='hidden' name='action' value='parcel'>
      <label>ID маршрута</label><input name='route_id' required>
      <label>Отправитель</label><input name='sender_name' required>
      <label>Получатель</label><input name='recipient_name' required>
      <label>Описание</label><input name='description' required>
      <button type='submit'>Оформить</button>
    </form>
  </div>

  <div class='card'>
    <h2>Результат запроса</h2>
    {results_html or "<p class='small'>Выполните действие в одной из карточек выше.</p>"}
  </div>
</div>
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

    def do_GET(self) -> None:  # noqa: N802
        self._send_html(render_page())

    def do_POST(self) -> None:  # noqa: N802
        length = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(length).decode("utf-8")
        data = {k: v[0] for k, v in parse_qs(raw).items()}

        try:
            action = data.get("action", "")
            if action == "find_route":
                routes = service.find_route_sequence(
                    data.get("departure_city", ""),
                    data.get("arrival_city", ""),
                    data.get("earliest_departure") or None,
                )
                self._send_html(render_page("Маршрут построен", results_html=render_routes(routes)))
                return

            if action == "driver_schedule":
                routes = service.schedule_for_driver(data.get("driver_name", ""))
                self._send_html(render_page("Расписание водителя", results_html=render_routes(routes)))
                return

            if action == "city_schedule":
                routes = service.schedule_for_passenger(data.get("city", ""))
                self._send_html(render_page("Расписание по городу", results_html=render_routes(routes)))
                return

            if action == "book":
                booking = service.book_seats(
                    data.get("route_id", ""),
                    data.get("passenger_name", ""),
                    int(data.get("seats", "0")),
                )
                self._send_html(render_page(f"Бронь #{booking.booking_id} успешно создана"))
                return

            if action == "parcel":
                parcel = service.register_parcel(
                    data.get("route_id", ""),
                    data.get("sender_name", ""),
                    data.get("recipient_name", ""),
                    data.get("description", ""),
                )
                self._send_html(render_page(f"Передачка #{parcel.parcel_id} успешно оформлена"))
                return

            self._send_html(render_page("Неизвестное действие", error=True))
        except ValueError as exc:
            self._send_html(render_page(f"Ошибка: {exc}", error=True))


def run() -> None:
    host, port = "0.0.0.0", 8080
    server = HTTPServer((host, port), LogisticsHandler)
    print(f"Сервер запущен: http://{host}:{port}")
    server.serve_forever()


if __name__ == "__main__":
    run()
