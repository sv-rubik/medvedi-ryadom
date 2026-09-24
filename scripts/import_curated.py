"""Import the user's ten-year incident list as individually traceable map reports.

Rows with a geographic place are mapped. Nationwide statistics are kept in the
source document but cannot truthfully be represented by a single map point.
The import is idempotent and uses a matching archived publication when found.
"""

from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote

from update_news import ATTACK, CACHE, EVENTS, HISTORY, geocode

SOURCE = Path(__file__).resolve().parents[1] / 'data' / 'curated-2016-2026.md'
MONTHS = {'январь': 1, 'февраль': 2, 'март': 3, 'апрель': 4, 'май': 5,
          'июнь': 6, 'июль': 7, 'август': 8, 'сентябрь': 9, 'октябрь': 10,
          'ноябрь': 11, 'декабрь': 12}
STOP = {'медвед', 'медвеж', 'нападе', 'напал', 'напала', 'напали', 'област',
        'район', 'красно', 'россий', 'погиб', 'мужчи', 'женщи', 'людям',
        'получ', 'после', 'вышел', 'зашел', 'среди', 'вблиз', 'около',
        'групп', 'челове', 'сентяб', 'август', 'город', 'местн', 'зверь',
        'два', 'двух', 'дней', 'медведи'}
PREFIX = re.compile(r'^(?:дер\.|пос\.|с\.|г\.|о\.|мкр\.|район|около|возле|центр|территория|берег)\s*', re.I)
FALLBACK_QUERIES = {
    'Южно-Енисейский': 'Красноярский край',
    'Петропавловск-Камчатский': 'Петропавловск-Камчатский',
    'Холмский район': 'Холмск',
    'Мутновской ГеоЭС': 'Камчатский край',
    'Курильские острова': 'Южно-Курильск',
    'Томск,': 'Томск',
    'Магадан,': 'Магадан',
    'Онотка': 'Иркутская область',
    'реки Таптан': 'Кривошеино, Томская область',
    'Мариинский район': 'Мариинск',
    'Ергаки': 'Красноярский край',
    'озеро Медвежье': 'Красноярский край',
    'Магри': 'Сочи',
    'Яковлевский район': 'Приморский край',
    'Лесное': 'Красноярский край',
    'Ярославль': 'Ярославль',
    'Кунашир': 'Южно-Курильск',
    'Тугуро-Чумиканский район': 'Хабаровский край',
    'Маркова под Иркутском': 'Иркутск',
    'Архангельска': 'Архангельск',
    'Оротукан': 'Магаданская область',
    'Красноярск,': 'Красноярск',
    'Саяны, Красноярск': 'Красноярск',
    'Водники': 'Красноярск',
    'Ханты-Мансийский автономный округ': 'Ханты-Мансийск',
    'Поросозера': 'Мурманская область',
    'Гыданская тундра': 'Салехард',
    'Ягодный': 'Елизово',
    'Медногорска': 'Медногорск',
    'Амдерма': 'Нарьян-Мар',
}


def rows():
    for line in SOURCE.read_text(encoding='utf-8').splitlines():
        if not line.startswith('| ') or line.startswith('| Дата') or line.startswith('|---'):
            continue
        parts = [part.strip() for part in line.strip('|').split('|')]
        if len(parts) != 4:
            continue
        raw_date, location, summary, source = parts
        source = re.sub(r'\s*:chatgpt-content-reference\{.*', '', source).strip()
        source = source.split(' / ')[0].strip()
        yield raw_date, location, summary, source


def parsed_date(value):
    year_match = re.search(r'20\d{2}', value)
    if not year_match:
        raise ValueError(value)
    year = int(year_match.group())
    first_in_range = re.match(r'(\d{1,2})\.(\d{2})[–-]', value)
    if first_in_range:
        day, month = map(int, first_in_range.groups())
        return f'{year:04d}-{month:02d}-{day:02d}', 'range'
    month_match = re.search(r'(\d{1,2})\.(\d{2})\.(20\d{2})', value)
    if month_match:
        day, month = map(int, month_match.groups()[:2])
        first_day = re.match(r'(\d{1,2})[–-]', value)
        if first_day:
            day = int(first_day.group(1))
        return f'{year:04d}-{month:02d}-{day:02d}', 'range' if '–' in value else 'event'
    if value[:1].isdigit() and '–' in value:
        first_day = int(re.match(r'\d+', value).group())
        month = int(re.search(r'\.(\d{2})', value).group(1))
        return f'{year:04d}-{month:02d}-{first_day:02d}', 'range'
    for name, month in MONTHS.items():
        if name in value.lower():
            return f'{year:04d}-{month:02d}-01', 'month'
    return f'{year:04d}-01-01', 'year'


def words(value):
    return {word[:6] for word in re.findall(r'[а-яё]{5,}', value.casefold())
            if word[:6] not in STOP}


