"""Resolve the source-checked Vologda and Tuva reports to one point each."""

import json
from datetime import datetime, timezone

from update_news import CACHE, EVENTS, HISTORY, geocode


def merge(events, history, primary, extras):
    removed = set()
    links = primary.setdefault('additionalSources', [])
    known = {primary['sourceUrl']} | {item['sourceUrl'] for item in links}
    for event in extras:
        removed.add(event['id'])
        for source in [{'source': event['source'], 'sourceUrl': event['sourceUrl']}] + event.get('additionalSources', []):
            if source['sourceUrl'] not in known:
                links.append(source)
                known.add(source['sourceUrl'])
    events[:] = [item for item in events if item['id'] not in removed]
    for item in history:
        if item.get('mappedEventId') in removed:
            item['mappedEventId'] = primary['id']
    return len(removed)


def main():
    data = json.loads(EVENTS.read_text(encoding='utf-8'))
    archive = json.loads(HISTORY.read_text(encoding='utf-8'))
    cache = json.loads(CACHE.read_text(encoding='utf-8'))
    events = data['events']
    vologda = [item for item in events if item['region'] == 'Вологодская область'
               and item['eventDate'] == '2026-09-24' and item['type'] == 'attack']
    if vologda:
        primary = next((item for item in vologda if 'охотник' in item['title']), vologda[0])
        removed_vologda = merge(events, archive['records'], primary, [item for item in vologda if item is not primary])
        point = geocode('Ивановское, Усть-Кубинский округ, Вологодская область', cache)
        if point and 'Вологод' in point['region']:
            primary['place'] = 'окрестности деревни Ивановское'
            primary['longitude'], primary['latitude'] = point['longitude'], point['latitude']
            primary['precision'] = 'Точка обозначает центр деревни Ивановское; нападение произошло в лесничестве рядом, точные координаты неизвестны.'
        primary['title'] = 'Медведь напал на охотника в Вологодской области'
        primary['summary'] = ('По предварительным данным Следственного комитета, 73-летний житель села Устье 22 сентября отправился на охоту '
                              'в лесничество в районе деревни Ивановское Усть-Кубинского округа. В лесу на него напал медведь; мужчина погиб. '
                              'Следователи устанавливают обстоятельства происшествия. Точная дата нападения в сообщении не указана.')
        primary['dateBasis'] = 'publication'
        primary['status'] = 'Сверено с региональной публикацией со ссылкой на Следственный комитет'
        primary['source'] = 'Вологда Регион'
        primary['sourceUrl'] = 'https://www.vologdaregion.ru/public/news/2026/9/24/v-vologodskoy-oblasti-medved-razorval-73-letnego-ohotnika'
    else:
        removed_vologda = 0
    tuva_primary = next((item for item in events if item['id'] == 'auto-5a5b3a4232306497'), None)
    if tuva_primary:
        tuva_extras = [item for item in events if item['region'] == 'Республика Тыва'
                       and item['eventDate'] == '2026-09-24' and item['type'] == 'attack'
                       and any(word in item['title'].lower() for word in ('турист', 'москвич', 'отец', 'хоккеист', 'тренер', 'мужчина'))]
        removed_tuva = merge(events, archive['records'], tuva_primary, tuva_extras)
    else:
        removed_tuva = 0
    now = datetime.now(timezone.utc).isoformat(timespec='seconds')
    data['updatedAt'] = now
    archive['updatedAt'] = now
    data['events'].sort(key=lambda item: item['eventDate'], reverse=True)
    EVENTS.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    HISTORY.write_text(json.dumps(archive, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    CACHE.write_text(json.dumps(cache, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(f'Merged Vologda duplicates: {removed_vologda}; Tuva duplicates: {removed_tuva}')


if __name__ == '__main__':
    main()
