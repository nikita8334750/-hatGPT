from __future__ import annotations

import json
from datetime import datetime
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Any, Callable, Dict, List, Optional
from urllib.parse import parse_qs, urlparse

from logistics import Booking, LogisticsService, ParcelOrder, RouteSegment, SAMPLE_SEGMENTS


class SelfHealingLogistics:
    """Обёртка над сервисом с авто-восстановлением после ошибок."""

    def __init__(self, seed_segments: List[RouteSegment]) -> None:
        self.seed_segments = seed_segments
        self.service = LogisticsService(self._clone_seed_segments())
        self.heal_count = 0
        self.errors_count = 0
        self.last_error = ""
        self.events: List[Dict[str, Any]] = []

    def _clone_seed_segments(self) -> List[RouteSegment]:
        return [
            RouteSegment(
                segment.route_id,
                segment.departure_city,
                segment.arrival_city,
                segment.departure_time,
                segment.arrival_time,
                segment.capacity,
                segment.driver_name,
            )
            for segment in self.seed_segments
        ]

    def _replay_events(self) -> None:
        for event in self.events:
            try:
                if event["type"] == "booking":
                    self.service.book_seats(event["route_id"], event["passenger_name"], event["seats"])
                if event["type"] == "parcel":
                    self.service.register_parcel(
                        event["route_id"],
                        event["sender_name"],
                        event["recipient_name"],
                        event["description"],
                    )
                if event["type"] == "cancel_booking":
                    self.service.cancel_booking(event["booking_id"])
                if event["type"] == "cancel_parcel":
                    self.service.cancel_parcel(event["parcel_id"])
                if event["type"] == "upsert_route":
                    route = RouteSegment(
                        event["route_id"],
                        event["departure_city"],
                        event["arrival_city"],
                        event["departure_time"],
                        event["arrival_time"],
                        int(event["capacity"]),
                        event["driver_name"],
                    )
                    self.service.upsert_route(route)
                if event["type"] == "delete_route":
                    self.service.delete_route(event["route_id"])
            except ValueError:
                continue

    def heal(self, reason: str) -> None:
        self.heal_count += 1
        self.last_error = reason
        self.service = LogisticsService(self._clone_seed_segments())
        self._replay_events()

    def run(self, operation: Callable[[LogisticsService], Any], label: str = "operation") -> Any:
        try:
            return operation(self.service)
        except Exception as exc:
            self.errors_count += 1
            self.heal(f"{label}: {exc}")
            return operation(self.service)

    def record_booking(self, booking: Booking) -> None:
        self.events.append(
            {
                "type": "booking",
                "route_id": booking.route_id,
                "passenger_name": booking.passenger_name,
                "seats": booking.seats,
            }
        )

    def record_event(self, payload: Dict[str, Any]) -> None:
        self.events.append(payload)

    def record_parcel(self, parcel: ParcelOrder) -> None:
        self.events.append(
            {
                "type": "parcel",
                "route_id": parcel.route_id,
                "sender_name": parcel.sender_name,
                "recipient_name": parcel.recipient_name,
                "description": parcel.description,
            }
        )

    def health_payload(self) -> Dict[str, Any]:
        return {
            "healing": {
                "heal_count": self.heal_count,
                "errors_count": self.errors_count,
                "last_error": self.last_error,
                "replayed_events": len(self.events),
            }
        }