def source_for(location, summary, year, archive, event_date=None, date_basis=None):
    terms = words(location + ' ' + summary)
    place_terms = words(location)
    ranked = []
    for item in archive:
        if item['publishedAt'][:4] != str(year):
            continue
        if event_date and date_basis in ('event', 'range'):
            if abs((datetime.fromisoformat(item['publishedAt']) - datetime.fromisoformat(event_date)).days) > (21 if date_basis == 'range' else 10):
                continue
        if event_date and date_basis == 'month' and item['publishedAt'][:7] != event_date[:7]:
            continue
        if re.search(r'Тув|Тыв', location, re.I) and not re.search(r'Тув|Тыв|Енисе|Тодж', item['title'], re.I):
            continue
        if ATTACK.search(summary) and not ATTACK.search(item['title']):
            continue
        head = words(item['title'])
        place_overlap = len(place_terms & head)
        overlap = len(terms & head)
        if place_overlap == 0 or overlap < 2:
            continue
        ranked.append((overlap + 1.5 * place_overlap, item))
    if ranked:
        ranked.sort(key=lambda pair: pair[0], reverse=True)
        if ranked[0][0] >= 3.5:
            return ranked[0][1], ranked[0][0]
    return None, 0


def geocode_query(location):
    parts = [part.strip() for part in location.split(',')]
    # The most specific named settlement comes first in most rows. When a
    # region is listed first, keep its regional centre as the marker.
    first = re.sub(r'\([^)]*\)', '', parts[0]).strip()
    first = PREFIX.sub('', first).strip(' «»')
    first = PREFIX.sub('', first).strip(' «»')
    first = re.split(r'\s+и\s+|\s+—\s+|\s*/\s*', first)[0].strip()
    if first.lower().startswith('республика '):
        return first
    if first == 'ЯНАО':
        return 'Ямало-Ненецкий автономный округ'
    if first == 'ХМАО':
        return 'Ханты-Мансийский автономный округ'
    if first.startswith('северный склон г. Зелёная'):
        return 'Краснодарский край'
    if first.startswith('Карлук под Иркутском'):
        return 'Карлук, Иркутская область'
    if ' край' in first or ' область' in first or first in ('Сахалин', 'Камчатка', 'ЯНАО', 'ХМАО — Югра'):
        return first
    region = parts[-1].strip()
    region = re.sub(r'\([^)]*\)', '', region).strip()
    if region != parts[0] and len(region) < 45:
        return f'{first}, {region}'
    return first


def find_existing(events, date, location, summary):
    matching = words(location + ' ' + summary)
    for event in events:
        if event['eventDate'][:4] != date[:4]:
            continue
        if abs((datetime.fromisoformat(event['eventDate']) - datetime.fromisoformat(date)).days) > 7:
            continue
        common = matching & words(event['place'] + ' ' + event['title'] + ' ' + event['summary'])
        if len(common) >= 2 and (words(location) & words(event['place'] + ' ' + event['region'] + ' ' + event['title'])):
            return event
    return None


def main():
    data = json.loads(EVENTS.read_text(encoding='utf-8'))
    archive = json.loads(HISTORY.read_text(encoding='utf-8'))['records']
    cache = json.loads(CACHE.read_text(encoding='utf-8'))
    added = matched = skipped = without_source = unlocated = 0
    for raw_date, location, summary, source_name in rows():
        if location.startswith('Россия, 41 регион') or location.startswith('Сахалин и Курильские острова'):
            skipped += 1  # Counts of many incidents, without individual places.
            continue
        date, date_basis = parsed_date(raw_date)
        prior = find_existing(data['events'], date, location, summary)
        if prior:
            matched += 1
            continue
        identifier = hashlib.sha256((raw_date + location + summary).encode()).hexdigest()[:16]
        if any(event['id'] == 'curated-' + identifier for event in data['events']):
            matched += 1
            continue
        query = geocode_query(location)
        point = geocode(query, cache)
        if not point:
            for fragment, fallback in FALLBACK_QUERIES.items():
                if fragment in location or fragment in query:
                    point = geocode(fallback, cache)
                    if point:
                        break
        if not point:
            print(f'NO PLACE: {location} -> {query}', flush=True)
            unlocated += 1
            CACHE.write_text(json.dumps(cache, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
            continue
        article, score = source_for(location, summary, int(date[:4]), archive, date, date_basis)
        if article:
            source_url = article['sourceUrl']
            source_name = article['source']
        else:
            # The pasted ChatGPT citation markers are not URLs. Preserve a
            # live search for manual verification and label it honestly.
            source_url = 'https://news.google.com/search?q=' + quote(f'медведь {location} {date[:4]}')
            source_name = 'Поиск источника'
            without_source += 1
        kind = 'attack' if ATTACK.search(summary) or 'погиб' in summary or 'ранен' in summary else 'sighting'
        title = f"{location}: {'нападение медведя' if kind == 'attack' else 'выход медведя к людям'}"
        data['events'].append({
            'id': 'curated-' + identifier, 'type': kind, 'eventDate': date,
            'dateBasis': date_basis, 'reportedDate': raw_date,
            'place': point['place'], 'region': point['region'],
            'title': title, 'summary': summary,
            'longitude': point['longitude'], 'latitude': point['latitude'],
            'precision': f'Метка поставлена по названию места «{location}». Точные координаты происшествия не установлены.',
            'status': 'Из пользовательского списка; детали требуют сверки с публикацией',
            'source': source_name, 'sourceUrl': source_url,
        })
        added += 1
        if added % 10 == 0:
            print(f'Imported {added} map reports', flush=True)
            CACHE.write_text(json.dumps(cache, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    data['updatedAt'] = datetime.now(timezone.utc).isoformat(timespec='seconds')
    data['events'].sort(key=lambda item: item['eventDate'], reverse=True)
    EVENTS.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    CACHE.write_text(json.dumps(cache, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(f'Added: {added}; already mapped: {matched}; aggregate counts: {skipped}; without article URL: {without_source}; unlocated: {unlocated}')


if __name__ == '__main__':
    main()
