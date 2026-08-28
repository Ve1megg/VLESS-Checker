import asyncio
import json
import time
from urllib.parse import urlparse
from typing import Optional, Tuple, Any

MAX_WORKERS = 20
TEST_TIMEOUT = 5
MAX_LATENCY_MS = 2000

keys_file = "docs/keys.json"


def parse_vless_target(vless_url: str) -> Tuple[Optional[str], Optional[int]]:
    try:
        if not vless_url.startswith("vless://"):
            return None, None

        parsed = urlparse(vless_url)
        netloc = parsed.netloc

        if "@" in netloc:
            netloc = netloc.split("@")[-1]

        if "]:" in netloc:
            host, port_str = netloc.rsplit(":", 1)
            host = host.strip("[]")
        elif ":" in netloc:
            host, port_str = netloc.rsplit(":", 1)
        else:
            host = netloc
            port_str = "443"

        return host, int(port_str)
    except Exception:
        return None, None


async def check_key_object(key_obj: dict, semaphore: asyncio.Semaphore) -> Optional[dict]:
    vless_url = key_obj.get("key", "")
    host = key_obj.get("host")
    port = key_obj.get("port")

    if not host or not port:
        host, port = parse_vless_target(vless_url)

    if not host or not port:
        return None

    async with semaphore:
        start_time = time.monotonic()
        try:
            conn = asyncio.open_connection(host, port)
            _, writer = await asyncio.wait_for(conn, timeout=TEST_TIMEOUT)

            latency = round((time.monotonic() - start_time) * 1000, 1)
            writer.close()
            await writer.wait_closed()

            if latency <= MAX_LATENCY_MS:
                key_obj["latency_ms"] = latency
                print(f"[ok] {latency} ms -> {host}:{port}")
                return key_obj
            else:
                print(f"[slow] {latency}ms > {MAX_LATENCY_MS}ms -> удалён")
                return None

        except Exception:
            print(f"[dead] {host}:{port} -> удалён")
            return None


async def process_item(item: Any, semaphore: asyncio.Semaphore) -> Any:
    # 1. Если элемент — объект VLESS-ключа
    if isinstance(item, dict) and "key" in item and isinstance(item["key"], str) and item["key"].startswith("vless://"):
        return await check_key_object(item, semaphore)

    # 2. Если элемент — список
    elif isinstance(item, list):
        tasks = [process_item(elem, semaphore) for elem in item]
        results = await asyncio.gather(*tasks)
        return [r for r in results if r is not None]

    # 3. Если элемент — словарь (страна, ветка home/mobile или корень)
    elif isinstance(item, dict):
        cleaned_dict = {}
        for k, v in item.items():
            if k in ("total_working", "total", "best"):
                continue
            res = await process_item(v, semaphore)
            if res is not None:
                cleaned_dict[k] = res

        # Если в объекте есть массив top10 (уровень home/mobile)
        if "top10" in cleaned_dict and isinstance(cleaned_dict["top10"], list):
            # Сортируем ключи по возрастанию задержки (ms)
            cleaned_dict["top10"].sort(
                key=lambda x: x.get("latency_ms", 99999) if isinstance(x, dict) else 99999
            )
            count = len(cleaned_dict["top10"])

            # Восстанавливаем корректные счётчики и определяем лучший ключ
            cleaned_dict["total_working"] = count
            cleaned_dict["total"] = count
            if count > 0 and isinstance(cleaned_dict["top10"][0], dict):
                cleaned_dict["best"] = cleaned_dict["top10"][0].get("key")
            else:
                cleaned_dict["best"] = None

        return cleaned_dict

    return item


def count_total_keys(data: Any) -> int:
    """Подсчёт общего количества VLESS-ключей в структуре"""
    count = 0
    if isinstance(data, dict):
        if "key" in data and isinstance(data["key"], str) and data["key"].startswith("vless://"):
            return 1
        for v in data.values():
            count += count_total_keys(v)
    elif isinstance(data, list):
        for elem in data:
            count += count_total_keys(elem)
    return count


async def main():
    print(f"Загрузка ключей из {keys_file}...")
    try:
        with open(keys_file, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        print(f"Ошибка чтения файла {keys_file}: {e}")
        return

    initial_key_count = count_total_keys(data)
    print(f"Всего ключей до проверки: {initial_key_count}")

    semaphore = asyncio.Semaphore(MAX_WORKERS)

    print("Начинаем асинхронную проверку...")
    cleaned_data = await process_item(data, semaphore)

    if isinstance(cleaned_data, dict):
        now_utc = time.strftime("%Y-%m-%d %H:%M UTC", time.gmtime())
        cleaned_data["last_deleted_at"] = now_utc

    final_key_count = count_total_keys(cleaned_data)
    print(f"Осталось рабочих ключей: {final_key_count}")

    # Защитный механизм: если исходных ключей было много, а стало 0 — отменяем запись
    if initial_key_count >= 5 and final_key_count == 0:
        print("⚠️ ОШИБКА: Скрипт отбраковал 100% ключей. Возможно, пропала сеть. Файл не перезаписан.")
        return

    print(f"Сохранение отфильтрованных данных в {keys_file}...")
    with open(keys_file, "w", encoding="utf-8") as f:
        json.dump(cleaned_data, f, ensure_ascii=False, indent=2)

    print("✅ Очистка и обновление JSON завершены!")


if __name__ == "__main__":
    asyncio.run(main())