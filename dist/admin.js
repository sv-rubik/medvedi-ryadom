(function () {
  const api = 'https://api.github.com/repos/sv-rubik/medvedi-ryadom/contents/dist/';
  const form = document.getElementById('admin-form');
  const fields = form.elements;
  const status = document.getElementById('admin-status');
  const list = document.getElementById('admin-list');
  let token = '';
  let section = 'events';
  let files = {};
  let selectedId = null;
  const fileName = () => section + '.json';
  const collectionName = () => section === 'events' ? 'events' : section === 'news' ? 'articles' : 'records';
  const current = () => files[section].data[collectionName()];
  const encode = (value) => {
    const bytes = new TextEncoder().encode(value);
    let binary = '';
    for (const byte of bytes) binary += String.fromCharCode(byte);
    return btoa(binary);
  };
  const decode = (value) => {
    const binary = atob(value.replace(/\s/g, ''));
    return new TextDecoder().decode(Uint8Array.from(binary, (char) => char.charCodeAt(0)));
  };
  async function request(url, options = {}) {
    const response = await fetch(url, {
      ...options,
      headers: { 'Accept': 'application/vnd.github+json', 'Authorization': `Bearer ${token}`, 'X-GitHub-Api-Version': '2022-11-28', ...(options.headers || {}) },
      cache: 'no-store'
    });
    if (!response.ok) {
      const body = await response.json().catch(() => ({}));
      throw new Error(`${response.status}: ${body.message || 'GitHub не принял запрос'}`);
    }
    return response.json();
  }
  async function load() {
    for (const name of ['events', 'history', 'news']) {
      const response = await request(api + name + '.json?ref=main');
      // The Contents API omits inline content once a file exceeds 1 MB.
      const content = response.content || (await request(response.git_url)).content;
      files[name] = { sha: response.sha, data: JSON.parse(decode(content)) };
    }
    document.getElementById('admin-workspace').hidden = false;
    setSection(section);
    status.textContent = 'Данные загружены. Изменения станут видны после публикации GitHub Pages.';
  }
  document.getElementById('connect').addEventListener('click', async () => {
    token = document.getElementById('token').value.trim();
    document.getElementById('token').value = '';
    if (!token) { status.textContent = 'Введите GitHub-токен.'; return; }
    status.textContent = 'Проверка доступа…';
    try {
      const user = await request('https://api.github.com/user');
      if (user.login.toLowerCase() !== 'sv-rubik') throw new Error('Нужен доступ GitHub-аккаунта sv-rubik.');
      await load();
    } catch (error) { token = ''; status.textContent = `Не удалось открыть данные: ${error.message}`; }
  });
  function setSection(name) {
    section = name;
    selectedId = null;
    document.getElementById('tab-events').classList.toggle('active', name === 'events');
    document.getElementById('tab-history').classList.toggle('active', name === 'history');
    document.getElementById('tab-news').classList.toggle('active', name === 'news');
    document.getElementById('event-fields').hidden = name !== 'events';
    document.getElementById('promote-item').hidden = name !== 'history';
    form.reset();
    renderList();
    if (current().length) select(current()[0].id);
  }
  function renderList() {
    list.replaceChildren();
    const dateKey = section === 'events' ? 'eventDate' : 'publishedAt';
    const query = document.getElementById('admin-search').value.trim().toLocaleLowerCase('ru');
    const matching = [...current()].filter((item) =>
      !query || [item.title, item.source, item.place, item.region].some((value) =>
        String(value || '').toLocaleLowerCase('ru').includes(query))
    ).sort((a, b) => b[dateKey].localeCompare(a[dateKey]));
    for (const item of matching.slice(0, 150)) {
      const button = document.createElement('button');
      button.type = 'button';
      button.className = item.id === selectedId ? 'active' : '';
      button.setAttribute('role', 'listitem');
      button.textContent = item.title;
      const small = document.createElement('small');
      small.textContent = `${item[dateKey]} · ${item.source}`;
      button.append(small);
      button.addEventListener('click', () => select(item.id));
      list.append(button);
    }
    if (matching.length > 150) {
      const hint = document.createElement('p');
      hint.textContent = `Показаны 150 из ${matching.length}. Уточните поиск.`;
      list.append(hint);
    }
  }
  document.getElementById('admin-search').addEventListener('input', renderList);
  function select(id) {
    selectedId = id;
    const item = current().find((entry) => entry.id === id);
    if (!item) return;
    fields.id.value = item.id;
    fields.title.value = item.title || '';
    fields.date.value = item.eventDate || item.publishedAt || '';
    fields.summary.value = item.summary || '';
    fields.source.value = item.source || '';
    fields.sourceUrl.value = item.sourceUrl || '';
    if (section === 'events') {
      fields.type.value = item.type || 'sighting';
      fields.place.value = item.place || '';
      fields.region.value = item.region || '';
      fields.latitude.value = item.latitude ?? '';
      fields.longitude.value = item.longitude ?? '';
      fields.precision.value = item.precision || '';
      fields.status.value = item.status || '';
      fields.dateBasis.value = item.dateBasis || 'event';
    }
    renderList();
  }
  document.getElementById('tab-events').addEventListener('click', () => setSection('events'));
  document.getElementById('tab-history').addEventListener('click', () => setSection('history'));
  document.getElementById('tab-news').addEventListener('click', () => setSection('news'));
  document.getElementById('promote-item').addEventListener('click', () => {
    const item = current().find((entry) => entry.id === selectedId);
    if (!item) return;
    setSection('events');
    selectedId = null;
    fields.id.value = '';
    fields.title.value = item.title;
    fields.date.value = item.publishedAt;
    fields.summary.value = 'Дополните карточку фактами из публикации и проверьте дату происшествия.';
    fields.source.value = item.source;
    fields.sourceUrl.value = item.sourceUrl;
    fields.dateBasis.value = 'publication';
    fields.title.focus();
  });
  document.getElementById('add-item').addEventListener('click', () => {
    selectedId = null;
    form.reset();
    fields.id.value = '';
    renderList();
    fields.title.focus();
  });
  async function saveFile(message) {
    const file = files[section];
    file.data.updatedAt = new Date().toISOString();
    const response = await request(api + fileName(), {
      method: 'PUT', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message, branch: 'main', sha: file.sha, content: encode(JSON.stringify(file.data, null, 2) + '\n') })
    });
    file.sha = response.content.sha;
  }
  form.addEventListener('submit', async (event) => {
    event.preventDefault();
    if (!token) { status.textContent = 'Сначала откройте данные с GitHub-токеном.'; return; }
    try {
      const url = new URL(fields.sourceUrl.value);
      if (url.protocol !== 'https:') throw new Error('Ссылка на источник должна начинаться с https://');
      const id = fields.id.value || `manual-${crypto.randomUUID()}`;
      let item = current().find((entry) => entry.id === id);
      if (!item) { item = { id }; current().unshift(item); }
      Object.assign(item, {
        title: fields.title.value.trim(), summary: fields.summary.value.trim(),
        source: fields.source.value.trim(), sourceUrl: url.href,
      });
      if (section === 'events') {
        const latitude = Number(fields.latitude.value);
        const longitude = Number(fields.longitude.value);
        if (!fields.place.value.trim() || !fields.region.value.trim() ||
            !fields.latitude.value || !fields.longitude.value ||
            latitude < -90 || latitude > 90 || longitude < -180 || longitude > 180) {
          throw new Error('Для точки нужны место, регион и правильные координаты.');
        }
        Object.assign(item, {
          eventDate: fields.date.value, type: fields.type.value,
          place: fields.place.value.trim(), region: fields.region.value.trim(),
          latitude, longitude, precision: fields.precision.value.trim(),
          status: fields.status.value.trim(),
        });
        if (fields.dateBasis.value === 'publication') item.dateBasis = 'publication';
        else delete item.dateBasis;
      } else item.publishedAt = fields.date.value;
      status.textContent = 'Сохранение…';
      await saveFile(`${section === 'events' ? 'Edit map report' : 'Edit bear news'}: ${item.title.slice(0, 60)}`);
      selectedId = id;
      renderList();
      status.textContent = 'Сохранено в GitHub. Публикация сайта начнётся автоматически.';
    } catch (error) {
      status.textContent = `Не удалось сохранить: ${error.message}. При конфликте обновите данные кнопкой «Открыть данные».`;
      await load().catch(() => {});
    }
  });
  document.getElementById('delete-item').addEventListener('click', async () => {
    if (!selectedId || !token) return;
    const index = current().findIndex((entry) => entry.id === selectedId);
    if (index < 0) return;
    const item = current()[index];
    if (!confirm(`Удалить «${item.title}» с сайта? Запись в CSV-архиве сохранится.`)) return;
    current().splice(index, 1);
    const ignored = files[section].data.ignoredUrls ||= [];
    if (item.sourceUrl && !ignored.includes(item.sourceUrl)) ignored.push(item.sourceUrl);
    try {
      status.textContent = 'Удаление…';
      await saveFile(`Remove ${section === 'events' ? 'map report' : 'bear news'}: ${item.title.slice(0, 60)}`);
      selectedId = null;
      renderList();
      if (current().length) select(current()[0].id);
      else form.reset();
      status.textContent = 'Удалено с сайта. Запись в CSV-архиве осталась.';
    } catch (error) {
      status.textContent = `Не удалось удалить: ${error.message}`;
      await load().catch(() => {});
    }
  });
})();
