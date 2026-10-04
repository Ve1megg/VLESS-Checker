import re
import atexit
import requests
import socket
import time
import json
import os
from collections import defaultdict
from datetime import datetime, timezone
from concurrent.futures import ThreadPoolExecutor, as_completed

BLACK_URL = "https://raw.githubusercontent.com/igareck/vpn-configs-for-russia/refs/heads/main/BLACK_VLESS_RUS.txt"
BLACK_MOBILE_URL = "https://raw.githubusercontent.com/igareck/vpn-configs-for-russia/refs/heads/main/BLACK_VLESS_RUS_mobile.txt"
WHITE_URL = "https://raw.githubusercontent.com/igareck/vpn-configs-for-russia/refs/heads/main/WHITE-CIDR-RU-checked.txt"
WHITE_URL_MOBILE = "https://raw.githubusercontent.com/igareck/vpn-configs-for-russia/refs/heads/main/Vless-Reality-White-Lists-Rus-Mobile.txt"

MAX_WORKERS = 20
TEST_TIMEOUT = 5
MAX_LATENCY_MS = 2000

CACHE_FILE = "docs/cache_map.json"
KEYS_FILE = "docs/keys.json"

COUNTRIES = {
    "baltics": ["lithuania", "estonia", "latvia"],
    "finland": ["finland"],
    "germany": ["germany"],
    "sweden": ["sweden"],
    "netherlands": ["netherlands"],
    "poland": ["poland"],
}

COUNTRIES_ALL_KEYWORDS = [kw for kws in COUNTRIES.values() for kw in kws]
SKIP_COUNTRY_NAMES = {"anycast", "anycast-ip", "unknown"}

# Кэш провайдера
ISP_CACHE = {}


def extract_first_seen_data(data):
    """
    Рекурсивно обойдет любую структуру (dict/list)
    и соберет словарь вида {"vless://...": "2026-09-11T14:07:27Z"}
    """
    cache_map = {}

    def parse_node(node):
        if isinstance(node, dict):
            if "key" in node and "first_seen" in node:
                cache_map[node["key"]] = node["first_seen"]
            for value in node.values():
                parse_node(value)
        elif isinstance(node, list):
            for item in node:
                parse_node(item)

    parse_node(data)
    return cache_map


def load_cache_map():
    """
    Загружает кэш из docs/cache_map.json.
    Если файла нет, восстанавливает базу из существующего docs/keys.json.
    """
    last_deleted = None
    cache_map = {}

    # 1. Пробуем прочитать готовый cache_map.json
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, "r", encoding="utf-8") as f:
                cache_map = json.load(f)
            print(f"Успешно загружен {CACHE_FILE} (записей: {len(cache_map)})")
        except Exception as e:
            print(f"Ошибка чтения {CACHE_FILE}: {e}")

    # 2. Если cache_map еще нет, но есть keys.json — вытаскиваем историю оттуда
    if os.path.exists(KEYS_FILE):
        try:
            with open(KEYS_FILE, "r", encoding="utf-8") as f:
                old_keys = json.load(f)
            last_deleted = old_keys.get("last_deleated_at") or old_keys.get("last_deleted_at")

            if not cache_map:
                cache_map = extract_first_seen_data(old_keys)
                print(f"[LOG] Восстановлен cache_map из {KEYS_FILE} (записей: {len(cache_map)})")
        except Exception as e:
            print(f"[LOG ERROR] Ошибка чтения {KEYS_FILE}: {e}")

    return cache_map, last_deleted


