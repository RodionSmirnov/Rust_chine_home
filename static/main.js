const $ = id => document.getElementById(id);
let data = null, requestId = 0;
function node(tag, text, cls) {
  const el = document.createElement(tag);
  if (text !== undefined) el.textContent = text;
  if (cls) el.className = cls;
  return el;
}
function render() {
  const fragment = document.createDocumentFragment();
  if (!data) { $('grid').replaceChildren(); $('count').textContent = ''; return; }
  const query = $('search').value.toLocaleLowerCase().trim();
  const items = data.items.filter(x => `${x.name} ${x.english_name} ${x.id}`.toLocaleLowerCase().includes(query) && (!$('category').value || x.category === $('category').value));
  items.sort((a,b) => $('sort').value === 'name' || data.crate === 'all' ? a.name.localeCompare(b.name, 'ru') : ($('sort').value === 'asc' ? a.chance-b.chance : b.chance-a.chance));
  $('count').textContent = `${items.length} из ${data.items.length} предметов`;
  for (const item of items) {
    const row = node('tr'), cell = node('td'), wrap = node('div', undefined, 'item');
    const picture = node('div', undefined, 'picture');
    const fallback = () => { picture.replaceChildren(node('span', '◇', 'placeholder')); picture.title = 'В источнике нет доступного изображения'; };
    if (item.image) {
      const img = node('img'); img.alt = item.name; img.loading = 'lazy';
      img.onerror = fallback; img.src = item.image; picture.append(img);
    } else fallback();
    const content = node('div');
    content.append(node('div', item.name, 'name'));
    content.append(node('div', `${item.id}${item.hidden ? ' · служебный / скрытый' : ''}`, 'shortname'));
    if (item.amount !== '—') content.append(node('div', `× ${item.amount}`, 'quantity'));
    wrap.append(picture, content); cell.append(wrap);
    const chance = node('td'); chance.append(node('span', item.chance_text, 'chance'));
    if (item.chance !== null) {
      const track = node('div', undefined, 'track'), fill = node('div');
      fill.style.width = `${item.chance}%`; track.append(fill); chance.append(track);
    }
    row.append(cell, node('td', item.condition), node('td', item.category), chance); fragment.append(row);
  }
  if (!items.length) { const row = node('tr'), cell = node('td', 'Предметы не найдены. Измени поиск или категорию.', 'empty'); cell.colSpan = 4; row.append(cell); fragment.append(row); }
  $('grid').replaceChildren(fragment);
}
function date(value) { return new Date(value).toLocaleDateString('ru-RU'); }
function show(result) {
  data = result;
  const previous = $('category').value;
  const options = [node('option', 'Все категории')]; options[0].value = '';
  for (const category of [...new Set(data.items.map(x => x.category))].sort()) { const option = node('option', category); option.value = category; options.push(option); }
  $('category').replaceChildren(...options);
  if (options.some(x => x.value === previous)) $('category').value = previous;
  $('status').className = '';
  $('status').textContent = data.crate === 'all' ? 'Полный каталог базы, включая служебные предметы. Для шансов выбери конкретный контейнер.' : 'Все предметы из таблицы выбранного контейнера. Данные и изображения загружены локально.';
  $('version').textContent = `${result.total_items} предметов · ${result.total_containers} контейнер · Сборка ${result.meta.build} · Проверка источником: ${date(result.meta.checked)}`;
  const link = node('a', 'rust-items-json'); link.href = `${result.source}/tree/${result.commit}`; link.target = '_blank'; link.rel = 'noopener noreferrer';
  $('source').replaceChildren(node('span', 'Источник: '), link, node('span', ` · Данные обновлены: ${date(result.meta.updated)} · Сборка ${result.meta.build}`));
  render();
}
async function load() {
  const id = ++requestId; data = null; render(); $('source').replaceChildren();
  $('title').textContent = $('crate').selectedOptions[0].textContent;
  $('status').className = ''; $('status').textContent = 'Загружаем встроенную базу…';
  try {
    const response = await fetch(`/api/loot?crate=${encodeURIComponent($('crate').value)}`);
    const result = await response.json(); if (id !== requestId) return;
    if (!response.ok) throw new Error(result.error); show(result);
  } catch (err) { if (id === requestId) { $('status').className = 'error'; $('status').textContent = err.message; } }
}
$('search').oninput = render; $('sort').onchange = render; $('category').onchange = render; $('crate').onchange = load;
fetch('/api/crates').then(r => { if (!r.ok) throw new Error('Не удалось получить список контейнеров'); return r.json(); }).then(crates => {
  // Numeric container IDs must not affect the intended catalogue-first order.
  for (const value of ['all', ...Object.keys(crates).filter(x => x !== 'all')]) { const option = node('option', crates[value]); option.value = value; $('crate').append(option); }
  $('crate').value = '0'; load();
}).catch(err => { $('status').textContent = err.message; $('status').className = 'error'; });
