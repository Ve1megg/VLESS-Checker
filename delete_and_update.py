import asyncio
import json
import time
from urllib.parse import urlparse
from typing import Optional, Tuple, Any

#Конфигурации для проверки ключей
MAX_WORKERS = 20
TEST_TIMEOUT = 5
MAX_LATENCY_MS = 2000

#Файл для получения ключей
keys_file = "docs/keys.json"

#Функция для извлечения хоста и порта из vless:// ссылки.
def parse_vless_target(vless_url: str) -> Tuple[Optional[str], Optional[int]]:
    try:
        if not vless_url.startswith("vless://"):
            return None, None

        parsed = urlparse(vless_url)
        netloc = parsed.netloc

#Отрезаем UUID / пароль (всё что до @)
        if "@" in netloc:
            netloc = netloc.split("@")[-1]

#Разбираем host:port (с учётом IPv6)
        if "]:" in netloc:
            host, port_str = netloc.rsplit(":", 1)
            host = host.strip("[]")
        elif ":" in netloc:
            host, port_str = netloc.rsplit(":", 1)
        else:
            host = netloc
            port_str = "443" #Стандартный порт VLESS по умолчанию

        return host, int(port_str)
    except Exception:
        return None, None

#Проверка ключ-объекта
async def check_key_object(key_obj: dict, semaphore: asyncio.Semaphore) -> Optional[dict]:
    vless_url = key_obj.get("key", "")
    host = key_obj.get("host")
    port = key_obj.get("port")

#Если нет данных для проверки задержки - пробуем распарсить
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
#Обновляем пинг в объекте и возвращаем его со всеми исходными данными
                key_obj["latency_ms"] = latency
                print(f"[ok] {latency} ms -> {host}:{port}")
                return key_obj
            else:
                print(f"[slow] {latency}ms > {MAX_LATENCY_MS}ms -> удалён")
                return None

        except Exception:
            print(f"[dead] {host}:{port} -> удалён")
            return None

#Рекурсивная обработка структуры JSON
async def process_item(item: Any, semaphore: asyncio.Semaphore) -> Any:
#1. Если элемент - объект ключа с поля "key"
    if isinstance(item, dict) and "key" in item and isinstance(item["key"], str) and item["key"].startswith("vless://"):
            return await check_key_object(item, semaphore)

#2. Если элемент - список
    elif isinstance(item, list):
        tasks = [process_item(elem, semaphore) for elem in item]
        results = await asyncio.gather(*tasks)
        return [r for r in results if r is not None]

#3. Если элемент - родительский словарь
    elif isinstance(item, dict):
        cleaned_dict = {}
        for k, v in item.items():
            if k in ("total_working", "total"):
                continue
            res = await process_item(v, semaphore)
            if res is not None:
                cleaned_dict[k] = res
        return cleaned_dict

    return item

async def main():
    print(f"Загрузка ключей из {keys_file}...")
    try:
        with open(keys_file, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        print(f"Ошибка чтения файла {keys_file}: {e}")
        return

    semaphore = asyncio.Semaphore(MAX_WORKERS)

    print("Начинаем асинхронную проверку...")
    cleaned_data = await process_item(data, semaphore)

# Корректная обработка структуры по странам
    if isinstance(cleaned_data, dict):
        for key, country_data in cleaned_data.items():
# Работаем только со словарями стран (пропускаем "updated_at" и т.д.)
            if isinstance(country_data, dict) and "top10" in country_data:
                top10_list = country_data.get("top10", [])
                count = len(top10_list)

# 1. Обновляем счётчики для конкретной страны
                country_data["total_working"] = count
                country_data["total"] = count

# 2. Синхронизируем best (берём первый рабочий ключ из top10)
                if top10_list and isinstance(top10_list[0], dict):
                    country_data["best"] = top10_list[0].get("key")
                else:
                    country_data["best"] = None

# Обновляем время проверки
        now_utc = time.strftime("%Y-%m-%d %H:%M UTC", time.gmtime())
        cleaned_data["last_deleted_at"] = now_utc

    print(f"Сохранение отфильтрованных данных в {keys_file}...")
    with open(keys_file, "w", encoding="utf-8") as f:
        json.dump(cleaned_data, f, ensure_ascii=False, indent=2)

    print("✅ Очистка и обновление JSON завершены!")

if __name__ == "__main__":
    asyncio.run(main())