"""Append every new or edited report version to the permanent CSV history."""

import csv
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ARCHIVE = ROOT / 'data' / 'news-archive.csv'
FIELDS = ['id', 'revision', 'category', 'date', 'title', 'place', 'region',
          'summary', 'source', 'sourceUrl', 'archivedAt']


def main():
    known = set()
    if ARCHIVE.exists():
        with ARCHIVE.open(encoding='utf-8-sig', newline='') as stream:
            known = {(row['id'], row['revision']) for row in csv.DictReader(stream)}
    rows = []
    for category, filename, key, date_key in (
        ('event', 'events.json', 'events', 'eventDate'),
        ('news', 'news.json', 'articles', 'publishedAt'),
        ('indexed', 'history.json', 'records', 'publishedAt'),
    ):
        data = json.loads((ROOT / 'dist' / filename).read_text(encoding='utf-8'))
        for item in data[key]:
            revision = hashlib.sha256(json.dumps(item, ensure_ascii=False, sort_keys=True).encode()).hexdigest()[:16]
            if (item['id'], revision) in known:
                continue
            rows.append({
                'id': item['id'], 'revision': revision, 'category': category,
                'date': item.get(date_key, ''), 'title': item.get('title', ''),
                'place': item.get('place', ''), 'region': item.get('region', ''),
                'summary': item.get('summary', ''), 'source': item.get('source', ''),
                'sourceUrl': item.get('sourceUrl', ''),
                'archivedAt': datetime.now(timezone.utc).isoformat(timespec='seconds'),
            })
            known.add((item['id'], revision))
    ARCHIVE.parent.mkdir(exist_ok=True)
    with ARCHIVE.open('a', encoding='utf-8-sig' if not ARCHIVE.exists() else 'utf-8', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=FIELDS)
        if stream.tell() == 0:
            writer.writeheader()
        writer.writerows(rows)
    print(f'Archived record versions: {len(rows)}')


if __name__ == '__main__':
    main()
