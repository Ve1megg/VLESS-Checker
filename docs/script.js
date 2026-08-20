document.addEventListener("DOMContentLoaded", () => {
  const modal = document.getElementById("disclaimerModel");
  const acceptBtn = document.getElementById("acceptBtn");

  if (localStorage.getItem("vless_disclaimer_accepted") === "true") {
    if (modal) modal.classList.add("hidden");
  }

  if (acceptBtn) {
    acceptBtn.addEventListener("click", () => {
      localStorage.setItem("vless_disclaimer_accepted", "true");
      if (modal) modal.classList.add("hidden");
    });
  }
});

const KEYS_URL = 'keys.json';
let data = null;

const MODES = [
  { key: 'baltics', label: '🇱🇹🇪🇪🇱🇻 Прибалтика', section: 'vpn' },
  { key: 'finland', label: '🇫🇮 Финляндия', section: 'vpn' },
  { key: 'germany', label: '🇩🇪 Германия', section: 'vpn' },
  { key: 'sweden', label: '🇸🇪 Швеция', section: 'vpn' },
  { key: 'netherlands', label: '🇳🇱 Нидерланды', section: 'vpn' },
  { key: 'poland', label: '🇵🇱 Польша', section: 'vpn' },
  { key: 'other', label: '🌍 Остальные', section: 'vpn' },
  { key: 'w_baltics', label: '🇱🇹🇪🇪🇱🇻 Прибалтика', section: 'white' },
  { key: 'w_finland', label: '🇫🇮 Финляндия', section: 'white' },
  { key: 'w_germany', label: '🇩🇪 Германия', section: 'white' },
  { key: 'w_sweden', label: '🇸🇪 Швеция', section: 'white' },
  { key: 'w_netherlands', label: '🇳🇱 Нидерланды', section: 'white' },
  { key: 'w_poland', label: '🇵🇱 Польша', section: 'white' },
  { key: 'w_other', label: '🌍 Остальные', section: 'white' },
  { key: 'russia', label: '🇷🇺 Россия (Москва)', section: 'white' },
];

let activeSection = null; // 'vpn' | 'white' | null

const connectionState = {
  vpn: { country: null, connectionType: null },
  white: { country: null, connectionType: null }
};

// Функция для очистки неактивной секции
function clearOtherSection(currentSection) {
  const otherSection = currentSection === 'vpn' ? 'white' : 'vpn';
  connectionState[otherSection].country = null;
  connectionState[otherSection].connectionType = null;
}

function switchMode(mode) {
  if (mode === 'home_internet' || mode === 'home') {
    selectConnectionType('home');
  } else if (mode === 'mobile_internet' || mode === 'mobile') {
    selectConnectionType('mobile');
  } else {
    selectCountry(mode);
  }
}

function selectCountry(countryKey) {
  const modeObj = MODES.find(m => m.key === countryKey);
  if (!modeObj) return;

  activeSection = modeObj.section;

  // Сбрасываем выбор в другом блоке
  clearOtherSection(activeSection);

  connectionState[activeSection].country = countryKey;

  updateCountryTabsUI();
  updateConnectionTabsUI();
  renderActiveCard();
}

function selectConnectionType(sectionOrType, type) {
  let section = sectionOrType;
  let connType = type;

  if (!connType) {
    connType = sectionOrType;

    const evt = window.event;
    const target = evt ? (evt.currentTarget || evt.target) : null;

    if (target && target.closest('#tabs-conection-wl')) {
      section = 'white';
    } else if (target && target.closest('#tabs-conection-bl')) {
      section = 'vpn';
    } else {
      section = activeSection || 'vpn';
    }
  }

  if (section === 'bl') section = 'vpn';
  if (section === 'wl') section = 'white';

  activeSection = section;

  // Сбрасываем выбор в другом блоке
  clearOtherSection(activeSection);

  if (connectionState[section]) {
    connectionState[section].connectionType = connType;
  }

  updateCountryTabsUI();
  updateConnectionTabsUI();
  renderActiveCard();
}

function updateCountryTabsUI() {
  const activeCountry = activeSection ? connectionState[activeSection].country : null;
  document.querySelectorAll('#tabs-countries .tab, #tabs-white .tab').forEach(btn => {
    const onclickAttr = btn.getAttribute('onclick') || '';
    const isCurrent = activeCountry && onclickAttr.includes(`'${activeCountry}'`);
    btn.classList.toggle('active', !!isCurrent);
  });
}

