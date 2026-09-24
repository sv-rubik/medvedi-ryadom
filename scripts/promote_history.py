"""One-time promotion of locatable Russian incident headlines to the map.

The history index remains intact. Every promoted record points to its map
event, while publication date and approximate coordinates stay explicit.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone

from update_news import (ALIASES, ATTACK, CACHE, EVENTS, HISTORY, MULTIPLE,
                         GENERAL_NEWS, geocode, key_words, location_candidates,
                         relevant)


def duplicate(events, record, point, kind):
    date = datetime.fromisoformat(record['publishedAt'])
    for event in events:
        if event['type'] != kind or event['region'] != point['region']:
            continue
        if abs((datetime.fromisoformat(event['eventDate']) - date).days) > 4:
            continue
        first = key_words(event['title'] + ' ' + event['summary'])
        second = key_words(record['title'])
        shared = first & second
        if len(shared) >= 2:
            return event
        # Reports dated the same day and geocoded to the same named settlement
        # usually describe one occurrence, even if headlines differ.
        if event['eventDate'] == record['publishedAt'] and point['place'] != point['region'] and event['place'] == point['place']:
            return event
    return None


def main():
    data = json.loads(EVENTS.read_text(encoding='utf-8'))
    history = json.loads(HISTORY.read_text(encoding='utf-8'))
    cache = json.loads(CACHE.read_text(encoding='utf-8'))
    seen_urls = {item['sourceUrl']: item['id'] for item in data['events']}
    for event in data['events']:
        seen_urls.update({source['sourceUrl']: event['id'] for source in event.get('additionalSources', [])})
    added = linked = unlocated = irrelevant = 0
    for record in history['records']:
        if record.get('mappedEventId'):
            continue
        if record['sourceUrl'] in seen_urls:
            record['mappedEventId'] = seen_urls[record['sourceUrl']]
            linked += 1
            continue
        title = record['title']
        if not relevant(title) or MULTIPLE.search(title) or GENERAL_NEWS.search(title):
            irrelevant += 1
            continue
        point = None
        for candidate in location_candidates(title):
            # An indexed title alone is too weak to justify an unlimited
            # settlement lookup. Resolve cached places and recognized regions.
            if candidate.casefold() not in cache and not any(
                candidate.endswith(suffix) for suffix in ('область', 'край', 'республика', 'автономный округ')
            ) and candidate not in ALIASES.values():
                continue
            point = geocode(candidate, cache)
            if point:
                break
        if not point:
            unlocated += 1
            continue
        kind = 'attack' if ATTACK.search(title) else 'sighting'
        event = duplicate(data['events'], record, point, kind)
        if event:
            extras = event.setdefault('additionalSources', [])
            if record['sourceUrl'] != event['sourceUrl'] and not any(item['sourceUrl'] == record['sourceUrl'] for item in extras):
                extras.append({'source': record['source'], 'sourceUrl': record['sourceUrl']})
            record['mappedEventId'] = event['id']
            seen_urls[record['sourceUrl']] = event['id']
            linked += 1
            continue
        identifier = hashlib.sha256(record['sourceUrl'].encode()).hexdigest()[:16]
        event = {
            'id': 'auto-' + identifier, 'type': kind,
            'eventDate': record['publishedAt'], 'dateBasis': 'publication',
            'place': point['place'], 'region': point['region'],
            'title': title,
            'summary': (record['summary'] if record.get('summary') and
                        not record['summary'].startswith('Заголовок найден в архиве') else
                        f'В индексе новостей опубликован заголовок: «{title}». '
                        'Полный текст публикации недоступен; обстоятельства и дата самого происшествия требуют проверки по ссылке.'),
            'longitude': point['longitude'], 'latitude': point['latitude'],
            'precision': f'Метка поставлена по названию «{point["place"]}»; точное место происшествия не установлено.',
            'status': 'Автоматически найдено в архиве; текст и дата события не проверены',
            'source': record['source'], 'sourceUrl': record['sourceUrl'],
        }
        data['events'].append(event)
        record['mappedEventId'] = event['id']
        seen_urls[record['sourceUrl']] = event['id']
        added += 1
        if added % 50 == 0:
            print(f'Added {added} archive map points; linked {linked} reports', flush=True)
            CACHE.write_text(json.dumps(cache, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    now = datetime.now(timezone.utc).isoformat(timespec='seconds')
    if added:
        data['updatedAt'] = now
    if added or linked:
        history['updatedAt'] = now
    data['events'].sort(key=lambda item: item['eventDate'], reverse=True)
    EVENTS.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    HISTORY.write_text(json.dumps(history, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    CACHE.write_text(json.dumps(cache, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(f'Added map points: {added}; linked publications: {linked}; unlocated: {unlocated}; rejected/aggregate: {irrelevant}')


if __name__ == '__main__':
    main()
