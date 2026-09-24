(function () {
  const list = document.getElementById('news-list');
  const search = document.getElementById('news-search');
  const count = document.getElementById('news-count');
  const updated = document.getElementById('news-updated');
  let articles = [];
  const dataBase = location.hostname.endsWith('chatgpt.site') ? 'https://sv-rubik.github.io/medvedi-ryadom/' : './';
  const dateLabel = (date) => new Intl.DateTimeFormat('ru-RU', { day: 'numeric', month: 'long', year: 'numeric', timeZone: 'UTC' }).format(new Date(date + 'T12:00:00Z'));
  function render() {
    const query = search.value.trim().toLocaleLowerCase('ru');
    const filtered = articles.filter((item) => [item.title, item.summary, item.source].some((value) => value.toLocaleLowerCase('ru').includes(query)));
    count.textContent = `${filtered.length} публикаций`;
    list.replaceChildren();
    if (!filtered.length) {
      const empty = document.createElement('div');
      empty.className = 'news-empty';
      empty.textContent = articles.length ? 'По запросу ничего не найдено.' : 'Подборка пока пуста. Поиск выполняется ежедневно.';
      list.append(empty);
      return;
    }
    for (const item of filtered) {
      const card = document.createElement('article');
      card.className = 'news-item';
      const meta = document.createElement('div');
      meta.className = 'news-meta';
      meta.textContent = `${dateLabel(item.publishedAt)} · ${item.source}`;
      const h2 = document.createElement('h2');
      const title = document.createElement('a');
      title.href = item.sourceUrl;
      title.target = '_blank';
      title.rel = 'noopener noreferrer';
      title.textContent = item.title;
      h2.append(title);
      const summary = document.createElement('p');
      summary.textContent = item.summary;
      const source = document.createElement('a');
      source.className = 'source-link';
      source.href = item.sourceUrl;
      source.target = '_blank';
      source.rel = 'noopener noreferrer';
      source.textContent = `Читать в источнике: ${item.source} ↗`;
      card.append(meta, h2, summary, source);
      list.append(card);
    }
  }
  search.addEventListener('input', render);
  fetch(dataBase + 'news.json', { cache: 'no-cache' }).then((response) => {
    if (!response.ok) throw new Error('News data unavailable');
    return response.json();
  }).then((data) => {
    articles = data.articles || [];
    render();
    updated.textContent = data.lastSearchAt ? `Последний поиск: ${new Date(data.lastSearchAt).toLocaleString('ru-RU')}` : 'Ежедневный поиск ещё не запускался.';
  }).catch(() => {
    list.textContent = 'Новости временно не загрузились. Попробуйте позже.';
  });
})();