function updateConnectionTabsUI() {
  ['vpn', 'white'].forEach(section => {
    const containerId = section === 'vpn' ? 'tabs-conection-bl' : 'tabs-conection-wl';
    const collapsedId = section === 'vpn' ? 'tabs-collapsed-conection-bl' : 'tabs-collapsed-conection-wl';
    const toggleId = section === 'vpn' ? 'collapsed-toggle-conection-bl' : 'collapsed-toggle-conection-wl';
    const labelId = section === 'vpn' ? 'collapsed-label-conection-bl' : 'collapsed-label-conection-wl';

    const emptyConnections = [];
    const currentCountry = connectionState[section].country;
    const selectedType = connectionState[section].connectionType;

    ['home', 'mobile'].forEach(type => {
      const container = document.getElementById(containerId);
      if (!container) return;

      const btn = container.querySelector(`[data-type="${type}"], [onclick*="${type}"]`);
      if (!btn) return;

      let hasKeys = true;
      if (currentCountry && data && data[currentCountry] && data[currentCountry][type]) {
        hasKeys = data[currentCountry][type].total_working > 0;
      }

      if (hasKeys) {
        btn.style.display = '';
        btn.disabled = false;
        const isSelected = (type === selectedType);
        btn.classList.toggle('active', isSelected);
      } else {
        const clone = btn.cloneNode(true);
        clone.disabled = true;
        emptyConnections.push(clone);
        btn.style.display = 'none';
      }
    });

    setupCollapsed(collapsedId, toggleId, labelId, emptyConnections);
  });
}

async function loadData() {
  const updatedEl = document.getElementById('updated');
  if (updatedEl) {
    updatedEl.innerHTML = '<span class="spinner"></span>Загружаем...';
  }
  try {
    const resp = await fetch(KEYS_URL + '?t=' + Date.now());
    if (!resp.ok) throw new Error('Ошибка загрузки');
    data = await resp.json();
    renderAll();
  } catch (e) {
    if (updatedEl) updatedEl.textContent = 'Ошибка загрузки данных';
    renderAll();
  }
}

function renderAll() {
  if (data) {
    const utcStr = data.updated_at;
    let displayTime = utcStr || '—';
    if (utcStr) {
      try {
        const d = new Date(utcStr.replace(' ', 'T').replace(' UTC', 'Z'));
        if (!isNaN(d)) {
          const msk = new Date(d.getTime() + 3 * 60 * 60 * 1000);
          displayTime = msk.toISOString().slice(0, 16).replace('T', ' ') + ' МСК';
        }
      } catch (e) {}
  }
  const updatedEl = document.getElementById('updated');
  if (updatedEl) updatedEl.textContent = 'Последнее добавления ключей: ' + displayTime;

  const deletedUtcStr = data.last_deleted_at;
  const deletedEl = document.getElementById('last-deleted');
  if (deletedEl) {
    if (deletedUtcStr) {
      let displayDeleted = deletedUtcStr;
      try {
        const d = new Date(deletedUtcStr.replace(' ', 'T').replace(' UTC', 'Z'));
        if (!isNaN(d)) {
          const msk = new Date(d.getTime() + 3 * 60 * 60 * 1000);
          displayDeleted = msk.toISOString().slice(0, 16).replace('T', ' ') + ' МСК';
        }
      } catch (e) {}
    deletedEl.textContent = 'Последнее удаление и обновление данных ключей: ' + displayDeleted;
    } else {
      deletedEl.textContent = '';
    }
  }
}

  setupCollapsed('tabs-collapsed', 'collapsed-toggle', 'collapsed-label', emptyVpn);
  setupCollapsed('tabs-collapsed-white', 'collapsed-toggle-white', 'collapsed-label-white', emptyWhite);

  updateCountryTabsUI();
  updateConnectionTabsUI();
  renderActiveCard();
}

