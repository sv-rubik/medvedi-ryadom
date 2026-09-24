"""Daily discovery of bear reports and related news for the static site."""

from __future__ import annotations

import hashlib
import html
import json
import re
import sys
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from html.parser import HTMLParser
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EVENTS = ROOT / "dist" / "events.json"
NEWS = ROOT / "dist" / "news.json"
HISTORY = ROOT / "dist" / "history.json"
CACHE = ROOT / "data" / "geocode-cache.json"
BING = "https://www.bing.com/news/search?"
MSK = timezone(timedelta(hours=3))
USER_AGENT = "MedvediRyadom/1.0 (+https://github.com/sv-rubik/medvedi-ryadom)"
QUERIES = [
    'медведь', 'медведи',
] + [f'медведь site:{site}' for site in (
    'ria.ru', 'tass.ru', 'rbc.ru', 'interfax.ru',
    'kommersant.ru', 'lenta.ru', 'rg.ru',
)]

# Inflected names in headlines need explicit normalization before geocoding.
# Locations not resolved to a settlement or administrative region are skipped.
ALIASES = {
    'приморье': 'Приморский край', 'приморском крае': 'Приморский край',
    'хабаровском крае': 'Хабаровский край', 'камчатке': 'Камчатский край',
    'камчатском крае': 'Камчатский край', 'туве': 'Республика Тыва',
    'тыве': 'Республика Тыва', 'якутии': 'Республика Саха (Якутия)',
    'бурятии': 'Республика Бурятия', 'карелии': 'Республика Карелия',
    'алтае': 'Республика Алтай', 'сахалине': 'Сахалинская область',
    'чукотке': 'Чукотский автономный округ', 'приангарье': 'Иркутская область',
    'забайкалье': 'Забайкальский край', 'кузбассе': 'Кемеровская область',
    'подмосковье': 'Московская область', 'татарстане': 'Республика Татарстан',
    'томске': 'Томск', 'благовещенске': 'Благовещенск',
    'иркутске': 'Иркутск', 'красноярске': 'Красноярск',
    'магадане': 'Магадан', 'петропавловске-камчатском': 'Петропавловск-Камчатский',
    'усть-камчатске': 'Усть-Камчатск', 'мурманске': 'Мурманск',
    'хабаровске': 'Хабаровск', 'владивостоке': 'Владивосток',
    'южно-сахалинске': 'Южно-Сахалинск', 'новосибирске': 'Новосибирск',
}
BEAR = re.compile(r'\bмедвед(?:ь|я|ю|ем|и|ей|ям|ями|ях)|\bмедвеж(?:ий|ья|ьи|ьего|ьей|ьих)', re.I)
ENCOUNTER = re.compile(
    r'напад|атаков|покус|загрыз|задр|растерза|ранил|погиб|убил|покалечил|жертв|'
    r'выш(?:ел|ли|ла)|выход|заметил|замечен|встрет|увидел|видели|'
    r'забрел|забрался|зашел|залез|захватил|бродил|бродит|гулял|появил|пришел|пробрался|'
    r'преслед|отпуг|прогнал|загнал|осаду|охотят|спас|обнаружил|застрелил|ликвидир', re.I
)
ATTACK = re.compile(r'напад|атаков|покус|загрыз|задр|растерза|ранил|погиб|убил|покалечил|жертв', re.I)
REJECT = re.compile(
    r'медведев|зоопарк|цирк|мультфильм|маша и медведь|игрушечн|'
    r'бирж|рынк|акци|крипто|хоккей|футбол|панда|спектакл|'
    r'как себя вести|что делать при встрече|правила поведения', re.I
)
MULTIPLE = re.compile(r'\b\d+\s+(?:сообщени|случа|встреч)', re.I)
GENERAL_NEWS = re.compile(r'число погибших|сколько было|по всей россии|за фото|оштраф|наказал', re.I)
PLACE_PATTERN = re.compile(
    r'\b(?:в|во|на|под|около|возле)\s+([А-ЯЁ][а-яё-]+(?:-[А-ЯЁа-яё-]+)?'
    r'(?:\s+(?:области|крае|республике|районе|округе))?)'
)
BAD_PLACES = {'России', 'Сибири', 'лесу', 'городе', 'поселке', 'селе', 'тайге', 'горах', 'регионе'}


