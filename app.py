from __future__ import annotations

import json
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Dict, List
from urllib.parse import parse_qs, urlparse

from logistics import LogisticsService, RouteSegment, SAMPLE_SEGMENTS

service = LogisticsService(SAMPLE_SEGMENTS)

MANIFEST_JSON = {
    "name": "Логистика перевозок",
    "short_name": "Логистика",
    "start_url": "/",
    "display": "standalone",
    "background_color": "#0b1020",
    "theme_color": "#4f7cff",
    "description": "Маршруты, бронирования и передачки для водителей и пассажиров",
    "icons": [],
}

SERVICE_WORKER_JS = """
self.addEventListener('install', event => event.waitUntil(self.skipWaiting()));
self.addEventListener('activate', event => event.waitUntil(self.clients.claim()));
self.addEventListener('fetch', () => {});
"""

STYLE = """
:root {
  --bg: #0b1020;
  --bg-soft: #131a30;
  --surface: rgba(255,255,255,0.08);
  --surface-strong: rgba(255,255,255,0.12);
  --text: #f5f7ff;
  --muted: #b6c1e3;
  --primary: #4f7cff;
  --primary-2: #58d6ff;
  --ok: #22c55e;
  --err: #f87171;
  --shadow: 0 18px 40px rgba(0,0,0,0.35);
}
* { box-sizing: border-box; }
html, body { margin: 0; padding: 0; font-family: Inter, -apple-system, BlinkMacSystemFont, Segoe UI, sans-serif; background: radial-gradient(circle at 0% 0%, #1d2a52, var(--bg) 45%); color: var(--text); }
body { min-height: 100vh; }
.container { max-width: 1250px; margin: 0 auto; padding: 18px 14px 80px; }
.hero { padding: 22px; border-radius: 20px; background: linear-gradient(140deg, rgba(79,124,255,.32), rgba(88,214,255,.15)); box-shadow: var(--shadow); border: 1px solid rgba(255,255,255,.12); }
.hero h1 { margin: 0; font-size: clamp(24px, 5vw, 38px); }
.hero p { color: var(--muted); margin: 10px 0 0; }
.metrics { margin-top: 14px; display: grid; grid-template-columns: repeat(auto-fit, minmax(160px, 1fr)); gap: 10px; }
.metric { background: var(--surface); border: 1px solid rgba(255,255,255,.12); border-radius: 14px; padding: 10px; }
.metric b { display: block; font-size: 24px; margin-top: 4px; }
.layout { margin-top: 14px; display: grid; grid-template-columns: 1.1fr .9fr; gap: 12px; }
.card { background: var(--surface); border: 1px solid rgba(255,255,255,.11); border-radius: 16px; padding: 14px; backdrop-filter: blur(8px); }
.card h2 { margin: 0 0 12px; font-size: 18px; }
.table-wrap { max-height: 420px; overflow: auto; border: 1px solid rgba(255,255,255,.1); border-radius: 10px; }
.table { width: 100%; border-collapse: collapse; min-width: 600px; font-size: 14px; }
.table th, .table td { border-bottom: 1px solid rgba(255,255,255,.08); padding: 8px; text-align: left; }
.table th { position: sticky; top: 0; background: #111932; z-index: 2; }
.controls { display: flex; gap: 8px; margin-bottom: 10px; }
.input, select, button { width: 100%; border-radius: 10px; border: 1px solid rgba(255,255,255,.15); padding: 11px 12px; font-size: 15px; color: var(--text); background: rgba(0,0,0,.2); }
.input::placeholder { color: #9dadde; }
button { cursor: pointer; border: none; background: linear-gradient(120deg, var(--primary), var(--primary-2)); color: #fff; font-weight: 700; }
button.ghost { background: rgba(255,255,255,.08); border: 1px solid rgba(255,255,255,.2); }
.forms { display: grid; gap: 10px; }
.form { display: grid; gap: 8px; padding: 12px; background: rgba(0,0,0,.2); border-radius: 12px; border: 1px solid rgba(255,255,255,.09); }
.form-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; }
.status { margin-top: 10px; padding: 10px; border-radius: 10px; background: rgba(79,124,255,.22); border: 1px solid rgba(79,124,255,.45); }
.status.error { background: rgba(248,113,113,.15); border-color: rgba(248,113,113,.5); }
.list { display: grid; gap: 8px; margin-top: 10px; }
.item { background: rgba(255,255,255,.06); border: 1px solid rgba(255,255,255,.1); border-radius: 10px; padding: 8px; font-size: 13px; }
.mobile-nav { display: none; position: fixed; left: 10px; right: 10px; bottom: 10px; background: rgba(16,24,44,.92); border: 1px solid rgba(255,255,255,.16); border-radius: 12px; padding: 6px; gap: 6px; }
.mobile-nav a { flex: 1; text-decoration: none; text-align: center; color: var(--text); font-size: 12px; padding: 8px 4px; border-radius: 8px; background: rgba(255,255,255,.08); }
@media (max-width: 980px) { .layout { grid-template-columns: 1fr; } }
@media (max-width: 760px) {
  .container { padding: 12px 10px 88px; }
  .form-grid { grid-template-columns: 1fr; }
  .table { min-width: 520px; }
  .mobile-nav { display: flex; }
}
"""

