from __future__ import annotations

import json
from datetime import datetime
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
  --surface: rgba(255,255,255,.08);
  --surface-strong: rgba(255,255,255,.14);
  --text: #f5f7ff;
  --muted: #b8c4ea;
  --primary: #4f7cff;
  --primary-2: #58d6ff;
  --danger: #fb7185;
  --line: rgba(255,255,255,.16);
}
* { box-sizing: border-box; }
html, body { margin: 0; padding: 0; font-family: Inter, -apple-system, BlinkMacSystemFont, Segoe UI, sans-serif; background: radial-gradient(circle at 0% 0%, #1d2a52, #0b1020 50%); color: var(--text); }
.container { max-width: 1280px; margin: 0 auto; padding: 16px 14px 80px; }
.hero { background: linear-gradient(130deg, rgba(79,124,255,.35), rgba(88,214,255,.12)); border: 1px solid var(--line); border-radius: 18px; padding: 20px; }
.hero h1 { margin: 0; font-size: clamp(24px, 5vw, 38px); }
.hero p { margin: 8px 0 0; color: var(--muted); }
.metrics { margin-top: 14px; display: grid; grid-template-columns: repeat(auto-fit, minmax(160px, 1fr)); gap: 10px; }
.metric { padding: 10px; border-radius: 12px; border: 1px solid var(--line); background: var(--surface); }
.metric b { display: block; margin-top: 4px; font-size: 24px; }
.card { background: var(--surface); border: 1px solid var(--line); border-radius: 16px; padding: 14px; backdrop-filter: blur(8px); }
.layout { margin-top: 12px; display: grid; grid-template-columns: 1.15fr .85fr; gap: 12px; }
section h2 { margin: 0 0 10px; font-size: 18px; }
.input, button, select { width: 100%; padding: 11px 12px; font-size: 15px; border-radius: 10px; border: 1px solid var(--line); color: var(--text); background: rgba(0,0,0,.25); }
.input::placeholder { color: #98a8dc; }
button { cursor: pointer; border: none; font-weight: 700; background: linear-gradient(120deg, var(--primary), var(--primary-2)); }
button.ghost { background: rgba(255,255,255,.08); border: 1px solid var(--line); }
.toolbar { display: flex; gap: 8px; margin-bottom: 10px; }
.table-wrap { max-height: 390px; overflow: auto; border: 1px solid var(--line); border-radius: 10px; }
.table { width: 100%; border-collapse: collapse; min-width: 630px; font-size: 14px; }
.table th, .table td { border-bottom: 1px solid rgba(255,255,255,.1); text-align: left; padding: 8px; }
.table th { position: sticky; top: 0; background: #111a35; }
.status { margin-top: 10px; border: 1px solid rgba(79,124,255,.55); background: rgba(79,124,255,.18); border-radius: 10px; padding: 10px; }
.status.error { border-color: rgba(251,113,133,.55); background: rgba(251,113,133,.15); }
.tabs { display: flex; gap: 8px; margin-bottom: 10px; }
.tab-btn { border: 1px solid var(--line); background: rgba(255,255,255,.06); color: var(--text); border-radius: 999px; padding: 8px 12px; font-size: 13px; cursor: pointer; }
.tab-btn.active { background: linear-gradient(120deg, var(--primary), var(--primary-2)); border-color: transparent; }
.panel { display: none; }
.panel.active { display: block; }
.forms { display: grid; gap: 10px; }
.form { display: grid; gap: 8px; border: 1px solid rgba(255,255,255,.1); background: rgba(0,0,0,.2); border-radius: 12px; padding: 11px; }
.form b { font-size: 14px; }
.split { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; }
.chips { display: flex; flex-wrap: wrap; gap: 6px; margin-top: 8px; }
.chip { border: 1px solid var(--line); padding: 5px 9px; border-radius: 999px; font-size: 12px; cursor: pointer; background: rgba(255,255,255,.07); }
.timeline { display: grid; gap: 8px; margin-top: 10px; }
.step { border-left: 2px solid #5d85ff; padding: 8px 10px; border-radius: 8px; background: rgba(255,255,255,.06); }
.muted { color: var(--muted); font-size: 13px; }
.list { display: grid; gap: 8px; margin-top: 10px; }
.item { border: 1px solid rgba(255,255,255,.12); border-radius: 10px; background: rgba(255,255,255,.05); padding: 8px; font-size: 13px; }
.mobile-nav { display: none; position: fixed; left: 10px; right: 10px; bottom: 10px; border: 1px solid var(--line); background: rgba(16,24,44,.93); border-radius: 12px; padding: 6px; gap: 6px; }
.mobile-nav a { flex: 1; text-align: center; text-decoration: none; color: var(--text); font-size: 12px; background: rgba(255,255,255,.08); padding: 8px 6px; border-radius: 8px; }
@media (max-width: 980px) { .layout { grid-template-columns: 1fr; } }
@media (max-width: 760px) {
  .container { padding: 12px 10px 88px; }
  .toolbar, .split { grid-template-columns: 1fr; display: grid; }
  .table { min-width: 520px; }
  .mobile-nav { display: flex; }
}
"""

CLIENT_JS = """
const state = { routes: [], bookings: [], parcels: [], recentSearches: JSON.parse(localStorage.getItem('recent-searches') || '[]') };

const el = {
  routes: document.getElementById('routes-body'),
  status: document.getElementById('status'),
  timeline: document.getElementById('timeline'),
  departures: document.getElementById('departures-list'),
  recents: document.getElementById('recent-searches'),
  favorites: document.getElementById('favorite-routes'),
  metrics: {
    routes: document.getElementById('m-routes'),
    seats: document.getElementById('m-seats'),
    bookings: document.getElementById('m-bookings'),
    parcels: document.getElementById('m-parcels'),
  },
  filterCity: document.getElementById('filter-city'),
  filterDriver: document.getElementById('filter-driver'),
  departuresCity: document.getElementById('departures-city'),
};

const tabs = document.querySelectorAll('.tab-btn');
const panels = document.querySelectorAll('.panel');

tabs.forEach(btn => btn.addEventListener('click', () => {
  tabs.forEach(x => x.classList.remove('active'));
  panels.forEach(x => x.classList.remove('active'));
  btn.classList.add('active');
  document.getElementById(btn.dataset.target).classList.add('active');
}));

function setStatus(msg, isError = false) {
  el.status.textContent = msg;
  el.status.classList.toggle('error', isError);
}

function routeRow(route) {
  return `<tr><td>${route.route_id}</td><td>${route.departure_city} → ${route.arrival_city}</td><td>${route.departure_time} - ${route.arrival_time}</td><td>${route.driver_name}</td><td>${route.available_seats}</td></tr>`;
}

function saveRecent(entry) {
  const compact = `${entry.from}→${entry.to} (${entry.time || 'любой'})`;
  state.recentSearches = [compact, ...state.recentSearches.filter(x => x !== compact)].slice(0, 6);
  localStorage.setItem('recent-searches', JSON.stringify(state.recentSearches));
  renderRecents();
}

function renderRecents() {
  el.recents.innerHTML = state.recentSearches.length
    ? state.recentSearches.map(x => `<div class='item'>${x}</div>`).join('')
    : "<div class='item'>История поиска пока пуста</div>";
}

function renderFavorites() {
  const grouped = {};
  state.routes.forEach(r => {
    const key = `${r.departure_city} → ${r.arrival_city}`;
    grouped[key] = (grouped[key] || 0) + 1;
  });
  const top = Object.entries(grouped).sort((a,b) => b[1]-a[1]).slice(0, 5);
  el.favorites.innerHTML = top.length
    ? top.map(([name,count]) => `<div class='item'>${name} <span class='muted'>• рейсов: ${count}</span></div>`).join('')
    : "<div class='item'>Нет данных</div>";
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
  renderFavorites();
}

function buildTimeline(segments) {
  if (!segments.length) {
    el.timeline.innerHTML = "<div class='item'>Маршрут не найден</div>";
    return;
  }
  let html = "";
  for (let i = 0; i < segments.length; i++) {
    const s = segments[i];
    html += `<div class='step'><b>${s.departure_city} (${s.departure_time}) → ${s.arrival_city} (${s.arrival_time})</b><div class='muted'>Рейс ${s.route_id}, водитель ${s.driver_name}</div>`;
    if (i < segments.length - 1) {
      const wait = segments[i + 1].wait_minutes;
      html += `<div class='muted'>Пересадка: ${wait} мин</div>`;
    }
    html += "</div>";
  }
  el.timeline.innerHTML = html;
}

async function loadDepartures() {
  const city = el.departuresCity.value.trim();
  const result = await api('/api/departures', { city, limit: 8 });
  if (!result.ok) {
    setStatus(`Ошибка: ${result.error}`, true);
    return;
  }
  el.departures.innerHTML = result.departures.length
    ? result.departures.map(d => `<div class='item'><b>${d.departure_time}</b> · ${d.departure_city} → ${d.arrival_city}<br><span class='muted'>${d.driver_name}, мест: ${d.available_seats}</span></div>`).join('')
    : "<div class='item'>Нет отправлений</div>";
  setStatus(`Табло обновлено для города: ${city || 'все'}`);
}

function bindSubmit(id, handler) {
  document.getElementById(id).addEventListener('submit', async (e) => {
    e.preventDefault();
    const fd = new FormData(e.currentTarget);
    try {
      await handler(fd);
      await refresh();
    } catch (err) {
      setStatus(`Ошибка: ${err.message}`, true);
    }
  });
}

bindSubmit('route-form', async (fd) => {
  const payload = {
    departure_city: fd.get('departure_city'),
    arrival_city: fd.get('arrival_city'),
    earliest_departure: fd.get('earliest_departure') || null,
  };
  const result = await api('/api/navigation-guide', payload);
  if (!result.ok) throw new Error(result.error);
  buildTimeline(result.guide.segments);
  saveRecent({ from: payload.departure_city, to: payload.arrival_city, time: payload.earliest_departure });
  setStatus(`Навигация построена: ${result.guide.total_duration_minutes} мин, пересадок ${result.guide.transfers_count}`);
});

bindSubmit('driver-form', async (fd) => {
  el.filterDriver.value = fd.get('driver_name');
  renderRoutes();
  setStatus('Фильтр по водителю применён');
});

bindSubmit('city-form', async (fd) => {
  el.filterCity.value = fd.get('city');
  renderRoutes();
  setStatus('Фильтр по городу применён');
});

bindSubmit('booking-form', async (fd) => {
  const result = await api('/api/book', {
    route_id: fd.get('route_id'),
    passenger_name: fd.get('passenger_name'),
    seats: Number(fd.get('seats')),
  });
  if (!result.ok) throw new Error(result.error);
  setStatus(`Бронь #${result.booking.booking_id} создана`);
});

bindSubmit('parcel-form', async (fd) => {
  const result = await api('/api/parcel', {
    route_id: fd.get('route_id'),
    sender_name: fd.get('sender_name'),
    recipient_name: fd.get('recipient_name'),
    description: fd.get('description'),
  });
  if (!result.ok) throw new Error(result.error);
  setStatus(`Передачка #${result.parcel.parcel_id} оформлена`);
});

let timer;
for (const input of [el.filterCity, el.filterDriver]) {
  input.addEventListener('input', () => {
    clearTimeout(timer);
    timer = setTimeout(renderRoutes, 70);
  });
}

for (const chip of document.querySelectorAll('.chip')) {
  chip.addEventListener('click', () => {
    const city = chip.dataset.city;
    el.filterCity.value = city;
    el.departuresCity.value = city;
    renderRoutes();
    loadDepartures();
  });
}

document.getElementById('departures-refresh').addEventListener('click', loadDepartures);
document.getElementById('reset-filters').addEventListener('click', () => {
  el.filterCity.value = '';
  el.filterDriver.value = '';
  renderRoutes();
  setStatus('Фильтры очищены');
});

if ('serviceWorker' in navigator) {
  navigator.serviceWorker.register('/service-worker.js').catch(() => null);
}

renderRecents();
refresh();
loadDepartures();
"""


def parse_clock(value: str) -> datetime:
    return datetime.strptime(value, "%H:%M")


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


def build_navigation_guide(segments: List[RouteSegment]) -> Dict[str, object]:
    if not segments:
        return {"segments": [], "total_duration_minutes": 0, "transfers_count": 0}

    normalized_segments: List[Dict[str, object]] = []
    for index, segment in enumerate(segments):
        wait_minutes = 0
        if index < len(segments) - 1:
            next_departure = parse_clock(segments[index + 1].departure_time)
            arrival = parse_clock(segment.arrival_time)
            wait_minutes = int((next_departure - arrival).total_seconds() // 60)

        payload = segment_to_dict(segment)
        payload["wait_minutes"] = wait_minutes
        normalized_segments.append(payload)

    trip_start = parse_clock(segments[0].departure_time)
    trip_end = parse_clock(segments[-1].arrival_time)
    total_duration = int((trip_end - trip_start).total_seconds() // 60)

    return {
        "segments": normalized_segments,
        "total_duration_minutes": max(total_duration, 0),
        "transfers_count": max(len(segments) - 1, 0),
    }


def get_departures(city: str, limit: int = 8) -> List[Dict[str, object]]:
    city_normalized = city.strip().lower()
    items = []
    for segment in service.segments.values():
        if city_normalized and segment.departure_city.lower() != city_normalized:
            continue
        items.append(segment)

    items = sorted(items, key=lambda x: parse_clock(x.departure_time))[: max(limit, 1)]
    return [segment_to_dict(item) for item in items]


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
    <h1>Навигационный центр перевозок</h1>
    <p>Продвинутая навигация: смарт-маршруты с пересадками, табло отправлений, избранные направления и история поиска.</p>
    <div class='metrics'>
      <div class='metric'>Рейсов <b id='m-routes'>0</b></div>
      <div class='metric'>Свободных мест <b id='m-seats'>0</b></div>
      <div class='metric'>Бронирований <b id='m-bookings'>0</b></div>
      <div class='metric'>Передачек <b id='m-parcels'>0</b></div>
    </div>
  </section>

  <section class='layout'>
    <div id='dashboard' class='card'>
      <h2>Центральная навигация</h2>
      <div class='tabs'>
        <button class='tab-btn active' data-target='tab-routes' type='button'>Рейсы</button>
        <button class='tab-btn' data-target='tab-guide' type='button'>Смарт-маршрут</button>
        <button class='tab-btn' data-target='tab-board' type='button'>Табло отправлений</button>
      </div>

      <div id='tab-routes' class='panel active'>
        <div class='toolbar'>
          <input id='filter-city' class='input' placeholder='Фильтр по городу'>
          <input id='filter-driver' class='input' placeholder='Фильтр по водителю'>
          <button id='reset-filters' type='button' class='ghost'>Сбросить</button>
        </div>
        <div class='chips'>
          <span class='chip' data-city='Алматы'>Алматы</span>
          <span class='chip' data-city='Караганда'>Караганда</span>
          <span class='chip' data-city='Астана'>Астана</span>
          <span class='chip' data-city='Тараз'>Тараз</span>
          <span class='chip' data-city='Шымкент'>Шымкент</span>
        </div>
        <div class='table-wrap'>
          <table class='table'>
            <thead><tr><th>ID</th><th>Маршрут</th><th>Время</th><th>Водитель</th><th>Мест</th></tr></thead>
            <tbody id='routes-body'><tr><td colspan='5'>Загрузка...</td></tr></tbody>
          </table>
        </div>
      </div>

      <div id='tab-guide' class='panel'>
        <div class='muted'>Пошаговая навигация по цепочке сегментов с учётом пересадок:</div>
        <div id='timeline' class='timeline'><div class='item'>Постройте маршрут справа, чтобы увидеть детали.</div></div>
      </div>

      <div id='tab-board' class='panel'>
        <div class='toolbar'>
          <input id='departures-city' class='input' placeholder='Город отправления (например, Алматы)'>
          <button id='departures-refresh' type='button'>Обновить табло</button>
        </div>
        <div id='departures-list' class='list'></div>
      </div>

      <div id='status' class='status'>Готово к работе</div>
      <div class='split' style='margin-top:10px'>
        <div>
          <h2>История поиска</h2>
          <div id='recent-searches' class='list'></div>
        </div>
        <div>
          <h2>Избранные направления</h2>
          <div id='favorite-routes' class='list'></div>
        </div>
      </div>
    </div>

    <div id='actions' class='card'>
      <h2>Операции</h2>
      <div class='forms'>
        <form id='route-form' class='form'>
          <b>Смарт-построение маршрута</b>
          <input name='departure_city' class='input' placeholder='Откуда' required>
          <input name='arrival_city' class='input' placeholder='Куда' required>
          <input name='earliest_departure' class='input' placeholder='Не раньше (HH:MM)'>
          <button>Построить навигацию</button>
        </form>

        <form id='driver-form' class='form'>
          <b>Навигация по водителю</b>
          <input name='driver_name' class='input' placeholder='Имя водителя' required>
          <button>Применить фильтр</button>
        </form>

        <form id='city-form' class='form'>
          <b>Навигация по городу</b>
          <input name='city' class='input' placeholder='Город' required>
          <button>Применить фильтр</button>
        </form>

        <form id='booking-form' class='form'>
          <b>Бронирование</b>
          <input name='route_id' class='input' placeholder='ID маршрута' required>
          <input name='passenger_name' class='input' placeholder='ФИО пассажира' required>
          <input name='seats' class='input' type='number' min='1' placeholder='Количество мест' required>
          <button>Создать бронь</button>
        </form>

        <form id='parcel-form' class='form'>
          <b>Передачка</b>
          <input name='route_id' class='input' placeholder='ID маршрута' required>
          <input name='sender_name' class='input' placeholder='Отправитель' required>
          <input name='recipient_name' class='input' placeholder='Получатель' required>
          <input name='description' class='input' placeholder='Описание' required>
          <button>Оформить передачку</button>
        </form>
      </div>
    </div>
  </section>
</div>

<nav class='mobile-nav'>
  <a href='#dashboard'>Навигация</a>
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
                if path == "/api/navigation-guide":
                    route = service.find_route_sequence(
                        str(data.get("departure_city", "")),
                        str(data.get("arrival_city", "")),
                        str(data.get("earliest_departure", "") or "") or None,
                    )
                    self._send_json({"ok": True, "guide": build_navigation_guide(route)})
                    return

                if path == "/api/find-route":
                    route = service.find_route_sequence(
                        str(data.get("departure_city", "")),
                        str(data.get("arrival_city", "")),
                        str(data.get("earliest_departure", "") or "") or None,
                    )
                    self._send_json({"ok": True, "routes": [segment_to_dict(item) for item in route]})
                    return

                if path == "/api/departures":
                    departures = get_departures(str(data.get("city", "")), int(data.get("limit", 8)))
                    self._send_json({"ok": True, "departures": departures})
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