def get(url: str, timeout: int = 20) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return response.read()


class ArticleParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.description = ''
        self.article_depth = 0
        self.paragraph = None
        self.paragraphs = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == 'meta' and attrs.get('property') == 'og:description':
            self.description = attrs.get('content', '')
        if tag == 'article':
            self.article_depth += 1
        if tag == 'p' and self.article_depth:
            self.paragraph = []

    def handle_data(self, data):
        if self.paragraph is not None:
            self.paragraph.append(data)

    def handle_endtag(self, tag):
        if tag == 'p' and self.paragraph is not None:
            value = ' '.join(''.join(self.paragraph).split())
            if len(value) > 65:
                self.paragraphs.append(value)
            self.paragraph = None
        if tag == 'article' and self.article_depth:
            self.article_depth -= 1


def article_summary(url: str, feed_description: str, fetch_full: bool = False) -> str:
    fallback = ' '.join(html.unescape(re.sub(r'<[^>]+>', ' ', feed_description)).split())
    if not fetch_full:
        return fallback or 'Подробности — в публикации источника.'
    try:
        parser = ArticleParser()
        parser.feed(get(url, timeout=2).decode('utf-8', errors='replace')[:1_000_000])
        paragraphs = parser.paragraphs[:3]
        if paragraphs:
            result = ' '.join(paragraphs)
        else:
            result = parser.description or fallback
    except Exception as exc:
        print(f'Article text unavailable for {url}: {exc}', file=sys.stderr)
        result = fallback
    result = ' '.join(html.unescape(result).split())
    if result.endswith('...'):
        unfinished = result[:-3].rstrip()
        sentence_end = unfinished.rfind('. ')
        result = unfinished[:sentence_end + 1] if sentence_end > 90 else unfinished + '…'
    if len(result) > 650:
        result = result[:650].rsplit(' ', 1)[0] + '…'
    return result or 'Текст публикации недоступен; подробности — по ссылке на источник.'


def key_words(title: str) -> set[str]:
    return {word[:6] for word in re.findall(r'[а-яё]{5,}', title.casefold())
            if not word.startswith(('медвед', 'напад', 'погиб', 'мужчин', 'камчат', 'област', 'крае'))}


def same_incident(existing: dict, article: dict, point: dict, kind: str) -> bool:
    if existing.get('type') != kind or existing.get('region') != point['region']:
        return False
    days = abs((datetime.fromisoformat(existing['eventDate']) - datetime.fromisoformat(article['published'])).days)
    if days > 7:
        return False
    if not existing['id'].startswith('auto-'):
        place_stem = existing['place'].casefold()[:5]
        return place_stem in (article['title'] + ' ' + article['feedDescription']).casefold()
    if days > 2:
        return False
    first, second = key_words(existing['title']), key_words(article['title'])
    return len(first & second) >= 2 or (point['place'] != point['region'] and existing.get('place') == point['place'])


def add_secondary_source(event: dict, article: dict) -> None:
    if article['sourceUrl'] == event['sourceUrl']:
        return
    extra = event.setdefault('additionalSources', [])
    if any(item['sourceUrl'] == article['sourceUrl'] for item in extra):
        return
    extra.append({'source': article['source'], 'sourceUrl': article['sourceUrl']})
    if event['id'].startswith('auto-') and len(event['summary']) < 400:
        detail = article_summary(article['sourceUrl'], article['feedDescription'])
        if detail and detail[:60] not in event['summary']:
            event['summary'] = (event['summary'] + '\nДополнительно: ' + detail)[:650]


def strip_source(title: str, source: str) -> str:
    suffix = ' - ' + source
    return title[:-len(suffix)].strip() if title.endswith(suffix) else title.strip()


def relevant(title: str) -> bool:
    return bool(BEAR.search(title) and ENCOUNTER.search(title)
                and not REJECT.search(title) and not MULTIPLE.search(title)
                and not GENERAL_NEWS.search(title))