CLIENT_JS = """
const state = {
  routes: [],
  bookings: [],
  parcels: [],
};

const el = {
  routes: document.getElementById('routes-body'),
  status: document.getElementById('status'),
  bookings: document.getElementById('booking-list'),
  parcels: document.getElementById('parcel-list'),
  metrics: {
    routes: document.getElementById('m-routes'),
    seats: document.getElementById('m-seats'),
    bookings: document.getElementById('m-bookings'),
    parcels: document.getElementById('m-parcels'),
  },
  filterCity: document.getElementById('filter-city'),
  filterDriver: document.getElementById('filter-driver'),
};

function renderStatus(text, isError = false) {
  el.status.textContent = text;
  el.status.classList.toggle('error', isError);
}

function routeRow(route) {
  return `<tr>
    <td>${route.route_id}</td>
    <td>${route.departure_city} → ${route.arrival_city}</td>
    <td>${route.departure_time} - ${route.arrival_time}</td>
    <td>${route.driver_name}</td>
    <td>${route.available_seats}</td>
  </tr>`;
}

function renderRoutes() {
  const city = el.filterCity.value.trim().toLowerCase();
  const driver = el.filterDriver.value.trim().toLowerCase();
  const filtered = state.routes.filter(r => {
    const cityOk = !city || r.departure_city.toLowerCase().includes(city) || r.arrival_city.toLowerCase().includes(city);
    const driverOk = !driver || r.driver_name.toLowerCase().includes(driver);
    return cityOk && driverOk;
  });
  el.routes.innerHTML = filtered.map(routeRow).join('') || '<tr><td colspan="5">Ничего не найдено</td></tr>';

  const freeSeats = state.routes.reduce((acc, r) => acc + r.available_seats, 0);
  el.metrics.routes.textContent = state.routes.length;
  el.metrics.seats.textContent = freeSeats;
  el.metrics.bookings.textContent = state.bookings.length;
  el.metrics.parcels.textContent = state.parcels.length;
}

function renderItems() {
  el.bookings.innerHTML = state.bookings.length
    ? state.bookings.slice(-5).reverse().map(b => `<div class='item'>Бронь #${b.booking_id}: ${b.passenger_name}, рейс ${b.route_id}, мест ${b.seats}</div>`).join('')
    : '<div class="item">Пока нет бронирований</div>';

  el.parcels.innerHTML = state.parcels.length
    ? state.parcels.slice(-5).reverse().map(p => `<div class='item'>Передачка #${p.parcel_id}: ${p.sender_name} → ${p.recipient_name}, рейс ${p.route_id}</div>`).join('')
    : '<div class="item">Пока нет передачек</div>';
}

async function api(path, payload) {
  const res = await fetch(path, {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify(payload),
  });
  return await res.json();
}

async function refresh() {
  const res = await fetch('/api/state');
  const data = await res.json();
  state.routes = data.routes;
  state.bookings = data.bookings;
  state.parcels = data.parcels;
  renderRoutes();
  renderItems();
}

function bindForm(id, handler) {
  document.getElementById(id).addEventListener('submit', async (e) => {
    e.preventDefault();
    const form = e.currentTarget;
    const fd = new FormData(form);
    try {
      await handler(fd);
      await refresh();
    } catch (err) {
      renderStatus(`Ошибка: ${err.message}`, true);
    }
  });
}

bindForm('route-form', async (fd) => {
  const result = await api('/api/find-route', {
    departure_city: fd.get('departure_city'),
    arrival_city: fd.get('arrival_city'),
    earliest_departure: fd.get('earliest_departure') || null,
  });
  if (!result.ok) throw new Error(result.error);
  const ids = result.routes.map(r => r.route_id).join(' → ') || 'маршрут не найден';
  renderStatus(`Построено: ${ids}`);
});

bindForm('driver-form', async (fd) => {
  el.filterDriver.value = fd.get('driver_name');
  renderRoutes();
  renderStatus('Фильтр по водителю применён');
});

bindForm('city-form', async (fd) => {
  el.filterCity.value = fd.get('city');
  renderRoutes();
  renderStatus('Фильтр по городу применён');
});

bindForm('booking-form', async (fd) => {
  const result = await api('/api/book', {
    route_id: fd.get('route_id'),
    passenger_name: fd.get('passenger_name'),
    seats: Number(fd.get('seats')),
  });
  if (!result.ok) throw new Error(result.error);
  renderStatus(`Бронь #${result.booking.booking_id} создана`);
});

bindForm('parcel-form', async (fd) => {
  const result = await api('/api/parcel', {
    route_id: fd.get('route_id'),
    sender_name: fd.get('sender_name'),
    recipient_name: fd.get('recipient_name'),
    description: fd.get('description'),
  });
  if (!result.ok) throw new Error(result.error);
  renderStatus(`Передачка #${result.parcel.parcel_id} оформлена`);
});

let timer;
for (const input of [el.filterCity, el.filterDriver]) {
  input.addEventListener('input', () => {
    clearTimeout(timer);
    timer = setTimeout(renderRoutes, 80);
  });
}

document.getElementById('reset-filters').addEventListener('click', () => {
  el.filterCity.value = '';
  el.filterDriver.value = '';
  renderRoutes();
  renderStatus('Фильтры очищены');
});

if ('serviceWorker' in navigator) {
  navigator.serviceWorker.register('/service-worker.js').catch(() => null);
}

refresh();
"""


