"""One-time cleanup of the initial trial run before publishing the news page."""

import json
from pathlib import Path

from update_news import report_related

ROOT = Path(__file__).resolve().parents[1]
NEWS = ROOT / 'dist' / 'news.json'
HISTORY = ROOT / 'dist' / 'history.json'


def main():
    news = json.loads(NEWS.read_text(encoding='utf-8'))
    history = json.loads(HISTORY.read_text(encoding='utf-8'))
    existing = {item['sourceUrl'] for item in history['records']}
    retained = []
    moved = 0
    for item in news['articles']:
        if report_related(item['title']):
            if item['sourceUrl'] not in existing:
                history['records'].append({**item, 'id': 'report-' + item['id'].split('-', 1)[1]})
                existing.add(item['sourceUrl'])
            moved += 1
        else:
            retained.append(item)
    news['articles'] = retained
    history['records'].sort(key=lambda item: item['publishedAt'], reverse=True)
    NEWS.write_text(json.dumps(news, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    HISTORY.write_text(json.dumps(history, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(f'Moved {moved} report headlines from other news to the encounter archive')


if __name__ == '__main__':
    main()
