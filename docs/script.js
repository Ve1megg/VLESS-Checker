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

const COUNTRY_FLAGS = {
  'turkey': '🇹🇷', 'Турция': '🇹🇷',
  'uk': '🇬🇧', 'Великобритания': '🇬🇧', 'Англия': '🇬🇧',
  'usa': '🇺🇸', 'США': '🇺🇸',
  'france': '🇫🇷', 'Франция': '🇫🇷',
  'japan': '🇯🇵', 'Япония': '🇯🇵',
  'kazakhstan': '🇰🇿', 'Казахстан': '🇰🇿',
  'italy': '🇮🇹', 'Италия': '🇮🇹',
  'spain': '🇪🇸', 'Испания': '🇪🇸',
  'georgia': '🇬🇪', 'Грузия': '🇬🇪',
  'armenia': '🇦🇲', 'Армения': '🇦🇲'
};

function getCountryFlag(key) {
  if (!key) return '🌍';
  return COUNTRY_FLAGS[key] || COUNTRY_FLAGS[key.toLowerCase()] || '🌍';
}

let activeSection = null;

const connectionState = {
  vpn: { country: null, connectionType: null },
  white: { country: null, connectionType: null }
};

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

function getCountryKeyFromBtn(btn) {
  if (btn.dataset && btn.dataset.key) return btn.dataset.key;
  const onclickAttr = btn.getAttribute('onclick') || '';
  const match = onclickAttr.match(/['"]([^'"]+)['"]/);
  return match ? match[1] : null;
}

function countryHasKeys(countryKey) {
  if (!data) return true;
  const targetObj = data[countryKey] || data[countryKey + '_countries'] || (countryKey === 'other' ? data.other_countries : null);
  if (!targetObj) return false;

  if (countryKey === 'other' || countryKey === 'w_other') {
    return Object.values(targetObj).some(cData => {
      if (!cData) return false;
      const homeWorking = cData.home ? (cData.home.total_working > 0) : false;
      const mobileWorking = cData.mobile ? (cData.mobile.total_working > 0) : false;
      const directWorking = cData.total_working > 0;
      return homeWorking || mobileWorking || directWorking;
    });
  }

  const cData = targetObj;
  const homeWorking = cData.home ? (cData.home.total_working > 0) : false;
  const mobileWorking = cData.mobile ? (cData.mobile.total_working > 0) : false;
  const directWorking = cData.total_working > 0;

  return homeWorking || mobileWorking || directWorking;
}

function selectCountry(countryKey) {
  const modeObj = MODES.find(m => m.key === countryKey);
  if (!modeObj) return;

  activeSection = modeObj.section;
  clearOtherSection(activeSection);

  connectionState[activeSection].country = countryKey;

  const availableTypes = [];
  if (data) {
    if (countryKey === 'other' || countryKey === 'w_other') {
      const otherObj = data[countryKey] || data[countryKey + '_countries'] || data.other_countries || {};
      ['home', 'mobile'].forEach(t => {
        const hasType = Object.values(otherObj).some(sub => (sub[t] && sub[t].total_working > 0) || (sub.total_working > 0));
        if (hasType) availableTypes.push(t);
      });
    } else {
      const cData = data[countryKey];
      if (cData) {
        ['home', 'mobile'].forEach(t => {
          if (cData[t] && cData[t].total_working > 0) availableTypes.push(t);
        });
      }
    }
  }

  if (availableTypes.length === 1) {
    connectionState[activeSection].connectionType = availableTypes[0];
  } else {
    const currentType = connectionState[activeSection].connectionType;
    if (currentType && !availableTypes.includes(currentType)) {
      connectionState[activeSection].connectionType = null;
    }
  }

  updateCountryTabsUI();
  updateConnectionTabsUI();
  renderActiveCard();
}