def segment_to_dict(segment: RouteSegment) -> Dict[str, object]:
    return {
        "route_id": segment.route_id,
        "departure_city": segment.departure_city,
        "arrival_city": segment.arrival_city,
        "departure_time": segment.departure_time,
        "arrival_time": segment.arrival_time,
        "driver_name": segment.driver_name,
        "available_seats": segment.available_seats,
    }


def render_page() -> str:
    return f"""<!doctype html>
<html lang='ru'>
<head>
  <meta charset='utf-8'>
  <meta name='viewport' content='width=device-width, initial-scale=1, viewport-fit=cover'>
  <meta name='theme-color' content='#4f7cff'>
  <meta name='apple-mobile-web-app-capable' content='yes'>
  <meta name='apple-mobile-web-app-title' content='Логистика'>
  <link rel='manifest' href='/manifest.webmanifest'>
  <title>Логистика перевозок</title>
  <style>{STYLE}</style>
</head>
<body>
<div class='container'>
  <section class='hero'>
    <h1>Премиум-диспетчерская перевозок</h1>
    <p>Красивый интерфейс + моментальный отклик: всё работает без перезагрузки страницы.</p>
    <div class='metrics'>
      <div class='metric'>Рейсов <b id='m-routes'>0</b></div>
      <div class='metric'>Свободных мест <b id='m-seats'>0</b></div>
      <div class='metric'>Бронирований <b id='m-bookings'>0</b></div>
      <div class='metric'>Передачек <b id='m-parcels'>0</b></div>
    </div>
  </section>

  <section class='layout'>
    <div id='dashboard' class='card'>
      <h2>Рейсы в реальном времени</h2>
      <div class='controls'>
        <input id='filter-city' class='input' placeholder='Фильтр по городу'>
        <input id='filter-driver' class='input' placeholder='Фильтр по водителю'>
        <button id='reset-filters' type='button' class='ghost'>Сбросить</button>
      </div>
      <div class='table-wrap'>
        <table class='table'>
          <thead><tr><th>ID</th><th>Маршрут</th><th>Время</th><th>Водитель</th><th>Мест</th></tr></thead>
          <tbody id='routes-body'><tr><td colspan='5'>Загрузка...</td></tr></tbody>
        </table>
      </div>
      <div id='status' class='status'>Готово к работе</div>
      <div class='form-grid' style='margin-top:10px'>
        <div>
          <h2>Последние брони</h2>
          <div id='booking-list' class='list'></div>
        </div>
        <div>
          <h2>Последние передачки</h2>
          <div id='parcel-list' class='list'></div>
        </div>
      </div>
    </div>

    <div id='actions' class='card'>
      <h2>Операции</h2>
      <div class='forms'>
        <form id='route-form' class='form'>
          <b>Построить маршрут</b>
          <input name='departure_city' class='input' placeholder='Откуда' required>
          <input name='arrival_city' class='input' placeholder='Куда' required>
          <input name='earliest_departure' class='input' placeholder='Не раньше (HH:MM)'>
          <button>Построить</button>
        </form>

        <form id='driver-form' class='form'>
          <b>Показать рейсы водителя</b>
          <input name='driver_name' class='input' placeholder='Имя водителя' required>
          <button>Применить</button>
        </form>

        <form id='city-form' class='form'>
          <b>Показать рейсы по городу</b>
          <input name='city' class='input' placeholder='Город' required>
          <button>Применить</button>
        </form>

        <form id='booking-form' class='form'>
          <b>Забронировать место</b>
          <input name='route_id' class='input' placeholder='ID маршрута' required>
          <input name='passenger_name' class='input' placeholder='ФИО пассажира' required>
          <input name='seats' type='number' min='1' class='input' placeholder='Количество мест' required>
          <button>Создать бронь</button>
        </form>

        <form id='parcel-form' class='form'>
          <b>Оформить передачку</b>
          <input name='route_id' class='input' placeholder='ID маршрута' required>
          <input name='sender_name' class='input' placeholder='Отправитель' required>
          <input name='recipient_name' class='input' placeholder='Получатель' required>
          <input name='description' class='input' placeholder='Описание' required>
          <button>Оформить</button>
        </form>
      </div>
    </div>
  </section>
</div>

<nav class='mobile-nav'>
  <a href='#dashboard'>Дашборд</a>
  <a href='#actions'>Операции</a>
</nav>

<script>{CLIENT_JS}</script>
</body>
</html>"""


