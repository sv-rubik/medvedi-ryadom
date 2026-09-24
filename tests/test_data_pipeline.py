import hashlib
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))

from import_curated import find_existing, parsed_date, rows  # noqa: E402
from update_news import ATTACK, location_candidates, relevant  # noqa: E402


class DataPipelineTests(unittest.TestCase):
    def test_russian_location_and_attack_inflections(self):
        headline = 'Медведь напал на охотника в Вологодской области'
        self.assertTrue(relevant(headline))
        self.assertTrue(ATTACK.search(headline))
        self.assertEqual(location_candidates(headline)[0], 'Вологодская область')
        self.assertEqual(location_candidates('В Туве погиб турист из Якутии')[0], 'Республика Тыва')

    def test_editorial_summary_is_not_an_incident(self):
        self.assertFalse(relevant('Почему медведи выходят к людям в Бурятии: мнение охотоведа'))
        self.assertFalse(relevant('Карта выхода медведей в Алтайском крае за год'))

    def test_partial_dates_are_marked(self):
        self.assertEqual(parsed_date('31.08–16.09.2026'), ('2026-08-31', 'range'))
        self.assertEqual(parsed_date('сентябрь 2025'), ('2025-09-01', 'month'))
        self.assertEqual(parsed_date('2026'), ('2026-01-01', 'year'))

    def test_every_supplied_place_has_a_map_event(self):
        events = json.loads((ROOT / 'dist' / 'events.json').read_text(encoding='utf-8'))['events']
        ids = {item['id'] for item in events}
        self.assertEqual(len(ids), len(events))
        self.assertEqual(sum(item['id'].startswith('curated-split-') for item in events), 6)
        supplied = list(rows())
        self.assertEqual(len(supplied), 79)
        for raw_date, location, summary, _ in supplied:
            if location.startswith(('Россия, 41 регион', 'Сахалин и Курильские острова')):
                continue
            identifier = 'curated-' + hashlib.sha256((raw_date + location + summary).encode()).hexdigest()[:16]
            self.assertTrue(identifier in ids or find_existing(events, parsed_date(raw_date)[0], location, summary), location)
        vologda = [item for item in events if item['region'] == 'Вологодская область'
                   and item['eventDate'] == '2026-09-24' and item['type'] == 'attack']
        self.assertEqual(len(vologda), 1)
        self.assertIn('vologdaregion.ru', vologda[0]['sourceUrl'])
        archive = json.loads((ROOT / 'dist' / 'history.json').read_text(encoding='utf-8'))['records']
        self.assertTrue(all(item.get('mappedEventId') in ids for item in archive if item.get('mappedEventId')))


if __name__ == '__main__':
    unittest.main()
