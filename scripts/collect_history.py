"""Search the Google News index, once across past years or daily for one day.

The index gives headlines and publication dates but often no article text or
direct URL. Those records remain in a separate searchable archive until their
place and details can be verified for the map.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import date, datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path

from update_news import BEAR, ENCOUNTER, GENERAL_NEWS, REJECT, MSK, ROOT, USER_AGENT

HISTORY = ROOT / 'dist' / 'history.json'
BASE = 'https://news.google.com/rss/search?'
SEARCHES = ('медведь напал', 'медведь вышел', 'медведь site:dzen.ru')


def search(query: str, start: date, end: date) -> list[dict]:
    term = f'{query} after:{start.isoformat()} before:{end.isoformat()}'
    url = BASE + urllib.parse.urlencode({'q': term, 'hl': 'ru', 'gl': 'RU', 'ceid': 'RU:ru'})
    request = urllib.request.Request(url, headers={'User-Agent': USER_AGENT})
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            root = ET.fromstring(response.read())
    except Exception as exc:
        print(f'Google News failed for {term}: {exc}', file=sys.stderr)
        return []
    records = []
    for item in root.findall('./channel/item'):
        source = item.find('source')
        source_name = source.text.strip() if source is not None and source.text else 'СМИ'
        title = item.findtext('title', '').strip()
        suffix = ' - ' + source_name
        if title.endswith(suffix):
            title = title[:-len(suffix)].strip()
        if not BEAR.search(title) or not ENCOUNTER.search(title) or REJECT.search(title) or GENERAL_NEWS.search(title):
            continue
        link = item.findtext('link', '')
        if not link.startswith('https://news.google.com/rss/articles/'):
            continue
        try:
            published = parsedate_to_datetime(item.findtext('pubDate', '')).astimezone(MSK).date()
        except (TypeError, ValueError):
            continue
        if not start <= published < end:
            continue
        records.append({
            'id': 'index-' + hashlib.sha256(link.encode()).hexdigest()[:16],
            'title': title, 'publishedAt': published.isoformat(),
            'source': source_name, 'sourceUrl': link,
            'summary': 'Заголовок найден в архиве новостей. Текст публикации, дата происшествия и точное место требуют проверки перед добавлением на карту.',
        })
    return records


def periods(all_years: bool):
    if not all_years:
        today = datetime.now(MSK).date()
        yield today, today + timedelta(days=1)
        return
    today = datetime.now(MSK).date()
    for year in range(1991, today.year + 1):
        if year < 2020:
            yield date(year, 1, 1), date(year + 1, 1, 1)
        else:
            for month in range(1, 13):
                start = date(year, month, 1)
                if start > today:
                    break
                end = date(year + 1, 1, 1) if month == 12 else date(year, month + 1, 1)
                yield start, min(end, today + timedelta(days=1))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--all', action='store_true', help='one-time initial search since 1991')
    args = parser.parse_args()
    data = json.loads(HISTORY.read_text(encoding='utf-8'))
    seen = {item['sourceUrl'] for item in data['records']} | set(data.get('ignoredUrls', []))
    added = 0
    checked = 0
    for start, end in periods(args.all):
        for query in SEARCHES:
            checked += 1
            results = search(query, start, end)
            for item in results:
                if item['sourceUrl'] not in seen:
                    data['records'].append(item)
                    seen.add(item['sourceUrl'])
                    added += 1
        if args.all:
            print(f'Searched through {start.isoformat()}: +{added} indexed reports', flush=True)
        time.sleep(.2)
    data['records'].sort(key=lambda item: item['publishedAt'], reverse=True)
    data['lastSearchAt'] = datetime.now(timezone.utc).isoformat(timespec='seconds')
    if added:
        data['updatedAt'] = data['lastSearchAt']
    HISTORY.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(f'Index queries: {checked}; new historical headlines: {added}; total: {len(data["records"])}')


if __name__ == '__main__':
    main()