service_manager = SelfHealingLogistics(SAMPLE_SEGMENTS)
CONTACT_REQUESTS: List[Dict[str, str]] = []

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
  --bg: #0b1020; --surface: rgba(255,255,255,.08); --surface-strong: rgba(255,255,255,.14);
  --text: #f5f7ff; --muted: #b8c4ea; --primary: #4f7cff; --primary-2: #58d6ff;
  --danger: #fb7185; --line: rgba(255,255,255,.16);
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
.site-nav { display:flex; gap:10px; flex-wrap:wrap; margin-top:12px; }
.site-nav a { color: var(--text); text-decoration:none; padding:7px 11px; border:1px solid var(--line); border-radius:999px; background: rgba(255,255,255,.06); font-size:13px; }
.enterprise-grid { display:grid; grid-template-columns: repeat(auto-fit, minmax(220px,1fr)); gap:10px; margin-top:10px; }
.enterprise-card { border:1px solid var(--line); background: rgba(255,255,255,.06); border-radius:12px; padding:12px; }
.enterprise-card h3 { margin:0 0 6px; font-size:15px; }
.faq details { border:1px solid var(--line); border-radius:10px; padding:10px; background: rgba(255,255,255,.05); margin-bottom:8px; }
.footer { margin-top:14px; border:1px solid var(--line); border-radius:12px; padding:12px; color: var(--muted); font-size:13px; }
.hero-visual { margin-top: 14px; border-radius: 14px; overflow: hidden; border: 1px solid var(--line); max-height: 260px; }
.hero-visual img { width: 100%; height: 260px; object-fit: cover; display: block; }
.photo-grid { margin-top: 12px; display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 10px; }
.photo-card { border: 1px solid var(--line); border-radius: 12px; overflow: hidden; background: rgba(255,255,255,.06); }
.photo-card img { width: 100%; height: 130px; object-fit: cover; display: block; }
.photo-card p { margin: 8px; font-size: 12px; color: var(--muted); }
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
  routes: document.getElementById('routes-body'), status: document.getElementById('status'),
  timeline: document.getElementById('timeline'), departures: document.getElementById('departures-list'),
  recents: document.getElementById('recent-searches'), favorites: document.getElementById('favorite-routes'),
  healing: document.getElementById('healing-state'),
  metrics: { routes: document.getElementById('m-routes'), seats: document.getElementById('m-seats'), bookings: document.getElementById('m-bookings'), parcels: document.getElementById('m-parcels') },
  filterCity: document.getElementById('filter-city'), filterDriver: document.getElementById('filter-driver'), departuresCity: document.getElementById('departures-city')
};

const tabs = document.querySelectorAll('.tab-btn');
const panels = document.querySelectorAll('.panel');
for (const btn of tabs) { btn.addEventListener('click', () => { tabs.forEach(x => x.classList.remove('active')); panels.forEach(x => x.classList.remove('active')); btn.classList.add('active'); document.getElementById(btn.dataset.target).classList.add('active'); }); }

function setStatus(msg, isError = false) { el.status.textContent = msg; el.status.classList.toggle('error', isError); }
  metrics: { routes: document.getElementById('m-routes'), seats: document.getElementById('m-seats'), bookings: document.getElementById('m-bookings'), parcels: document.getElementById('m-parcels'), load: document.getElementById('m-load'), conversion: document.getElementById('m-conversion') },

function saveRecent(entry) {
  const compact = `${entry.from}→${entry.to} (${entry.time || 'любой'})`;
  state.recentSearches = [compact, ...state.recentSearches.filter(x => x !== compact)].slice(0, 6);
  localStorage.setItem('recent-searches', JSON.stringify(state.recentSearches));
  renderRecents();
}

function renderRecents() {
  el.recents.innerHTML = state.recentSearches.length ? state.recentSearches.map(x => `<div class='item'>${x}</div>`).join('') : "<div class='item'>История поиска пока пуста</div>";
}

function renderFavorites() {
  const grouped = {};
  state.routes.forEach(r => { const k = `${r.departure_city} → ${r.arrival_city}`; grouped[k] = (grouped[k] || 0) + 1; });
  const top = Object.entries(grouped).sort((a, b) => b[1] - a[1]).slice(0, 5);
  el.favorites.innerHTML = top.length ? top.map(([name, count]) => `<div class='item'>${name} <span class='muted'>• рейсов: ${count}</span></div>`).join('') : "<div class='item'>Нет данных</div>";
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
  el.metrics.routes.textContent = state.routes.length;
  el.metrics.seats.textContent = state.routes.reduce((acc, r) => acc + r.available_seats, 0);
  el.metrics.bookings.textContent = state.bookings.length;
  el.metrics.parcels.textContent = state.parcels.length;
}

async function api(path, payload) {
  const res = await fetch(path, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) });
  return await res.json();
}

async function refresh() {
  const stateRes = await fetch('/api/state');
  const data = await stateRes.json();
  state.routes = data.routes;
  state.bookings = data.bookings;
  state.parcels = data.parcels;
  renderRoutes();
  renderFavorites();

  const healthRes = await fetch('/api/health');
  const health = await healthRes.json();
  el.healing.textContent = `Автовосстановление: ${health.healing.heal_count}, ошибок: ${health.healing.errors_count}`;
}

