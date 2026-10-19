const $ = id => document.getElementById(id);
let data = null, requestId = 0;
function node(tag, text, cls) {
  const el = document.createElement(tag);
  if (text !== undefined) el.textContent = text;
  if (cls) el.className = cls;
  return el;
}
function render() {
  $('grid').replaceChildren();
  if (!data) { $('count').textContent = ''; return; }
  const query = $('search').value.toLocaleLowerCase();
  const items = data.items.filter(x => x.name.toLocaleLowerCase().includes(query));
  items.sort((a,b) => $('sort').value === 'name' ? a.name.localeCompare(b.name) : ($('sort').value === 'asc' ? a.chance-b.chance : b.chance-a.chance));
  $('count').textContent = `${items.length} из ${data.items.length} предметов`;
  for (const item of items) {
    const card = node('article', undefined, 'card');
    const picture = node('div', undefined, 'picture');
    const fallback = () => picture.replaceChildren(node('span', '◇', 'placeholder'));
    if (item.image) {
      const img = node('img'); img.alt = item.name; img.loading = 'lazy';
      img.referrerPolicy = 'no-referrer'; img.onerror = fallback; img.src = item.image;
      picture.append(img);
    } else fallback();
    const content = node('div', undefined, 'content');
    content.append(node('h3', item.name), node('div', `Количество: ${item.amount}`, 'quantity'));
    const chance = node('div', undefined, 'chance');
    chance.append(node('span', 'ШАНС ВЫПАДЕНИЯ'), node('strong', item.chance_text));
    const track = node('div', undefined, 'track'), fill = node('div');
    fill.style.width = `${item.chance}%`; track.append(fill);
    content.append(chance, track); card.append(picture, content); $('grid').append(card);
  }
  if (!items.length) $('grid').append(node('p', 'Предметы не найдены. Попробуй другое название.'));
}
function show(result) {
  data = result;
  $('status').className = result.warning ? 'error' : '';
  $('status').textContent = result.warning || (result.origin === 'import' ? 'Показана импортированная таблица.' : result.cached ? 'Показана сохранённая таблица. Нажми «Обновить», чтобы проверить изменения.' : 'Таблица загружена с сайта.');
  const link = node('a', 'RustClash Wiki'); link.href = result.source; link.target = '_blank'; link.rel = 'noopener noreferrer';
  $('source').replaceChildren(node('span', 'Источник: '), link, node('span', ` · Загружено: ${new Date(result.updated).toLocaleString('ru-RU')}`));
  render();
}
async function load(refresh = false) {
  const id = ++requestId; data = null; render(); $('source').replaceChildren();
  $('title').textContent = $('crate').selectedOptions[0].textContent;
  $('status').className = ''; $('status').textContent = 'Загружаем таблицу лута…'; $('refresh').disabled = true;
  try {
    const response = await fetch(`/api/loot?crate=${encodeURIComponent($('crate').value)}&refresh=${refresh ? 1 : 0}`);
    const result = await response.json(); if (id !== requestId) return;
    if (!response.ok) throw new Error(result.error);
    show(result);
  } catch (err) { if (id === requestId) { $('status').className = 'error'; $('status').textContent = err.message; } }
  finally { if (id === requestId) $('refresh').disabled = false; }
}
$('search').oninput = render; $('sort').onchange = render; $('crate').onchange = () => load();
$('refresh').onclick = () => load(true);
$('import').onchange = async event => {
  const file = event.target.files[0]; if (!file) return;
  const id = ++requestId, crate = $('crate').value;
  try {
    if (file.size > 5 * 1024 * 1024) throw new Error('Файл должен быть меньше 5 МБ');
    const response = await fetch(`/api/import?crate=${encodeURIComponent(crate)}`, {method:'POST',headers:{'Content-Type':'text/html'},body:await file.text()});
    const result = await response.json(); if (id !== requestId) return;
    if (!response.ok) throw new Error(result.error); show(result);
  } catch (err) { if (id === requestId) { $('status').textContent = err.message; $('status').className = 'error'; } }
  finally { if (id === requestId) $('refresh').disabled = false; event.target.value = ''; }
};
fetch('/api/crates').then(r => { if (!r.ok) throw new Error('Не удалось получить список ящиков'); return r.json(); }).then(crates => {
  for (const [value, title] of Object.entries(crates)) { const option = node('option', title); option.value = value; $('crate').append(option); }
  load();
}).catch(err => { $('status').textContent = err.message; $('status').className = 'error'; });