def report_related(title: str) -> bool:
    return bool(BEAR.search(title) and ENCOUNTER.search(title) and not REJECT.search(title))


def bear_news(title: str) -> bool:
    return bool(BEAR.search(title) and not REJECT.search(title))


def location_candidates(title: str) -> list[str]:
    candidates = []
    lowered = title.lower()
    for alias, normal in ALIASES.items():
        if re.search(r'(?<!\w)' + re.escape(alias) + r'(?!\w)', lowered):
            candidates.append(normal)
    for match in PLACE_PATTERN.finditer(title):
        name = match.group(1)
        if name.split()[0] not in BAD_PLACES:
            candidates.append(name)
    return list(dict.fromkeys(candidates))


def geocode(place: str, cache: dict) -> dict | None:
    key = place.casefold()
    if key in cache:
        return cache[key]
    params = urllib.parse.urlencode({
        'q': f'{place}, Россия', 'format': 'jsonv2', 'addressdetails': '1',
        'countrycodes': 'ru', 'limit': '5',
    })
    # The public Nominatim service permits at most one request per second.
    time.sleep(1.1)
    try:
        results = json.loads(get('https://nominatim.openstreetmap.org/search?' + params))
    except Exception as exc:
        print(f'Geocoding failed for {place}: {exc}', file=sys.stderr)
        return None
    accepted = None
    for result in results:
        address = result.get('address', {})
        kind = result.get('type', '')
        if result.get('category') == 'place' and kind in ('city', 'town', 'village', 'hamlet'):
            accepted = result
            break
        if result.get('category') == 'boundary' and kind == 'administrative' and any(
            address.get(k) for k in ('state', 'region', 'county')
        ):
            accepted = result
            break
    if not accepted:
        cache[key] = None
        return None
    address = accepted['address']
    value = {
        'place': address.get('city') or address.get('town') or address.get('village')
                 or address.get('hamlet') or address.get('state') or address.get('region') or place,
        'region': address.get('state') or address.get('region') or address.get('county') or 'Россия',
        'longitude': float(accepted['lon']), 'latitude': float(accepted['lat']),
    }
    cache[key] = value
    return value


def collect(target_date=None) -> list[dict]:
    items = {}
    successes = 0
    target_date = target_date or datetime.now(MSK).date()
    for query in QUERIES:
        url = BING + urllib.parse.urlencode({'q': query, 'format': 'rss', 'mkt': 'ru-RU'})
        try:
            root = ET.fromstring(get(url))
            successes += 1
        except Exception as exc:
            print(f'RSS failed for {query}: {exc}', file=sys.stderr)
            continue
        for item in root.findall('./channel/item'):
            source = next((child for child in item if child.tag.endswith('Source')), None)
            source_name = source.text if source is not None and source.text else 'СМИ'
            title = strip_source(item.findtext('title', ''), source_name)
            indexed_link = item.findtext('link', '')
            link = urllib.parse.parse_qs(urllib.parse.urlsplit(indexed_link).query).get('url', [''])[0]
            try:
                published = parsedate_to_datetime(item.findtext('pubDate', '')).astimezone(timezone.utc)
            except (TypeError, ValueError):
                continue
            if published.astimezone(MSK).date() != target_date:
                continue
            if not bear_news(title) or not link.startswith('https://'):
                continue
            key = re.sub(r'\W+', ' ', title.casefold()).strip()
            items.setdefault(key, {
                'title': title, 'source': source_name, 'sourceUrl': link,
                'published': target_date.isoformat(),
                'feedDescription': item.findtext('description', ''),
            })
    if not successes:
        raise RuntimeError('All news searches failed; data was not changed')
    print(f'News searches succeeded: {successes}/{len(QUERIES)}; matching headlines: {len(items)}')
    return list(items.values())