function buildTimeline(segments) {
  if (!segments.length) { el.timeline.innerHTML = "<div class='item'>Маршрут не найден</div>"; return; }
  let html = '';
  for (let i = 0; i < segments.length; i++) {
    const s = segments[i];
    html += `<div class='step'><b>${s.departure_city} (${s.departure_time}) → ${s.arrival_city} (${s.arrival_time})</b><div class='muted'>Рейс ${s.route_id}, водитель ${s.driver_name}</div>`;
    if (i < segments.length - 1) html += `<div class='muted'>Пересадка: ${segments[i].wait_minutes} мин</div>`;
    html += '</div>';
  }
  el.timeline.innerHTML = html;
}

async function loadDepartures() {
  const city = el.departuresCity.value.trim();
  const result = await api('/api/departures', { city, limit: 8 });
  if (!result.ok) { setStatus(`Ошибка: ${result.error}`, true); return; }
  el.departures.innerHTML = result.departures.length ? result.departures.map(d => `<div class='item'><b>${d.departure_time}</b> · ${d.departure_city} → ${d.arrival_city}<br><span class='muted'>${d.driver_name}, мест: ${d.available_seats}</span></div>`).join('') : "<div class='item'>Нет отправлений</div>";
}

function bindSubmit(id, handler) {
  document.getElementById(id).addEventListener('submit', async (e) => {
    e.preventDefault();
    const fd = new FormData(e.currentTarget);
    try { await handler(fd); await refresh(); } catch (err) { setStatus(`Ошибка: ${err.message}`, true); }
  });
}

bindSubmit('route-form', async (fd) => {

  const analyticsRes = await fetch('/api/analytics');
  const analytics = await analyticsRes.json();
  el.metrics.load.textContent = `${analytics.load_factor_percent}%`;
  el.metrics.conversion.textContent = `${analytics.conversion_percent}%`;
  const payload = { departure_city: fd.get('departure_city'), arrival_city: fd.get('arrival_city'), earliest_departure: fd.get('earliest_departure') || null };
  const result = await api('/api/navigation-guide', payload);
  if (!result.ok) throw new Error(result.error);
  buildTimeline(result.guide.segments);
  saveRecent({ from: payload.departure_city, to: payload.arrival_city, time: payload.earliest_departure });
  setStatus(`Навигация построена: ${result.guide.total_duration_minutes} мин`);
});

bindSubmit('driver-form', async (fd) => { el.filterDriver.value = fd.get('driver_name'); renderRoutes(); setStatus('Фильтр по водителю применён'); });
bindSubmit('city-form', async (fd) => { el.filterCity.value = fd.get('city'); renderRoutes(); setStatus('Фильтр по городу применён'); });
bindSubmit('booking-form', async (fd) => {
  const result = await api('/api/book', { route_id: fd.get('route_id'), passenger_name: fd.get('passenger_name'), seats: Number(fd.get('seats')) });
  if (!result.ok) throw new Error(result.error);
  setStatus(`Бронь #${result.booking.booking_id} создана`);
});
bindSubmit('parcel-form', async (fd) => {
  const result = await api('/api/parcel', { route_id: fd.get('route_id'), sender_name: fd.get('sender_name'), recipient_name: fd.get('recipient_name'), description: fd.get('description') });
  if (!result.ok) throw new Error(result.error);
  setStatus(`Передачка #${result.parcel.parcel_id} оформлена`);
});

document.getElementById('departures-refresh').addEventListener('click', loadDepartures);
document.getElementById('heal-now').addEventListener('click', async () => { await api('/api/heal', {reason: 'manual'}); setStatus('Система самовосстановления запущена вручную'); await refresh(); });
document.getElementById('reset-filters').addEventListener('click', () => { el.filterCity.value = ''; el.filterDriver.value = ''; renderRoutes(); });

for (const chip of document.querySelectorAll('.chip')) {
  chip.addEventListener('click', () => { const city = chip.dataset.city; el.filterCity.value = city; el.departuresCity.value = city; renderRoutes(); loadDepartures(); });
}

