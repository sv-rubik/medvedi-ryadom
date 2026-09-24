(async function () {
  const chart = document.getElementById('population-chart');
  const label = document.getElementById('population-label');
  const dataBase = location.hostname.endsWith('chatgpt.site') ? 'https://sv-rubik.github.io/medvedi-ryadom/' : './';
  try {
    const response = await fetch(dataBase + 'population.json', { cache: 'no-cache' });
    if (!response.ok) throw new Error('Population data unavailable');
    const data = await response.json();
    const points = data.points;
    const values = points.map((point) => point.value);
    const low = Math.min(...values) - 2;
    const high = Math.max(...values) + 2;
    const x = (index) => 5 + index * 190 / (points.length - 1);
    const y = (value) => 31 - (value - low) * 26 / (high - low);
    const path = document.createElementNS('http://www.w3.org/2000/svg', 'path');
    path.setAttribute('d', points.map((point, index) => `${index ? 'L' : 'M'}${x(index).toFixed(1)} ${y(point.value).toFixed(1)}`).join(' '));
    path.setAttribute('fill', 'none');
    path.setAttribute('stroke', '#5ed4ab');
    path.setAttribute('stroke-width', '2');
    path.setAttribute('stroke-linecap', 'round');
    path.setAttribute('stroke-linejoin', 'round');
    chart.append(path);
    for (const [index, point] of points.entries()) {
      const circle = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
      circle.setAttribute('cx', x(index));
      circle.setAttribute('cy', y(point.value));
      circle.setAttribute('r', '2.4');
      circle.setAttribute('fill', '#d6fff0');
      const title = document.createElementNS('http://www.w3.org/2000/svg', 'title');
      title.textContent = `${point.year}: ${point.value.toLocaleString('ru-RU')} тыс. особей`;
      circle.append(title);
      chart.append(circle);
    }
    label.textContent = `${points[0].year}: ${points[0].value.toLocaleString('ru-RU')} → ${points.at(-1).year}: ${points.at(-1).value.toLocaleString('ru-RU')} тыс.`;
    chart.setAttribute('aria-label', `${data.title}. ${label.textContent}. ${data.note}`);
    label.append(' · ');
    data.sources.forEach((entry, index) => {
      const source = document.createElement('a');
      source.href = entry.url;
      source.target = '_blank';
      source.rel = 'noopener noreferrer';
      source.textContent = index ? '2024 ↗' : 'Росстат ↗';
      if (index) label.append(', ');
      label.append(source);
    });
  } catch {
    label.textContent = 'Данные о численности временно недоступны';
  }
})();
