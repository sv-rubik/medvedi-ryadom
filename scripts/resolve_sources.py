"""Replace search-result links on imported cases with matched publication links."""

from __future__ import annotations

import json
import re
import time
from datetime import date, datetime

from collect_history import search
from import_curated import EVENTS, words


def main():
    data = json.loads(EVENTS.read_text(encoding='utf-8'))
    changed = 0
    checked = 0
    for event in data['events']:
        if event.get('source') != 'Поиск источника':
            continue
        year = int(event['eventDate'][:4])
        original_place = re.search(r'«([^»]+)»', event.get('precision', ''))
        place = original_place.group(1) if original_place else event['place']
        terms = words(place + ' ' + event['summary'])
        place_terms = words(place)
        query_place = re.split(r',|\s+и\s+', place)[0]
        query_place = re.sub(r'^(?:с\.|пос\.|дер\.|район)\s+', '', query_place).strip()
        if len(query_place) < 4:
            continue
        results = search('медведь ' + query_place, date(year, 1, 1), date(year + 1, 1, 1))
        checked += 1
        ranked = []
        for item in results:
            if event['dateBasis'] == 'event' and abs((datetime.fromisoformat(item['publishedAt']) - datetime.fromisoformat(event['eventDate'])).days) > 10:
                continue
            title_terms = words(item['title'])
            location_overlap = len(place_terms & title_terms)
            overlap = len(terms & title_terms)
            minimum = 3 if any(word in place for word in ('область', 'край', 'республика')) else 2
            if location_overlap and overlap >= minimum:
                ranked.append((overlap + 2 * location_overlap, item))
        if ranked:
            ranked.sort(key=lambda pair: pair[0], reverse=True)
            score, best = ranked[0]
            if score >= 4:
                event['source'] = best['source']
                event['sourceUrl'] = best['sourceUrl']
                changed += 1
        if checked % 10 == 0:
            print(f'Checked {checked}; found {changed} publication links', flush=True)
            EVENTS.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        time.sleep(.15)
    EVENTS.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(f'Checked: {checked}; replaced search links: {changed}')


if __name__ == '__main__':
    main()