def update() -> None:
    data = json.loads(EVENTS.read_text(encoding='utf-8'))
    news = json.loads(NEWS.read_text(encoding='utf-8')) if NEWS.exists() else {'updatedAt': '', 'articles': []}
    history = json.loads(HISTORY.read_text(encoding='utf-8'))
    cache = json.loads(CACHE.read_text(encoding='utf-8')) if CACHE.exists() else {}
    existing = {item.get('sourceUrl') for item in data['events']}
    ignored = set(data.get('ignoredUrls', []))
    known_news = {item.get('sourceUrl') for item in news['articles']}
    ignored_news = set(news.get('ignoredUrls', []))
    known_history = {item['sourceUrl'] for item in history['records']} | set(history.get('ignoredUrls', []))
    added = 0
    news_added = 0
    history_added = 0
    unlocated = 0
    for article in collect():
        if not report_related(article['title']):
            if article['sourceUrl'] not in known_news and article['sourceUrl'] not in ignored_news:
                record = {
                    'id': 'news-' + hashlib.sha256(article['sourceUrl'].encode()).hexdigest()[:16],
                    'title': article['title'], 'publishedAt': article['published'],
                    'source': article['source'], 'sourceUrl': article['sourceUrl'],
                    'summary': article_summary(article['sourceUrl'], article['feedDescription']),
                }
                news['articles'].append(record)
                known_news.add(article['sourceUrl'])
                news_added += 1
            continue
        def save_to_history():
            nonlocal history_added
            if article['sourceUrl'] in known_history:
                return
            history['records'].append({
                'id': 'report-' + hashlib.sha256(article['sourceUrl'].encode()).hexdigest()[:16],
                'title': article['title'], 'publishedAt': article['published'],
                'source': article['source'], 'sourceUrl': article['sourceUrl'],
                'summary': article_summary(article['sourceUrl'], article['feedDescription']),
            })
            known_history.add(article['sourceUrl'])
            history_added += 1
        if not relevant(article['title']):
            save_to_history()
            continue
        if article['sourceUrl'] in existing or article['sourceUrl'] in ignored:
            continue
        point = None
        for candidate in location_candidates(article['title']):
            point = geocode(candidate, cache)
            if point:
                break
        if not point:
            save_to_history()
            unlocated += 1
            continue
        kind = 'attack' if ATTACK.search(article['title']) else 'sighting'
        duplicate = next((event for event in data['events'] if same_incident(event, article, point, kind)), None)
        if duplicate:
            add_secondary_source(duplicate, article)
            existing.add(article['sourceUrl'])
            continue
        identifier = hashlib.sha256(article['sourceUrl'].encode()).hexdigest()[:16]
        record = {
            'id': 'auto-' + identifier, 'type': kind,
            'eventDate': article['published'], 'dateBasis': 'publication',
            'place': point['place'], 'region': point['region'],
            'title': article['title'],
            'summary': article_summary(article['sourceUrl'], article['feedDescription'], fetch_full=True),
            'longitude': point['longitude'], 'latitude': point['latitude'],
            'precision': 'Автоматически определён центр населённого пункта или региона. Точное место не проверено.',
            'status': 'Автоматически найдено, не проверено',
            'source': article['source'], 'sourceUrl': article['sourceUrl'],
        }
        data['events'].append(record)
        existing.add(article['sourceUrl'])
        added += 1
    now = datetime.now(timezone.utc).isoformat(timespec='seconds')
    data['lastSearchAt'] = now
    news['lastSearchAt'] = now
    history['lastSearchAt'] = now
    if added:
        data['updatedAt'] = now
    if news_added:
        news['updatedAt'] = now
    if history_added:
        history['updatedAt'] = now
    news['articles'].sort(key=lambda item: item['publishedAt'], reverse=True)
    news['articles'] = news['articles'][:200]
    history['records'].sort(key=lambda item: item['publishedAt'], reverse=True)
    EVENTS.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    NEWS.write_text(json.dumps(news, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    HISTORY.write_text(json.dumps(history, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    CACHE.parent.mkdir(exist_ok=True)
    CACHE.write_text(json.dumps(cache, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(f'Added map points: {added}; other news: {news_added}; archived reports: {history_added}; encounters without a reliable place: {unlocated}')


if __name__ == '__main__':
    update()
