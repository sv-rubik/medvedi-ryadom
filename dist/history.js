(function () {
  const list = document.getElementById('history-list');
  const search = document.getElementById('history-search');
  const year = document.getElementById('history-year');
  const count = document.getElementById('history-count');
  let records = [];
  const dataBase = location.hostname.endsWith('chatgpt.site') ? 'https://sv-rubik.github.io/medvedi-ryadom/' : './';
  const dateLabel = (value) => new Intl.DateTimeFormat('ru-RU', { day: 'numeric', month: 'long', year: 'numeric', timeZone: 'UTC' }).format(new Date(value + 'T12:00:00Z'));
  function render() {
    const query = search.value.trim().toLocaleLowerCase('ru');
    const filtered = records.filter((item) =>
      (year.value === 'all' || item.publishedAt.startsWith(year.value)) &&
      [item.title, item.source].some((value) => value.toLocaleLowerCase('ru').includes(query))
    );
    count.textContent = `${filtered.length} публикаций`;
    list.replaceChildren();
    if (!filtered.length) {
      const empty = document.createElement('div');
      empty.className = 'news-empty';
      empty.textContent = 'По выбранным условиям публикаций нет.';
      list.append(empty);
      return;
    }
    for (const item of filtered.slice(0, 300)) {
      const card = document.createElement('article');
      card.className = 'news-item';
      const meta = document.createElement('div');
      meta.className = 'news-meta';
      meta.textContent = `${dateLabel(item.publishedAt)} · ${item.source}`;
      const h2 = document.createElement('h2');
      const link = document.createElement('a');
      link.href = item.sourceUrl;
      link.target = '_blank';
      link.rel = 'noopener noreferrer';
      link.textContent = item.title;
      h2.append(link);
      const summary = document.createElement('p');
      summary.textContent = item.summary;
      card.append(meta, h2, summary);
      list.append(card);
    }
    if (filtered.length > 300) {
      const hint = document.createElement('p');
      hint.className = 'news-foot';
      hint.textContent = 'Показаны первые 300 записей. Уточните год или запрос для остальных.';
      list.append(hint);
    }
  }
  search.addEventListener('input', render);
  year.addEventListener('change', render);
  fetch(dataBase + 'history.json', { cache: 'no-cache' }).then((response) => {
    if (!response.ok) throw new Error('History data unavailable');
    return response.json();
  }).then((data) => {
    records = data.records || [];
    const years = [...new Set(records.map((item) => item.publishedAt.slice(0, 4)))].sort().reverse();
    year.replaceChildren();
    const all = document.createElement('option');
    all.value = 'all'; all.textContent = 'Все годы'; year.append(all);
    years.forEach((value) => { const option = document.createElement('option'); option.value = value; option.textContent = value; year.append(option); });
    year.value = 'all';
    render();
    document.getElementById('history-updated').textContent = data.lastSearchAt ? `Последний поиск: ${new Date(data.lastSearchAt).toLocaleString('ru-RU')}` : '';
  }).catch(() => { list.textContent = 'Архив временно недоступен.'; });
})();
