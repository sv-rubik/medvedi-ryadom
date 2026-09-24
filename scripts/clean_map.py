"""Remove index-derived editorial summaries from map; keep their archive rows."""

import json

from update_news import EVENTS, HISTORY, relevant


def main():
    data = json.loads(EVENTS.read_text(encoding='utf-8'))
    archive = json.loads(HISTORY.read_text(encoding='utf-8'))
    removed = {event['id'] for event in data['events']
               if event.get('status', '').startswith('Автоматически найдено в архиве')
               and not relevant(event['title'])}
    data['events'] = [event for event in data['events'] if event['id'] not in removed]
    for record in archive['records']:
        if record.get('mappedEventId') in removed:
            del record['mappedEventId']
    EVENTS.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    HISTORY.write_text(json.dumps(archive, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(f'Removed {len(removed)} editorial map entries; headlines remain in archive')


if __name__ == '__main__':
    main()