class LogisticsHandler(BaseHTTPRequestHandler):
    def _send(self, status: int, body: str, content_type: str) -> None:
        data = body.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _send_json(self, payload: Dict[str, object], status: int = 200) -> None:
        self._send(status, json.dumps(payload, ensure_ascii=False), "application/json; charset=utf-8")

    def _read_json(self) -> Dict[str, object]:
        length = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(length).decode("utf-8")
        return json.loads(raw or "{}")

    def _state_payload(self) -> Dict[str, object]:
        return {
            "routes": [segment_to_dict(s) for s in service.segments.values()],
            "bookings": [vars(b) for b in service.bookings.values()],
            "parcels": [vars(p) for p in service.parcels.values()],
        }

    def do_GET(self) -> None:  # noqa: N802
        path = urlparse(self.path).path
        if path == "/manifest.webmanifest":
            self._send_json(MANIFEST_JSON)
            return
        if path == "/service-worker.js":
            self._send(200, SERVICE_WORKER_JS, "application/javascript; charset=utf-8")
            return
        if path == "/api/state":
            self._send_json(self._state_payload())
            return
        self._send(200, render_page(), "text/html; charset=utf-8")

    def do_POST(self) -> None:  # noqa: N802
        path = urlparse(self.path).path

        try:
            if path.startswith("/api/"):
                data = self._read_json()
                if path == "/api/find-route":
                    routes = service.find_route_sequence(
                        str(data.get("departure_city", "")),
                        str(data.get("arrival_city", "")),
                        str(data.get("earliest_departure", "") or "") or None,
                    )
                    self._send_json({"ok": True, "routes": [segment_to_dict(s) for s in routes]})
                    return

                if path == "/api/book":
                    booking = service.book_seats(
                        str(data.get("route_id", "")),
                        str(data.get("passenger_name", "")),
                        int(data.get("seats", 0)),
                    )
                    self._send_json({"ok": True, "booking": vars(booking)})
                    return

                if path == "/api/parcel":
                    parcel = service.register_parcel(
                        str(data.get("route_id", "")),
                        str(data.get("sender_name", "")),
                        str(data.get("recipient_name", "")),
                        str(data.get("description", "")),
                    )
                    self._send_json({"ok": True, "parcel": vars(parcel)})
                    return

                self._send_json({"ok": False, "error": "Неизвестный endpoint"}, status=404)
                return

            # Backward-compatible form handler
            length = int(self.headers.get("Content-Length", "0"))
            raw = self.rfile.read(length).decode("utf-8")
            data = {k: v[0] for k, v in parse_qs(raw).items()}
            action = data.get("action", "")

            if action == "book":
                service.book_seats(data.get("route_id", ""), data.get("passenger_name", ""), int(data.get("seats", "0")))
            if action == "parcel":
                service.register_parcel(
                    data.get("route_id", ""),
                    data.get("sender_name", ""),
                    data.get("recipient_name", ""),
                    data.get("description", ""),
                )
            self._send(200, render_page(), "text/html; charset=utf-8")
        except (ValueError, json.JSONDecodeError) as exc:
            if path.startswith("/api/"):
                self._send_json({"ok": False, "error": str(exc)}, status=400)
                return
            self._send(400, f"Ошибка: {exc}", "text/plain; charset=utf-8")


def run() -> None:
    host, port = "0.0.0.0", 8080
    server = HTTPServer((host, port), LogisticsHandler)
    print(f"Сервер запущен: http://{host}:{port}")
    server.serve_forever()


if __name__ == "__main__":
    run()