let timer;
for (const input of [el.filterCity, el.filterDriver]) {
  input.addEventListener('input', () => { clearTimeout(timer); timer = setTimeout(renderRoutes, 70); });
}

if ('serviceWorker' in navigator) navigator.serviceWorker.register('/service-worker.js').catch(() => null);
renderRecents(); refresh(); loadDepartures();
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
bindSubmit('cancel-booking-form', async (fd) => {
  const result = await api('/api/booking/cancel', { booking_id: Number(fd.get('booking_id')) });
  if (!result.ok) throw new Error(result.error);
  setStatus('Бронь отменена и места восстановлены');
});

bindSubmit('cancel-parcel-form', async (fd) => {
  const result = await api('/api/parcel/cancel', { parcel_id: Number(fd.get('parcel_id')) });
  if (!result.ok) throw new Error(result.error);
  setStatus('Передачка отменена');
});

bindSubmit('route-admin-form', async (fd) => {
  const result = await api('/api/route/upsert', {
    route_id: fd.get('route_id'),
    departure_city: fd.get('departure_city'),
    arrival_city: fd.get('arrival_city'),
    departure_time: fd.get('departure_time'),
    arrival_time: fd.get('arrival_time'),
    capacity: Number(fd.get('capacity')),
    driver_name: fd.get('driver_name'),
  });
  if (!result.ok) throw new Error(result.error);
  setStatus('Маршрут сохранён');
});

bindSubmit('route-delete-form', async (fd) => {
  const result = await api('/api/route/delete', { route_id: fd.get('route_id') });
  if (!result.ok) throw new Error(result.error);
  setStatus('Маршрут удалён');
});

bindSubmit('contact-form', async (fd) => {
  const result = await api('/api/contact', {
    name: fd.get('name'),
    email: fd.get('email'),
    company: fd.get('company'),
    message: fd.get('message'),
  });
  if (!result.ok) throw new Error(result.error);
  setStatus(`Заявка отправлена. Тикет: ${result.ticket}`);
});

        "available_seats": segment.available_seats,
    }


