(function () {
  'use strict';

  const $ = (id) => document.getElementById(id);
  const yearSelect = $('year');
  const searchInput = $('search');
  const sightingInput = $('filter-sighting');
  const attackInput = $('filter-attack');
  const eventList = $('event-list');
  const detailPanel = $('detail-panel');
  const aboutPanel = $('about-panel');
  const currentYear = Number(new Intl.DateTimeFormat('en-US', { timeZone: 'Europe/Moscow', year: 'numeric' }).format(new Date()));
  const state = { events: [], selectedId: null, map: null, mapReady: false };

  const allOption = document.createElement('option');
  allOption.value = 'all';
  allOption.textContent = 'Все годы';
  yearSelect.append(allOption);
  for (let year = currentYear; year >= 1991; year -= 1) {
    const option = document.createElement('option');
    option.value = String(year);
    option.textContent = String(year);
    yearSelect.append(option);
  }
  yearSelect.value = String(currentYear);

  const formatDate = (date) => new Intl.DateTimeFormat('ru-RU', { day: 'numeric', month: 'long', year: 'numeric', timeZone: 'UTC' }).format(new Date(date + 'T12:00:00Z'));
  const typeLabel = (type) => type === 'attack' ? 'Нападение' : 'Выход к людям';
  const selectedYear = () => yearSelect.value;
  const filteredEvents = () => {
    const query = searchInput.value.trim().toLocaleLowerCase('ru');
    return state.events.filter((event) =>
      (selectedYear() === 'all' || event.eventDate.slice(0, 4) === selectedYear()) &&
      ((event.type === 'attack' && attackInput.checked) || (event.type === 'sighting' && sightingInput.checked)) &&
      (!query || [event.place, event.region, event.title, event.summary].some((value) => value.toLocaleLowerCase('ru').includes(query)))
    ).sort((a, b) => b.eventDate.localeCompare(a.eventDate));
  };

  function updateMap(events) {
    if (!state.mapReady) return;
    const source = state.map.getSource('events');
    if (!source) return;
    source.setData({
      type: 'FeatureCollection',
      features: events.map((event) => ({
        type: 'Feature',
        geometry: { type: 'Point', coordinates: [event.longitude, event.latitude] },
        properties: { id: event.id, type: event.type, title: event.title }
      }))
    });
  }

  function showDetail(event, moveMap) {
    if (!event) return;
    state.selectedId = event.id;
    aboutPanel.hidden = true;
    $('about-trigger').setAttribute('aria-expanded', 'false');
    detailPanel.hidden = false;
    const root = $('detail-content');
    root.replaceChildren();
    const kind = document.createElement('div');
    kind.className = 'detail-type ' + event.type;
    kind.textContent = (event.type === 'attack' ? '●  ' : '▲  ') + typeLabel(event.type);
    const title = document.createElement('h2');
    title.textContent = event.title;
    const place = document.createElement('p');
    place.className = 'detail-place';
    place.textContent = event.place + ' · ' + event.region;
    const date = document.createElement('p');
    date.className = 'detail-date';
    date.textContent = formatDate(event.eventDate);
    const label = document.createElement('p');
    label.className = 'detail-small';
    label.textContent = 'Дата события';
    const summary = document.createElement('p');
    summary.className = 'detail-summary';
    summary.textContent = event.summary;
    const table = document.createElement('dl');
    table.className = 'detail-table';
    function row(key, content) {
      const wrapper = document.createElement('div');
      wrapper.className = 'detail-row';
      const dt = document.createElement('dt');
      dt.textContent = key;
      const dd = document.createElement('dd');
      if (typeof content === 'string') dd.textContent = content;
      else dd.append(content);
      wrapper.append(dt, dd);
      table.append(wrapper);
    }
    row('Статус', event.status);
    const link = document.createElement('a');
    link.href = event.sourceUrl;
    link.target = '_blank';
    link.rel = 'noopener noreferrer';
    link.textContent = event.source + ' ↗';
    row('Источник', link);
    const precision = document.createElement('p');
    precision.className = 'precision-note';
    precision.textContent = event.precision;
    root.append(kind, title, place, date, label, summary, table, precision);
    if (moveMap && state.mapReady) {
      state.map.flyTo({ center: [event.longitude, event.latitude], zoom: Math.max(state.map.getZoom(), 7), speed: 1.1, essential: true });
    }
    renderCards(filteredEvents());
  }

  function renderCards(events) {
    eventList.replaceChildren();
    $('filter-count').textContent = 'Найдено сообщений: ' + events.length;
    $('list-count').textContent = events.length ? String(events.length) : '';
    $('list-heading').textContent = selectedYear() === 'all' ? 'Все сообщения' : 'Сообщения за ' + selectedYear() + ' год';
    if (!events.length) {
      const empty = document.createElement('div');
      empty.className = 'empty-state';
      empty.textContent = searchInput.value.trim() ? 'По запросу сообщений нет. Попробуйте другое место.' : 'За выбранный год сообщений в архиве пока нет. Архив пополняется.';
      eventList.append(empty);
      return;
    }
    events.slice(0, 80).forEach((event) => {
      const button = document.createElement('button');
      button.type = 'button';
      button.className = 'event-card' + (state.selectedId === event.id ? ' selected' : '');
      button.setAttribute('role', 'listitem');
      button.setAttribute('aria-label', typeLabel(event.type) + ': ' + event.place + ', ' + formatDate(event.eventDate));
      const kind = document.createElement('span');
      kind.className = 'card-kind ' + event.type;
      kind.textContent = (event.type === 'attack' ? '●  ' : '▲  ') + typeLabel(event.type);
      const date = document.createElement('span');
      date.className = 'card-date';
      date.textContent = formatDate(event.eventDate);
      const place = document.createElement('span');
      place.className = 'card-place';
      place.textContent = event.place;
      const region = document.createElement('span');
      region.className = 'card-region';
      region.textContent = event.region;
      button.append(kind, date, place, region);
      button.addEventListener('click', () => showDetail(event, true));
      eventList.append(button);
    });
  }

  function render() {
    const events = filteredEvents();
    if (state.selectedId && !events.some((event) => event.id === state.selectedId)) {
      state.selectedId = null;
      detailPanel.hidden = true;
    }
    renderCards(events);
    updateMap(events);
  }

  function removeBorders(style) {
    // Exclude the boundary geometry itself, country/region labels and jurisdiction fills.
    // Keep settlements, physical features, roads, rivers and coastline.
    style.layers = style.layers.filter((layer) => {
      const id = String(layer.id || '').toLowerCase();
      const sourceLayer = String(layer['source-layer'] || '').toLowerCase();
      if (sourceLayer === 'boundary') return false;
      if (/boundar|admin|country|state|province|disput|territor|maritime/.test(id)) return false;
      if (layer.type === 'symbol' && /place[-_ ]?(country|state)|country[-_ ]?label/.test(id)) return false;
      return true;
    });
    return style;
  }

  async function initializeMap() {
    if (!window.maplibregl) throw new Error('Map rendering is unavailable');
    const response = await fetch('https://tiles.openfreemap.org/styles/dark');
    if (!response.ok) throw new Error('Map style could not be loaded');
    const style = removeBorders(await response.json());
    const map = new maplibregl.Map({
      container: 'map',
      style,
      center: [102, 61],
      zoom: window.innerWidth < 680 ? 1.7 : 2.4,
      minZoom: 1,
      maxZoom: 16,
      renderWorldCopies: false,
      attributionControl: false
    });
    state.map = map;
    map.addControl(new maplibregl.AttributionControl({ compact: true }), 'bottom-right');
    map.on('load', () => {
      state.mapReady = true;
      map.addSource('events', {
        type: 'geojson',
        data: { type: 'FeatureCollection', features: [] },
        cluster: true,
        clusterMaxZoom: 10,
        clusterRadius: 44
      });
      map.addLayer({ id: 'clusters-halo', type: 'circle', source: 'events', filter: ['has', 'point_count'], paint: { 'circle-color': '#f3ab47', 'circle-radius': ['step', ['get', 'point_count'], 18, 10, 23, 50, 29], 'circle-opacity': .17, 'circle-stroke-width': 0 } });
      map.addLayer({ id: 'clusters', type: 'circle', source: 'events', filter: ['has', 'point_count'], paint: { 'circle-color': '#f1ae4a', 'circle-radius': ['step', ['get', 'point_count'], 13, 10, 17, 50, 22], 'circle-stroke-color': '#ffe2a6', 'circle-stroke-width': 2 } });
      map.addLayer({ id: 'cluster-count', type: 'symbol', source: 'events', filter: ['has', 'point_count'], layout: { 'text-field': ['get', 'point_count_abbreviated'], 'text-size': 12 }, paint: { 'text-color': '#19242b' } });
      map.addLayer({ id: 'event-halo', type: 'circle', source: 'events', filter: ['!', ['has', 'point_count']], paint: { 'circle-color': ['match', ['get', 'type'], 'attack', '#ff626d', '#ffbb55'], 'circle-radius': 14, 'circle-opacity': .18 } });
      map.addLayer({ id: 'event-points', type: 'circle', source: 'events', filter: ['!', ['has', 'point_count']], paint: { 'circle-color': ['match', ['get', 'type'], 'attack', '#ff626d', '#ffbb55'], 'circle-radius': 7, 'circle-stroke-color': '#ffffff', 'circle-stroke-width': 2 } });
      map.on('click', 'event-points', (event) => {
        const id = event.features && event.features[0] && event.features[0].properties.id;
        showDetail(state.events.find((item) => item.id === id), false);
      });
      map.on('click', 'clusters', (event) => {
        const feature = event.features && event.features[0];
        if (!feature) return;
        map.getSource('events').getClusterExpansionZoom(feature.properties.cluster_id).then((zoom) => {
          map.easeTo({ center: feature.geometry.coordinates, zoom });
        });
      });
      ['clusters', 'event-points'].forEach((layer) => {
        map.on('mouseenter', layer, () => { map.getCanvas().style.cursor = 'pointer'; });
        map.on('mouseleave', layer, () => { map.getCanvas().style.cursor = ''; });
      });
      updateMap(filteredEvents());
    });
    map.on('error', (event) => {
      if (!state.mapReady) {
        console.error('Map error:', event.error);
        $('map-error').hidden = false;
      }
    });
  }

  ['year', 'filter-sighting', 'filter-attack'].forEach((id) => $(id).addEventListener('change', render));
  searchInput.addEventListener('input', render);
  $('zoom-in').addEventListener('click', () => state.map && state.map.zoomIn());
  $('zoom-out').addEventListener('click', () => state.map && state.map.zoomOut());
  $('close-detail').addEventListener('click', () => { detailPanel.hidden = true; state.selectedId = null; renderCards(filteredEvents()); });
  $('about-trigger').addEventListener('click', () => {
    const shouldOpen = aboutPanel.hidden;
    aboutPanel.hidden = !shouldOpen;
    detailPanel.hidden = true;
    $('about-trigger').setAttribute('aria-expanded', String(shouldOpen));
  });
  $('close-about').addEventListener('click', () => { aboutPanel.hidden = true; $('about-trigger').setAttribute('aria-expanded', 'false'); });
  document.addEventListener('keydown', (event) => {
    if (event.key === 'Escape') {
      detailPanel.hidden = true;
      aboutPanel.hidden = true;
      $('about-trigger').setAttribute('aria-expanded', 'false');
    }
  });

  fetch('./events.json', { cache: 'no-cache' }).then((response) => {
    if (!response.ok) throw new Error('No event data');
    return response.json();
  }).then((data) => {
    state.events = data.events.filter((event) =>
      Number(event.eventDate.slice(0, 4)) >= 1991 &&
      Number.isFinite(event.longitude) && Number.isFinite(event.latitude) &&
      /^https:\/\//.test(event.sourceUrl)
    );
    $('coverage-note').textContent = data.coverageNote;
    $('updated-at').textContent = 'Данные обновлены: ' + formatDate(data.updatedAt.slice(0, 10));
    render();
  }).catch(() => {
    eventList.replaceChildren();
    const empty = document.createElement('div');
    empty.className = 'empty-state';
    empty.textContent = 'Сообщения временно не загрузились. Обновите страницу позже.';
    eventList.append(empty);
    $('filter-count').textContent = 'Данные недоступны';
  });

  initializeMap().catch((error) => {
    console.error('Map initialization failed:', error);
    $('map-error').hidden = false;
  });
})();
