"""Check article dates and subjects before claiming a supplied case has a source."""

import json
import re
from urllib.parse import quote

from import_curated import EVENTS, HISTORY, source_for

VERIFIED = {
    ('2026-09-16', 'Красноярский край'): (
        'Вести. Красноярск', 'https://www.vesti-krasnoyarsk.ru/news/proisshestviya/post-61613/',
        'В ночь на 16 сентября медведь напал на 66-летнюю жительницу деревни Верхний Кебеж Ермаковского округа. Женщина погибла возле дома. Следователи выясняют обстоятельства; версия о том, что медведь вытащил её через окно, не подтверждена.'),
    ('2026-09-19', 'Камчатка / район границы с Чукоткой'): (
        'РБК', 'https://www.rbc.ru/society/15/09/2026/6aa937759a7947f752018767', None),
    ('2026-09-01', 'Республика Тыва'): (
        'РБК', 'https://www.rbc.ru/society/15/09/2026/6aa937759a7947f752018767', None),
    ('2026-08-01', 'Абаза, Хакасия'): (
        'МВД Медиа', 'https://mvdmedia.ru/news/obshchestvo/v-khakasii-dlya-zashchity-zhiteley-abazy-ot-nashestviya-medvedey-zadeystvovana-bespilotnaya-aviatsiya/', None),
}


def main():
    data = json.loads(EVENTS.read_text(encoding='utf-8'))
    archive = json.loads(HISTORY.read_text(encoding='utf-8'))['records']
    changed = 0
    for event in data['events']:
        if not event['id'].startswith('curated-'):
            continue
        location = event['title'].split(': ', 1)[0]
        article, _ = source_for(location, event['summary'], int(event['eventDate'][:4]),
                                archive, event['eventDate'], event['dateBasis'])
        if location.startswith('с. Анга') and article and not re.search(r'Анга|Юшин', article['title'], re.I):
            article = None
        if article:
            source, url = article['source'], article['sourceUrl']
        else:
            source = 'Поиск источника'
            url = 'https://news.google.com/search?q=' + quote(f'медведь {location} {event["eventDate"][:4]}')
        verified = VERIFIED.get((event['eventDate'], location))
        if verified:
            source, url, summary = verified
            if summary:
                event['summary'] = summary
                event['status'] = 'Сверено с региональным сообщением; точное место требует проверки'
        if (source, url) != (event['source'], event['sourceUrl']):
            print(f'Corrected source: {event["reportedDate"]} {location}: {event["source"]} -> {source}')
            event['source'], event['sourceUrl'] = source, url
            changed += 1
    EVENTS.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(f'Corrected {changed} publication links')


if __name__ == '__main__':
    main()
