"""One-time source-checked map entries from the historical search."""

import json
from datetime import datetime, timezone

from update_news import CACHE, EVENTS, NEWS, geocode

REPORTS = [
    ('2009-03-27-bolshoy-yaloman', '2009-03-27', 'Большой Яломан',
     'Республика Алтай', 'Медведь напал на чабана у Большого Яломана',
     'Житель села Большой Яломан Онгудайского района шел к своему подсобному хозяйству и встретил медведя. Мужчина залез на дерево, но зверь стащил его вниз и ранил. Пострадавшего доставили в больницу с травмой головы, переломами и рваными ранами.',
     'https://www.interfax.ru/russia/70963', False),
    ('2010-10-12-bichura', '2010-10-12', 'Бичура',
     'Республика Бурятия', 'Медведь ранил жителя Бичурского района',
     'В начале октября в лесу примерно в 15 километрах от Бичуры медведь напал сзади на местного жителя, занимавшегося зимними заготовками. Мужчина сумел отогнать зверя топором, но получил тяжелую травму головы и лишился глаза. Точная дата происшествия в публикации не названа.',
     'https://www.interfax.ru/russia/159575', True),
    ('2013-05-24-pakhachi', '2013-05-24', 'Пахачи',
     'Камчатский край', 'В Олюторском районе нашли погибшего оленевода',
     'Оленевод пропал 13 мая, когда отправился за отбившимися от стада животными примерно в 20 километрах от села Пахачи. Во время поисков медведь атаковал прибывших на вертолете людей; зверя застрелили. Рядом нашли останки оленевода. Точная дата его гибели не установлена.',
     'https://www.interfax.ru/russia/308447', True),
    ('2015-09-21-kirovskiy', '2015-09-21', 'Кировский, Приморский край',
     'Приморский край', 'Медведь напал на девушку в поселке Кировский',
     'Утром 21 сентября гималайский медведь выбежал на улицу поселка Кировский и столкнулся с микроавтобусом. После этого зверь напал на девушку; она получила легкие ранения руки и головы. Охотнадзор сообщил, что за три дня это был уже пятый выход медведя к населенным пунктам района.',
     'https://www.interfax.ru/russia/468006', False),
    ('2020-06-08-smirnykh', '2020-06-08', 'Смирных',
     'Сахалинская область', 'В Смирныховском районе погиб геодезист',
     '8 июня группа геодезистов работала примерно в 14 километрах от поселка Смирных. Руководитель группы ушел в лес проверить геодезический знак и не вернулся. Полицейские обнаружили его тело с ранами и следами медведя рядом. Администрация района сообщила, что мужчину убил медведь.',
     'https://www.interfax.ru/russia/712307', False),
    ('2021-12-26-preobrazheniye', '2021-12-26', 'Преображение, Приморский край',
     'Приморский край', 'Медведь напал на человека у поселка Преображение',
     'В районе поселка Преображение медведь напал на 57-летнего мужчину, когда тот собирал дрова. Сообщение о нападении поступило 26 декабря; пострадавшего госпитализировали в Находку. Егери искали зверя, а специалисты выясняли, почему он оставался активным зимой.',
     'https://www.interfax.ru/russia/812659', False),
]


def main():
    events = json.loads(EVENTS.read_text(encoding='utf-8'))
    news = json.loads(NEWS.read_text(encoding='utf-8'))
    cache = json.loads(CACHE.read_text(encoding='utf-8'))
    existing = {item['id'] for item in events['events']}
    for identifier, date, place, region, title, summary, url, publication_date in REPORTS:
        if identifier in existing:
            continue
        point = geocode(place, cache)
        if not point or region.casefold() not in point['region'].casefold():
            print(f'Skipped ambiguous location: {place} -> {point}')
            continue
        item = {
            'id': identifier, 'type': 'attack', 'eventDate': date,
            'place': place.split(',')[0], 'region': region,
            'title': title, 'summary': summary,
            'longitude': point['longitude'], 'latitude': point['latitude'],
            'precision': 'Точка обозначает центр населенного пункта; происшествие могло произойти в его окрестностях.',
            'status': 'Проверено по публикации Интерфакса',
            'source': 'Интерфакс', 'sourceUrl': url,
        }
        if publication_date:
            item['dateBasis'] = 'publication'
        events['events'].append(item)
        print(f'Added {identifier}')
    for item in events['events']:
        if item['id'] == 'auto-5a5b3a4232306497':
            item['eventDate'] = '2026-09-22'
            item.pop('dateBasis', None)
            item['title'] = 'В Туве погиб турист после нападения медведя'
            item['summary'] = (
                '22 сентября группа туристов из Москвы поднялась на лодке по Большому Енисею и остановилась в тайге Тоджинского района. '
                'Медведь напал на одного из мужчин, около 60 лет, и тяжело ранил его. Пострадавшего перевезли в село Тоора-Хем, затем санитарной авиацией доставили в Кызыл. '
                'Мужчина умер в больнице. О происшествии 24 сентября сообщил глава республиканского Госохотнадзора Артыш Салчак.'
            )
            item['source'] = 'Интерфакс'
            item['sourceUrl'] = 'https://www.interfax.ru/russia/1118149'
            item['additionalSources'] = [
                {'source': 'РБК', 'sourceUrl': 'https://www.rbc.ru/rbcfreenews/6ab4b852e50b2c8fd944c057'},
                {'source': 'Коммерсантъ', 'sourceUrl': 'https://www.kommersant.ru/doc/8973722'},
            ]
            item['status'] = 'Проверено по публикациям СМИ'
    events['events'].sort(key=lambda item: item['eventDate'], reverse=True)
    events['updatedAt'] = datetime.now(timezone.utc).isoformat(timespec='seconds')
    EVENTS.write_text(json.dumps(events, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    news_url = 'https://faunora.ru/news/v-komi-razreshili-otstrel-medvedey-31-2026-08-13'
    if not any(item['sourceUrl'] == news_url for item in news['articles']):
        news['articles'].append({
            'id': 'news-2026-08-13-komi-hunting',
            'title': 'В Коми разрешили отстрел медведей после выходов к поселкам',
            'publishedAt': '2026-08-13',
            'source': 'Faunora', 'sourceUrl': news_url,
            'summary': 'В Республике Коми с 1 августа разрешили отстрел бурого медведя. По данным регионального Минприроды, с начала 2026 года зарегистрировали 39 выходов диких животных к населенным пунктам, из них 31 связан с медведями. Ведомство связывает часть выходов с доступной пищей на свалках и безнадзорными животными.',
        })
        news['articles'].sort(key=lambda item: item['publishedAt'], reverse=True)
        news['updatedAt'] = datetime.now(timezone.utc).isoformat(timespec='seconds')
        NEWS.write_text(json.dumps(news, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    CACHE.write_text(json.dumps(cache, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


if __name__ == '__main__':
    main()
