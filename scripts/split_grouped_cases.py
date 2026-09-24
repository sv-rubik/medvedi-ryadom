"""Map separate dated places that were combined in supplied table rows."""

import hashlib
import json
from datetime import datetime, timezone
from urllib.parse import quote

from update_news import CACHE, EVENTS, geocode

RBC = 'https://www.rbc.ru/society/15/09/2026/6aa937759a7947f752018767'
EXTRAS = [
    ('2026-08-31', 'Хатырка, Чукотский автономный округ', 'Медведь напал на двух охотников у границы Камчатки и Чукотки',
     'РБК сообщает о нападении на двух охотников в районе села Хатырка 31 августа. Точное место на границе регионов не установлено.', 'РБК', RBC),
    ('2026-09-07', 'Республика Бурятия', 'Второе нападение медведя в Бурятии 7 сентября',
     'В сводке РБК отмечены отдельные нападения медведей в Бурятии 6 и 7 сентября. Место второго случая в этой сводке не уточнено.', 'РБК', RBC),
    ('2026-08-31', 'Подтёсово, Красноярский край', 'У Подтёсово погибли две сборщицы грибов',
     'По предварительным данным Следственного комитета, две жительницы Подтёсово 31 августа ушли за грибами и не вернулись. 2 сентября их тела обнаружили в лесу с повреждениями, характерными для нападения медведя.',
     'Интерфакс', 'https://m.interfax.ru/1112874'),
    ('2024-06-06', 'Юшина, Иркутская область', 'Медведь вышел у деревни Юшина',
     'В присланном списке отдельно упомянут выход медведя в районе деревни Юшина в тот же день, когда зверя заметили у села Анга. Подробности и точное место требуют проверки.',
     'Поиск источника', ''),
    ('2022-05-06', 'Поморцева, Иркутская область', 'Медведь вышел к домам у деревни Поморцева',
     'В присланном списке отдельно упомянут выход медведя к частным домам у деревни Поморцева. Подробности и точное место требуют проверки.',
     'Поиск источника', ''),
    ('2017-08-29', 'Лесосибирск, Красноярский край', 'Медведь ранил мужчину в Лесосибирске',
     'В присланном списке случай в Лесосибирске указан отдельно от выходов медведя в Подтёсово. Мужчина получил тяжёлые ранения; точная дата требует проверки.',
     'Поиск источника', ''),
]


def main():
    data = json.loads(EVENTS.read_text(encoding='utf-8'))
    cache = json.loads(CACHE.read_text(encoding='utf-8'))
    ids = {item['id'] for item in data['events']}
    added = 0
    for date, location, title, summary, source, source_url in EXTRAS:
        identifier = 'curated-split-' + hashlib.sha256((date + location).encode()).hexdigest()[:16]
        if identifier in ids:
            continue
        point = geocode(location, cache)
        if not point:
            region = location.split(',')[-1].strip()
            point = geocode(region, cache)
        if not point:
            print(f'Unlocated: {location}')
            continue
        if not source_url:
            source_url = 'https://news.google.com/search?q=' + quote(f'медведь {location} {date[:4]}')
        data['events'].append({
            'id': identifier, 'type': 'attack' if 'напал' in title or 'ранил' in title or 'погибли' in title else 'sighting',
            'eventDate': date, 'dateBasis': 'event' if source != 'Поиск источника' else 'unverified',
            'place': point['place'], 'region': point['region'],
            'title': title, 'summary': summary,
            'longitude': point['longitude'], 'latitude': point['latitude'],
            'precision': f'Приблизительная метка по названию «{location}»; точные координаты неизвестны.',
            'status': 'Отдельный случай из сгруппированного сообщения; детали требуют проверки',
            'source': source, 'sourceUrl': source_url,
        })
        ids.add(identifier)
        added += 1
    data['events'].sort(key=lambda item: item['eventDate'], reverse=True)
    if added:
        data['updatedAt'] = datetime.now(timezone.utc).isoformat(timespec='seconds')
    EVENTS.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    CACHE.write_text(json.dumps(cache, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(f'Added {added} separately located cases from grouped rows')


if __name__ == '__main__':
    main()