def save_cache_map(cache_map):
    """Сохраняет актуальную карту кэша в docs/cache_map.json"""
    os.makedirs("docs", exist_ok=True)
    try:
        with open(CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(cache_map, f, ensure_ascii=False, indent=2)
        print(f"Кэш успешно сохранён в {CACHE_FILE} (всего ключей: {len(cache_map)})")
    except Exception as e:
        print(f"Ошибка сохранения кэша: {e}")


def get_isp_info(host):
    if host in ISP_CACHE:
        return ISP_CACHE[host]

    try:
        ip = socket.gethostbyname(host)
        if ip in ISP_CACHE:
            ISP_CACHE[host] = ISP_CACHE[ip]
            return ISP_CACHE[host]

        url = f"http://ip-api.com/json/{ip}?fields=status,isp,org,as"
        resp = requests.get(url, timeout=3)
        if resp.status_code == 200:
            data = resp.json()
            if data["status"] == "success":
                isp_name = data.get("isp") or data.get("org") or "Неизвестен"
                ISP_CACHE[ip] = isp_name
                ISP_CACHE[host] = isp_name
                return isp_name
    except Exception:
        pass

    ISP_CACHE[host] = "Неизвестен"
    return "Неизвестен"


def parse_country_from_key(key):
    if '#' not in key:
        return None, None
    from urllib.parse import unquote
    fragment = unquote(key.split('#', 1)[1])
    match = re.search(
        r'([A-Z][A-Za-z\u00C0-\u017E](?:[A-Za-z\u00C0-\u017E\s\-]*[A-Za-z\u00C0-\u017E])?)(?:\s*[,|])',
        fragment
    )
    if not match:
        return None, None
    country = match.group(1).strip()
    flag = fragment[:match.start()].strip()
    return country, flag


def fetch_keys(url):
    resp = requests.get(url, timeout=15)
    resp.raise_for_status()
    lines = resp.text.strip().splitlines()
    return [line.strip() for line in lines if line.strip().startswith("vless://")]


def filter_keys(keys, mode):
    if mode in COUNTRIES:
        keywords = COUNTRIES[mode]
        return [k for k in keys if any(kw in k.lower() for kw in keywords)]
    if mode == "other":
        return [k for k in keys if
                not any(kw in k.lower() for kw in COUNTRIES_ALL_KEYWORDS) and "russia" not in k.lower()]
    if mode == "russia":
        return [k for k in keys if "russia" in k.lower()]
    if mode.startswith("w_"):
        country = mode[2:]
        if country in COUNTRIES:
            keywords = COUNTRIES[country]
            return [k for k in keys if any(kw in k.lower() for kw in keywords)]
        if country == "other":
            return [k for k in keys if
                    not any(kw in k.lower() for kw in COUNTRIES_ALL_KEYWORDS) and "russia" not in k.lower()]
    return keys


def parse_host_port(key):
    try:
        without_scheme = key[len("vless://"):]
        at_idx = without_scheme.rfind("@")
        after_at = without_scheme[at_idx + 1:]
        host_port = after_at.split("?")[0].split("#")[0]
        if ":" in host_port:
            host, port = host_port.rsplit(":", 1)
            return host.strip("[]"), int(port)
    except Exception:
        pass
    return None, None


def test_key(key):
    host, port = parse_host_port(key)
    if not host:
        return None
    try:
        infos = socket.getaddrinfo(host, port, socket.AF_UNSPEC, socket.SOCK_STREAM)
    except Exception:
        return None
    best = None
    for (family, socktype, proto, canonname, sockaddr) in infos:
        start = time.time()
        try:
            sock = socket.socket(family, socktype)
            sock.settimeout(TEST_TIMEOUT)
            result = sock.connect_ex(sockaddr)
            sock.close()
            elapsed = round((time.time() - start) * 1000, 1)
            if result == 0 and elapsed <= MAX_LATENCY_MS:
                if best is None or elapsed < best["latency_ms"]:
                    best = {"key": key, "host": host, "port": port, "latency_ms": elapsed}
        except Exception:
            pass
    return best


def check_mode(keys, cache_map):
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    working = []
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {executor.submit(test_key, key): key for key in keys}
        for future in as_completed(futures):
            result = future.result()
            if result:
                working.append(result)

    working.sort(key=lambda x: x["latency_ms"])

    # Привязываем first_seen из кэша либо записываем новое время
    for r in working:
        key_str = r["key"]
        if key_str in cache_map:
            r["first_seen"] = cache_map[key_str]
        else:
            r["first_seen"] = now
            cache_map[key_str] = now  # Сразу добавляем новый рабочий ключ в кэш

        r["isp"] = get_isp_info(r["host"])

    return {
        "best": working[0]["key"] if working else None,
        "top10": working[:10],
        "total_working": len(working),
        "total": len(keys),
    }


def main():
    # Загружаем текущий кэш
    cache_map, old_last_deleted = load_cache_map()
    initial_cache_size = len(cache_map)

    print("Загружаем BLACK (Домашний) ключи...")
    black_home_keys = fetch_keys(BLACK_URL)
    print(f"Загружено {len(black_home_keys)} BLACK (Домашний) ключей")

    print("Загружаем BLACK (Мобильный) ключи...")
    black_mobile_keys = fetch_keys(BLACK_MOBILE_URL)
    print(f"Загружено {len(black_mobile_keys)} BLACK (Мобильный) ключей")

    print("Загружаем WHITE ключи...")
    white_keys = fetch_keys(WHITE_URL)
    print(f"Загружено {len(white_keys)} WHITE ключей")

    now_utc = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    results = {
        "updated_at": now_utc,
        "last_deleated_at": old_last_deleted or now_utc,
    }

    # 1. Обычный VPN (BLACK) с разделением на home и mobile
    vpn_modes = list(COUNTRIES.keys()) + ["other"]
    for mode in vpn_modes:
        filtered_home = filter_keys(black_home_keys, mode)
        filtered_mobile = filter_keys(black_mobile_keys, mode)

        print(f"[{mode}] Проверяем Домашний ({len(filtered_home)}) и Мобильный ({len(filtered_mobile)})...")

        results[mode] = {
            "home": check_mode(filtered_home, cache_map),
            "mobile": check_mode(filtered_mobile, cache_map)
        }
        print(f"[{mode}] Домашний раб.: {results[mode]['home']['total_working']}/{results[mode]['home']['total']} | "
              f"Мобильный раб.: {results[mode]['mobile']['total_working']}/{results[mode]['mobile']['total']}")

    # Группировка прочих стран для раздела other_countries
    other_home_keys = filter_keys(black_home_keys, "other")
    other_mobile_keys = filter_keys(black_mobile_keys, "other")

    country_groups_home = defaultdict(list)
    country_groups_mobile = defaultdict(list)
    country_flags = {}

    for key in other_home_keys:
        name, flag = parse_country_from_key(key)
        if not name or name.lower() in SKIP_COUNTRY_NAMES:
            name, flag = "Other", "🌍"
        country_groups_home[name].append(key)
        country_flags[name] = flag

    for key in other_mobile_keys:
        name, flag = parse_country_from_key(key)
        if not name or name.lower() in SKIP_COUNTRY_NAMES:
            name, flag = "Other", "🌍"
        country_groups_mobile[name].append(key)
        country_flags[name] = flag

    all_other_names = set(country_groups_home.keys()) | set(country_groups_mobile.keys())
    other_countries = {}

    for name in all_other_names:
        h_keys = country_groups_home[name]
        m_keys = country_groups_mobile[name]
        checked_home = check_mode(h_keys, cache_map)
        checked_mobile = check_mode(m_keys, cache_map)

        other_countries[name] = {
            "flag": country_flags.get(name, "🌍"),
            "home": checked_home,
            "mobile": checked_mobile,
            "total_working": checked_home["total_working"] + checked_mobile["total_working"]
        }
    results["other_countries"] = other_countries

    # 2. Белые списки (WHITE)
    white_modes = ("w_baltics", "w_finland", "w_germany", "w_sweden", "w_netherlands", "w_poland", "w_other", "russia")
    for mode in white_modes:
        filtered = filter_keys(white_keys, mode)
        print(f"[{mode}] WHITE ключей: {len(filtered)}. Проверяем...")

        checked = check_mode(filtered, cache_map)
        results[mode] = {
            "home": checked,
            "mobile": checked
        }
        print(f"[{mode}] Рабочих: {checked['total_working']}/{checked['total']}")

    # Сохраняем итоговый keys.json
    os.makedirs("docs", exist_ok=True)
    with open(KEYS_FILE, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"Результаты сохранены в {KEYS_FILE}")

    # Сохраняем обновленный cache_map.json
    save_cache_map(cache_map)

    new_added = len(cache_map) - initial_cache_size

    def cleanup():
        if os.path.exists(CACHE_FILE):
            os.remove(CACHE_FILE)

    atexit.register(cleanup)

    print("Работа завершена!")

if __name__ == "__main__":
    main()