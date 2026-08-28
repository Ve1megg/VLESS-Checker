import re
import requests
import socket
import time
import json
import os
from collections import defaultdict
from datetime import datetime, timezone
from concurrent.futures import ThreadPoolExecutor, as_completed

BLACK_URL = "https://gitlab.com/igareck/vpn-configs-for-russia/-/raw/main/BLACK_VLESS_RUS.txt?ref_type=heads"
BLACK_MOBILE_URL = "https://gitlab.com/igareck/vpn-configs-for-russia/-/raw/main/BLACK_VLESS_RUS_mobile.txt?ref_type=heads"
WHITE_URL = "https://gitlab.com/igareck/vpn-configs-for-russia/-/raw/main/WHITE-SNI-RU-all.txt?ref_type=heads"
WHITE_URL_MOBILE = "https://gitlab.com/igareck/vpn-configs-for-russia/-/raw/main/Vless-Reality-White-Lists-Rus-Mobile.txt?ref_type=heads"

MAX_WORKERS = 20
TEST_TIMEOUT = 5
MAX_LATENCY_MS = 2000

COUNTRIES = {
    "baltics":     ["lithuania", "estonia", "latvia"],
    "finland":     ["finland"],
    "germany":     ["germany"],
    "sweden":      ["sweden"],
    "netherlands": ["netherlands"],
    "poland":      ["poland"],
}

COUNTRIES_ALL_KEYWORDS = [kw for kws in COUNTRIES.values() for kw in kws]

SKIP_COUNTRY_NAMES = {"anycast", "anycast-ip", "unknown"}

def parse_country_from_key(key):
    """Returns (country_name, flag_emoji) parsed from the key's URL fragment."""
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
        return [k for k in keys if not any(kw in k.lower() for kw in COUNTRIES_ALL_KEYWORDS) and "russia" not in k.lower()]
    if mode == "russia":
        return [k for k in keys if "russia" in k.lower()]
    if mode.startswith("w_"):
        country = mode[2:]
        if country in COUNTRIES:
            keywords = COUNTRIES[country]
            return [k for k in keys if any(kw in k.lower() for kw in keywords)]
        if country == "other":
            return [k for k in keys if not any(kw in k.lower() for kw in COUNTRIES_ALL_KEYWORDS) and "russia" not in k.lower()]
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


def check_mode(keys, old_first_seen=None):
    if old_first_seen is None:
        old_first_seen = {}
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    working = []
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {executor.submit(test_key, key): key for key in keys}
        for future in as_completed(futures):
            result = future.result()
            if result:
                working.append(result)

    working.sort(key=lambda x: x["latency_ms"])

    for r in working:
        r["first_seen"] = old_first_seen.get(r["key"], now)

    return {
        "best": working[0]["key"] if working else None,
        "top10": working[:10],
        "total_working": len(working),
        "total": len(keys),
    }


def load_old_first_seen():
    try:
        with open("docs/keys.json", "r", encoding="utf-8") as f:
            old = json.load(f)
        seen = {}
        old_last_deleted = old.get("last_deleted_at")

        def extract_keys(container):
            if not isinstance(container, dict):
                return
            top_list = container.get("top10")
            if isinstance(top_list, dict):
                for entry in top_list:
                    if isinstance(entry, dict) and "key" in entry and "first_seen" in entry:
                        seen[entry["key"]] = entry["first_seen"]

        for mode_data in old.values():
            if isinstance(mode_data, dict):
                extract_keys(mode_data)
                extract_keys(mode_data.get("home"))
                extract_keys(mode_data.get("mobile"))
        return seen, old_last_deleted
    except Exception:
        return {}, None


def main():
    old_first_seen, old_last_deleted = load_old_first_seen()

    print("Загружаем BLACK (Домашний) ключи...")
    black_home_keys = fetch_keys(BLACK_URL)
    print(f"Загружено {len(black_home_keys)} BLACK (Домашний) ключей")

    print("Загружаем BLACK (Мобильный) ключи...")
    black_mobile_keys = fetch_keys(BLACK_MOBILE_URL)
    print(f"Загружено {len(black_mobile_keys)} BLACK (Мобильный) ключей")

    print("Загружаем WHITE ключи...")
    white_keys = fetch_keys(WHITE_URL)
    print(f"Загружено {len(white_keys)} WHITE ключей")

    now_utc = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M UTC")

    results = {
        "updated_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        "last_deleated_at": old_last_deleted or now_utc,
    }

    # 1. Обычный VPN (BLACK) с разделением на home и mobile
    vpn_modes = list(COUNTRIES.keys()) + ["other"]
    for mode in vpn_modes:
        filtered_home = filter_keys(black_home_keys, mode)
        filtered_mobile = filter_keys(black_mobile_keys, mode)

        print(f"[{mode}] Проверяем Домашний ({len(filtered_home)}) и Мобильный ({len(filtered_mobile)})...")

        results[mode] = {
            "home": check_mode(filtered_home, old_first_seen),
            "mobile": check_mode(filtered_mobile, old_first_seen)
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
        checked_home = check_mode(h_keys, old_first_seen)
        checked_mobile = check_mode(m_keys, old_first_seen)

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

        checked = check_mode(filtered, old_first_seen)
        results[mode] = {
            "home": checked,
            "mobile": checked
        }
        print(f"[{mode}] Рабочих: {checked['total_working']}/{checked['total']}")

    os.makedirs("docs", exist_ok=True)
    with open("docs/keys.json", "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    print("Сохранено в docs/keys.json")

if __name__ == "__main__":
    main()