function renderActiveCard() {
  const container = document.getElementById('cards');
  if (!container) return;

  if (!activeSection) {
    container.innerHTML = `<div class="card"><h2>Выберите параметры</h2><div class="key-box empty">Выберите страну и тип подключения выше, чтобы получить ключ.</div></div>`;
    return;
  }

  const activeState = connectionState[activeSection];
  const selectedCountry = activeState.country;
  const selectedConnectionType = activeState.connectionType;

  if (!selectedCountry || !selectedConnectionType) {
    container.innerHTML = `<div class="card"><h2>Выберите параметры</h2><div class="key-box empty">Для получения ключа выберите и страну, и тип подключения.</div></div>`;
    return;
  }

  const modeObj = MODES.find(m => m.key === selectedCountry);
  const countryTitle = modeObj ? modeObj.label : selectedCountry;
  const connLabel = selectedConnectionType === 'home' ? 'Домашний Интернет' : 'Мобильный Интернет';

  if (!data || !data[selectedCountry]) {
    container.innerHTML = `<div class="card"><h2>${countryTitle} — ${connLabel}</h2><div class="key-box empty">Загрузка данных или ключи не найдены...</div></div>`;
    return;
  }

  const cData = data[selectedCountry];
  const targetData = (cData && cData[selectedConnectionType]) ? cData[selectedConnectionType] : cData;

  let html = `<div class="card">`;
  html += `<h2>${countryTitle} — ${connLabel}</h2>`;

  if (targetData && targetData.best) {
    html += `<div class="key-box">${targetData.best}</div>`;
    html += `<button class="copy-btn" onclick="copyText('${encodeKey(targetData.best)}', this)">Копировать ключ</button>`;
  } else {
    html += `<div class="key-box empty">Рабочих ключей не найдено. Проверьте позже.</div>`;
    html += `<button class="copy-btn" disabled>Копировать</button>`;
  }

  const totalWorking = targetData ? (targetData.total_working || 0) : 0;
  const total = targetData ? (targetData.total || 0) : 0;
  html += `<div class="stats">Рабочих: ${totalWorking} из ${total}</div>`;

  const topList = targetData ? (targetData.top10 || targetData.top5 || []) : [];
  if (topList.length > 0) {
    html += `<div class="top5"><h3>ТОП быстрых:</h3>`;
    html += topList.map((k, i) =>
      `<div class="top5-item">` +
      `<span class="host">${i + 1}. ${k.host}:${k.port}</span>` +
      `<span class="latency">${k.latency_ms} мс</span>` +
      (k.first_seen ? `<span class="uptime">в сети ${formatUptime(k.first_seen)}</span>` : '') +
      `<button class="copy-small" onclick="copyText('${encodeKey(k.key)}', this)">копировать</button>` +
      `</div>`
    ).join('');
    html += `</div>`;
  }

  html += `</div>`;
  container.innerHTML = html;
}

function setupCollapsed(collapsedId, toggleId, labelId, emptyTabs) {
  const collapsed = document.getElementById(collapsedId);
  const toggle = document.getElementById(toggleId);
  const label = document.getElementById(labelId);
  if (!collapsed || !toggle || !label) return;

  collapsed.innerHTML = '';
  if (emptyTabs.length > 0) {
    emptyTabs.forEach(btn => { collapsed.appendChild(btn); });
    label.textContent = 'Нет ключей: ' + emptyTabs.length;
    toggle.style.display = 'flex';
  } else {
    toggle.style.display = 'none';
  }
}

function toggleCollapsed() {
  const toggle = document.getElementById('collapsed-toggle');
  const collapsed = document.getElementById('tabs-collapsed');
  if (toggle) toggle.classList.toggle('open');
  if (collapsed) collapsed.classList.toggle('open');
}

function toggleCollapsedWhite() {
  const toggle = document.getElementById('collapsed-toggle-white');
  const collapsed = document.getElementById('tabs-collapsed-white');
  if (toggle) toggle.classList.toggle('open');
  if (collapsed) collapsed.classList.toggle('open');
}

function toggleCollapsedConectionBL() {
  const toggle = document.getElementById('collapsed-toggle-conection-bl');
  const collapsed = document.getElementById('tabs-collapsed-conection-bl');
  if (toggle) toggle.classList.toggle('open');
  if (collapsed) collapsed.classList.toggle('open');
}

function toggleCollapsedConectionWL() {
  const toggle = document.getElementById('collapsed-toggle-conection-wl');
  const collapsed = document.getElementById('tabs-collapsed-conection-wl');
  if (toggle) toggle.classList.toggle('open');
  if (collapsed) collapsed.classList.toggle('open');
}

function formatUptime(firstSeen) {
  const diff = Math.floor((Date.now() - new Date(firstSeen)) / 1000);
  if (diff < 3600) return Math.floor(diff / 60) + ' мин';
  if (diff < 86400) return Math.floor(diff / 3600) + ' ч';
  return Math.floor(diff / 86400) + ' д';
}

function encodeKey(key) {
  return key ? key.replace(/\\/g, '\\\\').replace(/'/g, "\\'") : '';
}

function copyText(text, btn) {
  navigator.clipboard.writeText(text).then(() => {
    const orig = btn.textContent;
    btn.textContent = 'Скопировано!';
    setTimeout(() => btn.textContent = orig, 1500);
  });
}

loadData();