"""Keep only the supplied incident rows, without nonfunctional ChatGPT citations."""

import re
from pathlib import Path

path = Path(__file__).resolve().parents[1] / 'data' / 'curated-2016-2026.md'
rows = [re.sub(r'\s*:chatgpt-content-reference\{index="\d+"\}', '', line)
        for line in path.read_text(encoding='utf-8').splitlines()
        if line.startswith('| ') and not line.startswith('| Дата') and not line.startswith('|---')]
path.write_text(
    '# Пользовательский перечень случаев, 2016–2026\n\n'
    'Это исходные сведения для геопривязки. Названия СМИ перенесены из присланного списка; '
    'часть ссылок и деталей требует проверки. Сводные показатели без единого места не превращаются в отдельные точки.\n\n'
    '| Дата или период | Место | Описание | Источник, указанный в списке |\n'
    '|---|---|---|---|\n' + '\n'.join(rows) + '\n', encoding='utf-8')
print(f'Saved {len(rows)} supplied rows')
