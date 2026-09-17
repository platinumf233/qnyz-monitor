"""Monitor every eligible arrival date for a 15-night personal stay."""
import json
import logging
import os
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import requests
from monitor import apply_filters, get_stations
from qnyz_client import QnyzClient

STATE = Path('flexible-state.json')


def periods(today):
    first = max(date(2026, 9, 21), today + timedelta(days=2))
    last = today + timedelta(days=20)
    return [(str(first + timedelta(days=i)), str(first + timedelta(days=i + 15)))
            for i in range(max(0, (last - first).days + 1))]


def deliver(hits, state, day, send):
    sent = set(state.get('sent', []))
    fresh = {k: v for k, v in hits.items() if k not in sent}
    count = state.get('count', 0) if state.get('day') == day else 0
    if not fresh:
        logging.info('No new matching stays')
        return
    if count >= 4:
        logging.info('Daily notification budget reached; unsent matches remain pending')
        return
    # Limit each message size; only mark the entries actually included.
    batch = dict(list(fresh.items())[:60])
    send(f'青年驿站：{len(batch)}组可连住15晚', '\n\n'.join(batch.values()))
    state.update(day=day, count=count + 1, sent=sorted(sent | batch.keys()))


def send_wechat(title, body):
    url = os.environ['QNYZ_NOTIFY_URL'].strip()
    try:
        response = requests.post(url, data={'title': title, 'desp': body}, timeout=30)
        response.raise_for_status()
        result = response.json()
    except requests.RequestException:
        raise RuntimeError('ServerChan request failed; credentials omitted') from None
    if result.get('code') != 0 or result.get('data', {}).get('errno', 0) != 0:
        raise RuntimeError('ServerChan rejected the notification; state not marked sent')
    logging.info('ServerChan accepted notification')


def main():
    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
    today = datetime.now(timezone(timedelta(hours=8))).date()
    state = json.loads(STATE.read_text(encoding='utf-8')) if STATE.exists() else {}
    client = QnyzClient(verify=False, retries=2)
    hits = {}
    failures = 0
    for arrival, departure in periods(today):
        cfg = {'filters': {'date_from': arrival, 'date_to': departure,
                           'apply_scope': 'personal', 'user_type': 2}}
        try:
            stations = apply_filters(get_stations(client, cfg), cfg)
            for station in stations:
                key = f"{arrival}|{departure}|{station['id']}"
                hits[key] = f"{station.get('name', '')} [{station.get('district', '')}] {arrival} → {departure}（15晚）"
            logging.info('%s -> %s: %d stations', arrival, departure, len(stations))
        except Exception as exc:
            failures += 1
            logging.error('%s lookup failed: %s', arrival, type(exc).__name__)
    if failures:
        raise RuntimeError(f'{failures} arrival-date queries failed; retaining previous state')
    logging.info('Total matching stays: %d', len(hits))
    deliver(hits, state, str(today), send_wechat)
    STATE.write_text(json.dumps(state, ensure_ascii=False), encoding='utf-8')


if __name__ == '__main__':
    main()