function selectConnectionType(sectionOrType, type, event) {
  let section = sectionOrType;
  let connType = type;

  if (!connType) {
    connType = sectionOrType;
    const target = event ? (event.currentTarget || event.target) : null;

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

  if (!connectionState[section].country) return;

  activeSection = section;
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

  const countrySections = [
    { containerId: 'tabs-countries', collapsedId: 'tabs-collapsed', toggleId: 'collapsed-toggle', labelId: 'collapsed-label' },
    { containerId: 'tabs-white', collapsedId: 'tabs-collapsed-white', toggleId: 'collapsed-toggle-white', labelId: 'collapsed-label-white' }
  ];

  countrySections.forEach(({ containerId, collapsedId, toggleId, labelId }) => {
    const container = document.getElementById(containerId);
    if (!container) return;

    const emptyCountries = [];
    const buttons = container.querySelectorAll('.tab');

    buttons.forEach(btn => {
      const countryKey = getCountryKeyFromBtn(btn);
      const isCurrent = activeCountry && countryKey === activeCountry;

      btn.classList.toggle('active', !!isCurrent);

      const hasKeys = countryKey ? countryHasKeys(countryKey) : true;

      if (hasKeys) {
        btn.style.display = '';
        btn.disabled = false;
        btn.classList.remove('disabled');
      } else {
        btn.style.display = 'none';

        const clone = btn.cloneNode(true);
        clone.disabled = true;
        clone.classList.add('disabled');
        clone.style.display = '';
        emptyCountries.push(clone);
      }
    });

    setupCollapsed(collapsedId, toggleId, labelId, emptyCountries);
  });
}

function updateConnectionTabsUI() {
  ['vpn', 'white'].forEach(section => {
    const containerId = section === 'vpn' ? 'tabs-conection-bl' : 'tabs-conection-wl';
    const container = document.getElementById(containerId);
    if (!container) return;

    const currentCountry = connectionState[section].country;
    const selectedType = connectionState[section].connectionType;

    ['home', 'mobile'].forEach(type => {
      const btn = container.querySelector(`[data-type="${type}"], [onclick*="${type}"]`);
      if (!btn) return;

      if (!currentCountry) {
        btn.disabled = true;
        btn.classList.add('disabled');
        btn.classList.remove('active');
        return;
      }

      let hasKeys = false;
      if (data) {
        if (currentCountry === 'other' || currentCountry === 'w_other') {
          const otherObj = data[currentCountry] || data[currentCountry + '_countries'] || data.other_countries || {};
          hasKeys = Object.values(otherObj).some(sub => (sub[type] && sub[type].total_working > 0) || (sub.total_working > 0));
        } else if (data[currentCountry] && data[currentCountry][type]) {
          hasKeys = data[currentCountry][type].total_working > 0;
        }
      }

      if (hasKeys) {
        btn.disabled = false;
        btn.classList.remove('disabled');
        const isSelected = (type === selectedType);
        btn.classList.toggle('active', isSelected);
      } else {
        btn.disabled = true;
        btn.classList.add('disabled');
        btn.classList.remove('active');
      }
    });
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
    if (updatedEl) updatedEl.textContent = 'Последнее добавление ключей: ' + displayTime;

    const deletedUtcStr = data.last_deleted_at || data.last_deleated_at;
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

  updateCountryTabsUI();
  updateConnectionTabsUI();
  renderActiveCard();
}

function renderCountryBlock(countryName, flag, d) {
  const topList = d.top10 || d.top5 || [];
  const displayFlag = flag || d.flag || getCountryFlag(countryName);
  const totalWorking = d.total_working || 0;
  const total = d.total || 0;

  let html = '<div class="country-block" style="margin-bottom:20px; padding:12px; background:rgba(255,255,255,0.03); border-radius:8px;">';
  html += '<h3 class="country-title" style="margin-bottom:10px; font-size:1.1em;">' + displayFlag + ' ' + countryName +
          '<span class="country-stats" style="font-size:0.85em; opacity:0.7;"> · ' + totalWorking + ' из ' + total + '</span></h3>';

  if (topList.length > 0) {
    html += topList.map((k, i) => {
      const provider = k.isp || k.host;
      return '<div class="top5-item">' +
        '<span class="host">' + (i + 1) + '. ' + provider + ':' + k.port + '</span>' +
        '<span class="latency">' + k.latency_ms + ' мс</span>' +
        (k.first_seen ? '<span class="uptime">добавлен ' + formatAddedTime(k.first_seen) + '</span>' : '') +
        '<button class="copy-small" onclick="copyText(\'' + encodeKey(k.key) + '\', this)">копировать</button>' +
        '</div>';
    }).join('');
  } else {
    html += '<div class="top5-item"><span class="host">Нет рабочих ключей</span></div>';
  }
  html += '</div>';
  return html;
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
  const categoryTitle = modeObj ? modeObj.label : selectedCountry;
  const connLabel = selectedConnectionType === 'home' ? 'Домашний Интернет' : 'Мобильный Интернет';

  if (selectedCountry === 'other' || selectedCountry === 'w_other') {
    const otherContainer = data ? (
      data[selectedCountry]
      || data[selectedCountry + '_countries']
      || (selectedCountry === 'other' ? data.other_countries : data.w_other_countries)
    ) : null;

    let html = `<div class="card">`;
    html += `<h2>${categoryTitle} — ${connLabel}</h2>`;

    if (!otherContainer) {
      html += `<div class="key-box empty">Рабочих ключей не найдено.</div></div>`;
      container.innerHTML = html;
      return;
    }

    const countryBlocks = [];

    Object.entries(otherContainer).forEach(([cKey, cVal]) => {
      if (!cVal) return;

      const targetData = (cVal[selectedConnectionType]) ? cVal[selectedConnectionType] : cVal;

      const workingCount = targetData.total_working || 0;
      const topList = targetData.top10 || targetData.top5 || [];

      if (workingCount > 0 || topList.length > 0) {
        const countryName = cVal.name || targetData.name || cKey;
        const countryFlag = cVal.flag || targetData.flag || getCountryFlag(cKey);

        countryBlocks.push({
          name: countryName,
          flag: countryFlag,
          data: targetData,
          working: workingCount
        });
      }
    });

    countryBlocks.sort((a, b) => b.working - a.working);

    if (countryBlocks.length > 0) {
      html += `<div class="top5" style="margin-top:15px;">`;
      html += countryBlocks.map(item => renderCountryBlock(item.name, item.flag, item.data)).join('');
      html += `</div>`;
    } else {
      html += `<div class="key-box empty">Рабочих ключей для выбранного типа подключения не найдено.</div>`;
    }

    html += `</div>`;
    container.innerHTML = html;
    return;
  }

  if (!data || !data[selectedCountry]) {
    container.innerHTML = `<div class="card"><h2>${categoryTitle} — ${connLabel}</h2><div class="key-box empty">Загрузка данных или ключи не найдены...</div></div>`;
    return;
  }

  const cData = data[selectedCountry];
  const targetData = (cData && cData[selectedConnectionType]) ? cData[selectedConnectionType] : cData;

  let html = `<div class="card">`;
  html += `<h2>${categoryTitle} — ${connLabel}</h2>`;

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
    html += topList.map((k, i) => {
      const provider = k.isp || k.host;
      return `<div class="top5-item">` +
        `<span class="host">${i + 1}. ${provider}:${k.port}</span>` +
        `<span class="latency">${k.latency_ms} мс</span>` +
        (k.first_seen ? `<span class="uptime">добавлен ${formatAddedTime(k.first_seen)}</span>` : '') +
        `<button class="copy-small" onclick="copyText('${encodeKey(k.key)}', this)">копировать</button>` +
        `</div>`;
    }).join('');
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

function formatAddedTime(firstSeen) {
  if (!firstSeen) return '';
  try {
    const d = new Date(firstSeen)
    if (isNaN(d)) return firstSeen;
//Перевод в московское время (UTC+3)
      const msk = new Date(d.getTime() + 3 * 60 * 60 * 1000);
      const day = String(msk.getUTCMonth() + 1).padStart(2, '0');
      const hours = String(msk.getUTCHours()).padStart(2, '0');
      const minutes = String(msk.getUTCMinutes()).padStart(2, '0');

      return `${day}.${month} в ${hours}:${minutes}`;
    } catch (e) {
      return '';
  }
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