def build_navigation_guide(segments: List[RouteSegment]) -> Dict[str, object]:
    if not segments:
        return {"segments": [], "total_duration_minutes": 0, "transfers_count": 0}

    result: List[Dict[str, object]] = []
    for i, segment in enumerate(segments):
        payload = segment_to_dict(segment)
        wait = 0
        if i < len(segments) - 1:
            wait = int((parse_clock(segments[i + 1].departure_time) - parse_clock(segment.arrival_time)).total_seconds() // 60)
        payload["wait_minutes"] = wait
        result.append(payload)

    total_duration = int((parse_clock(segments[-1].arrival_time) - parse_clock(segments[0].departure_time)).total_seconds() // 60)
    return {"segments": result, "total_duration_minutes": max(total_duration, 0), "transfers_count": max(len(segments) - 1, 0)}


def get_departures(city: str, limit: int = 8) -> List[Dict[str, object]]:
    city_normalized = city.strip().lower()

    def operation(service: LogisticsService) -> List[Dict[str, object]]:
        rows = [s for s in service.segments.values() if not city_normalized or s.departure_city.lower() == city_normalized]
        rows = sorted(rows, key=lambda x: parse_clock(x.departure_time))[: max(limit, 1)]
        return [segment_to_dict(s) for s in rows]

    return service_manager.run(operation, "get_departures")


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
    <p>Продвинутая навигация + самовосстановление: система лечит себя при сбоях и продолжает работу.</p>
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
      <div class='metric'>Заполняемость <b id='m-load'>0%</b></div>
      <div class='metric'>Конверсия <b id='m-conversion'>0%</b></div>
      </div>
    <div class='hero-visual'>
      <img src='https://images.unsplash.com/photo-1494412651409-8963ce7935a7?auto=format&fit=crop&w=1600&q=80' alt='Пассажирский транспорт на маршруте'>
    </div>
    <div class='photo-grid' id='photo-gallery'>
      <div class='photo-card'>
        <img src='https://images.unsplash.com/photo-1474487548417-781cb71495f3?auto=format&fit=crop&w=1200&q=80' alt='Автобус на трассе'>
        <p>Надёжные междугородние рейсы</p>
      </div>
      <div class='photo-card'>
        <img src='https://images.unsplash.com/photo-1502920917128-1aa500764ce7?auto=format&fit=crop&w=1200&q=80' alt='Дорога и логистика'>
        <p>Гибкая логистика и прогнозирование</p>
      </div>
      <div class='photo-card'>
        <img src='https://images.unsplash.com/photo-1515169067868-5387ec356754?auto=format&fit=crop&w=1200&q=80' alt='Комфорт для пассажиров'>
        <p>Комфорт и сервис для пассажиров</p>
      </div>
      <div class='photo-card'>
        <img src='https://images.unsplash.com/photo-1473396413399-6717e31f5e0b?auto=format&fit=crop&w=1200&q=80' alt='Передача посылок'>
        <p>Безопасная отправка передачек</p>
      </div>
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

      <div class='split' style='margin-top:10px'>
        <div class='item' id='healing-state'>Автовосстановление: 0, ошибок: 0</div>
        <button id='heal-now' class='ghost' type='button'>Запустить самовосстановление</button>
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

    def _send_json(self, payload: Dict[str, Any], status: int = 200) -> None:
        self._send(status, json.dumps(payload, ensure_ascii=False), "application/json; charset=utf-8")

    def _read_json(self) -> Dict[str, Any]:
        length = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(length).decode("utf-8")
        return json.loads(raw or "{}")

    def _state_payload(self) -> Dict[str, Any]:
        return service_manager.run(
            lambda service: {
                "routes": [segment_to_dict(s) for s in service.segments.values()],
                "bookings": [vars(b) for b in service.bookings.values()],
                "parcels": [vars(p) for p in service.parcels.values()],
            },
            "state_payload",
        )

    def do_GET(self) -> None:  # noqa: N802
        path = urlparse(self.path).path
        if path == "/manifest.webmanifest":
            self._send_json(MANIFEST_JSON)
            return
        if path == "/service-worker.js":

        <form id='cancel-booking-form' class='form'>
          <b>Отменить бронь</b>
          <input name='booking_id' class='input' type='number' min='1' placeholder='ID брони' required>
          <button class='ghost'>Отменить бронь</button>
        </form>

        <form id='cancel-parcel-form' class='form'>
          <b>Отменить передачку</b>
          <input name='parcel_id' class='input' type='number' min='1' placeholder='ID передачки' required>
          <button class='ghost'>Отменить передачку</button>
        </form>

        <form id='route-admin-form' class='form'>
          <b>Управление маршрутом (создать/обновить)</b>
          <input name='route_id' class='input' placeholder='ID маршрута' required>
          <input name='departure_city' class='input' placeholder='Город отправления' required>
          <input name='arrival_city' class='input' placeholder='Город прибытия' required>
          <input name='departure_time' class='input' placeholder='Время отправления HH:MM' required>
          <input name='arrival_time' class='input' placeholder='Время прибытия HH:MM' required>
          <input name='capacity' class='input' type='number' min='1' placeholder='Вместимость' required>
          <input name='driver_name' class='input' placeholder='Водитель' required>
          <button>Сохранить маршрут</button>
        </form>

        <form id='route-delete-form' class='form'>
          <b>Удалить маршрут</b>
          <input name='route_id' class='input' placeholder='ID маршрута' required>
          <button class='ghost'>Удалить маршрут</button>
        </form>
            self._send(200, SERVICE_WORKER_JS, "application/javascript; charset=utf-8")
            return
        if path == "/api/state":

  <section id='enterprise' class='card' style='margin-top:12px'>
    <h2>Enterprise-уровень (уровень проекта за $1M)</h2>
    <div class='site-nav'>
      <a href='#dashboard'>Операционный центр</a><a href='#actions'>Управление</a><a href='#enterprise'>Enterprise</a><a href='#support'>Support</a>
    </div>
    <div class='enterprise-grid'>
      <div class='enterprise-card'><h3>SLA 99.95%</h3><div class='muted'>Мониторинг, алерты и самовосстановление.</div></div>
      <div class='enterprise-card'><h3>Безопасность</h3><div class='muted'>Журнал событий, контроль доступов, трассировка ошибок.</div></div>
      <div class='enterprise-card'><h3>Продуктовая аналитика</h3><div class='muted'>KPI по рейсам, местам, заявкам и работе поддержки.</div></div>
      <div class='enterprise-card'><h3>Клиентский успех</h3><div class='muted'>Поддержка 24/7, onboarding и персональный менеджер.</div></div>
    </div>
  </section>

  <section id='support' class='card' style='margin-top:12px'>
    <h2>Поддержка и продажи</h2>
    <form id='contact-form' class='form'>
      <b>Запросить демо / консультацию</b>
      <input name='name' class='input' placeholder='Имя' required>
      <input name='email' class='input' placeholder='Email' required>
      <input name='company' class='input' placeholder='Компания'>
      <input name='message' class='input' placeholder='Что требуется внедрить' required>
      <button>Отправить заявку</button>
    </form>
    <div class='faq' style='margin-top:10px'>
      <details><summary>Есть ли SLA и ответственность?</summary><div class='muted'>Да, в enterprise-контракте фиксируются SLA, штрафы и KPI.</div></details>
      <details><summary>Есть ли кастомизация под бизнес?</summary><div class='muted'>Да, поддерживаются кастомные роли, интеграции и брендирование.</div></details>
      <details><summary>Есть ли миграция данных?</summary><div class='muted'>Да, предусмотрен onboarding и миграция с legacy-систем.</div></details>
    </div>
  </section>

  <footer class='footer'>© 2026 Logistics Enterprise Platform · Политика конфиденциальности · Условия обслуживания · Security & Compliance</footer>
            self._send_json(self._state_payload())
            return
        if path == "/api/health":
            self._send_json(service_manager.health_payload())
            return
        self._send(200, render_page(), "text/html; charset=utf-8")

    def do_POST(self) -> None:  # noqa: N802
        path = urlparse(self.path).path

        try:
            if path.startswith("/api/"):
                data = self._read_json()

                if path == "/api/heal":
                    service_manager.heal(str(data.get("reason", "manual")))
                    self._send_json({"ok": True, **service_manager.health_payload()})
                    return

                if path == "/api/navigation-guide":
                    route = service_manager.run(
                        lambda service: service.find_route_sequence(
                            str(data.get("departure_city", "")),
                            str(data.get("arrival_city", "")),
                            str(data.get("earliest_departure", "") or "") or None,
                        ),
                        "navigation_guide",
                    )
                    self._send_json({"ok": True, "guide": build_navigation_guide(route)})
                    return

                if path == "/api/find-route":
                    route = service_manager.run(
                        lambda service: service.find_route_sequence(
                            str(data.get("departure_city", "")),
                            str(data.get("arrival_city", "")),
                            str(data.get("earliest_departure", "") or "") or None,
                        ),
                        "find_route",
                    )
                    self._send_json({"ok": True, "routes": [segment_to_dict(item) for item in route]})
                    return

                if path == "/api/departures":
                    departures = get_departures(str(data.get("city", "")), int(data.get("limit", 8)))
                    self._send_json({"ok": True, "departures": departures})
                    return

                if path == "/api/book":
                    booking = service_manager.run(
                        lambda service: service.book_seats(
                            str(data.get("route_id", "")),
                            str(data.get("passenger_name", "")),
        if path == "/api/analytics":
            payload = self._state_payload()
            routes = payload["routes"]
            bookings = payload["bookings"]
            parcels = payload["parcels"]
            total_capacity = sum((service_manager.service.segments[r["route_id"]].capacity for r in routes if r["route_id"] in service_manager.service.segments), 0)
            free_seats = sum(r["available_seats"] for r in routes)
            occupied = max(total_capacity - free_seats, 0)
            load = int((occupied / total_capacity) * 100) if total_capacity else 0
            conversion = int((len(bookings) / len(routes)) * 100) if routes else 0
            self._send_json({"load_factor_percent": load, "conversion_percent": conversion, "parcels_count": len(parcels)})
            return
                            int(data.get("seats", 0)),
                        ),
                        "book",
                    )
                    service_manager.record_booking(booking)
                    self._send_json({"ok": True, "booking": vars(booking)})
                    return

                if path == "/api/parcel":
                    parcel = service_manager.run(
                        lambda service: service.register_parcel(
                            str(data.get("route_id", "")),
                            str(data.get("sender_name", "")),
                            str(data.get("recipient_name", "")),
                            str(data.get("description", "")),
                        ),
                        "parcel",
                    )
                    service_manager.record_parcel(parcel)
                    self._send_json({"ok": True, "parcel": vars(parcel)})
                    return

                self._send_json({"ok": False, "error": "Неизвестный endpoint"}, status=404)
                return

            length = int(self.headers.get("Content-Length", "0"))
            raw = self.rfile.read(length).decode("utf-8")
            data = {k: v[0] for k, v in parse_qs(raw).items()}
            action = data.get("action", "")
            if action == "book":
                booking = service_manager.run(
                    lambda service: service.book_seats(data.get("route_id", ""), data.get("passenger_name", ""), int(data.get("seats", "0"))),
                    "legacy_book",
                )
                service_manager.record_booking(booking)
            if action == "parcel":
                parcel = service_manager.run(
                    lambda service: service.register_parcel(
                        data.get("route_id", ""),
                        data.get("sender_name", ""),
                        data.get("recipient_name", ""),
                        data.get("description", ""),
                    ),
                    "legacy_parcel",
                )
                service_manager.record_parcel(parcel)
            self._send(200, render_page(), "text/html; charset=utf-8")
        except (ValueError, json.JSONDecodeError) as exc:
            if path.startswith("/api/"):
                self._send_json({"ok": False, "error": str(exc), **service_manager.health_payload()}, status=400)
                return
            self._send(400, f"Ошибка: {exc}", "text/plain; charset=utf-8")


def run() -> None:
    host, port = "0.0.0.0", 8080
    server = HTTPServer((host, port), LogisticsHandler)
    print(f"Сервер запущен: http://{host}:{port}")
    server.serve_forever()


if __name__ == "__main__":
    run()
                if path == "/api/contact":
                    name = str(data.get("name", "")).strip()
                    email = str(data.get("email", "")).strip()
                    message = str(data.get("message", "")).strip()
                    if not name or not email or not message:
                        raise ValueError("Заполните обязательные поля заявки")
                    ticket = f"REQ-{len(CONTACT_REQUESTS) + 1:05d}"
                if path == "/api/booking/cancel":
                    booking_id = int(data.get("booking_id", 0))
                    service_manager.run(lambda service: service.cancel_booking(booking_id), "cancel_booking")
                    service_manager.record_event({"type": "cancel_booking", "booking_id": booking_id})
                    self._send_json({"ok": True})
                    return

                if path == "/api/parcel/cancel":
                    parcel_id = int(data.get("parcel_id", 0))
                    service_manager.run(lambda service: service.cancel_parcel(parcel_id), "cancel_parcel")
                    service_manager.record_event({"type": "cancel_parcel", "parcel_id": parcel_id})
                    self._send_json({"ok": True})
                    return

                if path == "/api/route/upsert":
                    route = RouteSegment(
                        str(data.get("route_id", "")),
                        str(data.get("departure_city", "")),
                        str(data.get("arrival_city", "")),
                        str(data.get("departure_time", "")),
                        str(data.get("arrival_time", "")),
                        int(data.get("capacity", 0)),
                        str(data.get("driver_name", "")),
                    )
                    service_manager.run(lambda service: service.upsert_route(route), "route_upsert")
                    service_manager.record_event({
                        "type": "upsert_route",
                        "route_id": route.route_id,
                        "departure_city": route.departure_city,
                        "arrival_city": route.arrival_city,
                        "departure_time": route.departure_time,
                        "arrival_time": route.arrival_time,
                        "capacity": route.capacity,
                        "driver_name": route.driver_name,
                    })
                    self._send_json({"ok": True})
                    return

                if path == "/api/route/delete":
                    route_id = str(data.get("route_id", ""))
                    service_manager.run(lambda service: service.delete_route(route_id), "route_delete")
                    service_manager.record_event({"type": "delete_route", "route_id": route_id})
                    self._send_json({"ok": True})
                    return

                    CONTACT_REQUESTS.append({
                        "ticket": ticket,
                        "name": name,
                        "email": email,
                        "company": str(data.get("company", "")).strip(),
                        "message": message,
                    })
                    self._send_json({"ok": True, "ticket": ticket})
                    return

