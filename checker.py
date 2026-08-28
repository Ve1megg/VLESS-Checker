#!/usr/bin/env python3
import socket
import time
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
import os
import subprocess
import webbrowser
import platform
import ctypes

#Имя файла-маркера для первого запуска
First_run_file = (".first_run.json")
#Единая ширина для интерфейса
WIDTH = 68

def install_requirments():
#Список нужных библиотек
    required_libraries = ["requests"]

    for library in required_libraries:
        try:
#Проверка установки библиотеки
            __import__(library)
        except ImportError:
            print(f"Библиотека {library} не найдена. Устанавливаем")
            try:

#Запускаем установку
                subprocess.check_call(
                                      [sys.executable, "-m", "pip", "install", library],
                                      stdout=subprocess.DEVNULL,
                                      stderr=subprocess.DEVNULL)
                print(f"{library} успешно установлено!")
            except Exception as e:
                print(f"Ошибка при установвке {library}: {e}")
                time.sleep(1)
                sys.exit(0)

#Проверка файла "first_run_file"
def check_first_run():
    if os.path.exists(First_run_file):
        return True

#Текст дисклймера
    disclaimer_text = f"""
┌────────────────────────────────────────────────────────────────────┐
│{"ДИСКЛЕЙМЕР".center(WIDTH)}│
├────────────────────────────────────────────────────────────────────┤                                                       
│Привет! Спасибо что пользуетесь Vless-checker.                      │
│Перед первым запуском утилиты прошу прочитайте этот текст           │
│                                                                    │
│[1. ЗАИМСТВОВАНИЕ КОДА И КОНТЕНТА ]                                 │
│В данной программе используется контент и частично заимствован код  │
│из открытых репозиториев разработчиков igareck (актуальные базы     │
│данных ключей) и tiagorrg (логика чекера). Автор утилиты (Ve1megg)  │
│уважает чужой труд, и не присваивает его себе и выражает огромную   │
│благодарность авторам за вклад в развитие свободного интернета.     │
│                                                                    │
│[2. ОТКАЗ ОТ ОТВЕТСТВЕННОСТИ ]                                      │
│Программа создана исключительно в ознакомительных, диагностических и│
│образовательных целях. Разработчик (Ve1megg) НЕ несёт никакой       │
│ответственности за то, как именно пользователи используют данное    │
│программное обеспечение, и за любые возможные последствия его       │
│использования.                                                      │
│                                                                    │
│[3. ЛИЦЕНЗИЯ И ОТКРЫТЫЙ КОД ]                                       │
│Проект является абсолютно бесплатным и распространяется под         │
│международной лицензией MIT. Вы имеете право                        │
│модифицировать, и распространять этот код, сохраняя упоминание      │
│автора.                                                             │
│                                                                    │       
│[4. БЕЗОПАСНОСТЬ И КОНФИДИЦИАЛЬНОСТЬ ]                              │
│Используя публичные VLESS-ключи, помните что они контролируються    │
│третьими лицами. Владельцы серверов могут анализировать ваш трафик  │
│и видеть ваши DNS-запросы. Настоятельно рекомендуем использовать    │
│публичные ключи для подключение к https:// сайтам, так как их трафик│
│шифруеться и владельцы сервера НЕ смогут перехватить ваши личные    │
│данные с паролями.                                                  │
│                                                                    │
│[5. АВТОМАТИЧЕСКАЯ НАСТРОЙКА ]                                      │
│Принимая данное соглашения, программа автоматически запустит процесс│
│проверки и установки библиотек (зависимостей), необходимых для      │
│коректной работы движка утилиты.                                    │
└────────────────────────────────────────────────────────────────────┘
"""
    print(disclaimer_text)

#Согласие на условие
    try:
        input("Вы согласны с условиями? \n(Нажмите Enter чтобы согласиться, чтобы отказаться закройте программу)")

#Если пользователь не прерывал программу
        print(f"\nПроверка и подготовка окружения...")
        install_requirments()

#Сохраняем маркер
        with open(First_run_file, "w", encoding="utf-8") as f:
            f.write("accepted\n")

        system = platform.system()

        if system == "Windows":
            try:
                ctypes.windll.kernel32.SetFileAttributesW(str(First_run_file), 0x02)
            except Exception:
                pass

        elif system == "Darwin":
            try:
                os.system(f"chflags hidden '{First_run_file}'")
            except Exception:
                pass

        print(f"\nУсловия приняты. Добро пожаловать!")
        time.sleep(1)

        os.system('cls' if os.name == 'nt' else 'clear')

        return True

    except (KeyboardInterrupt, EOFError):
        print(f"\nВы отклонили условия. Работа программы завершена.")
        sys.exit(0)

global requests
import requests

# Прямые ссылки на raw-файлы с ключами
Sources = {
    #Для домашнего интернета
    "Black_vless_home": "https://gitlab.com/igareck/vpn-configs-for-russia/-/raw/main/BLACK_VLESS_RUS.txt?ref_type=heads",
    "Whitelist_bypass_home": "https://gitlab.com/igareck/vpn-configs-for-russia/-/raw/main/WHITE-SNI-RU-all.txt?ref_type=heads",
    #Для мобильного интернета
    "Black_vless_mobile": "https://gitlab.com/igareck/vpn-configs-for-russia/-/raw/main/BLACK_VLESS_RUS_mobile.txt?ref_type=heads",
    "Whitelist_bypass_mobile": "https://gitlab.com/igareck/vpn-configs-for-russia/-/raw/main/Vless-Reality-White-Lists-Rus-Mobile.txt?ref_type=heads"
}

MAX_WORKERS = 15       # сколько ключей проверять параллельно
TEST_TIMEOUT = 5       # таймаут подключения в секундах
MAX_LATENCY_MS = 2000  # ключи медленнее этого — отбрасываем

#Интерактивное меню с защитой от ошибок
def select_sources_menu():
    while True:
        os.system('cls' if os.name == 'nt' else 'clear')

#Главное меню
        print("┌────────────────────────────────────────────────────────────────────┐")
        print(f"│{"VLESS-Checker v1.0.0 by Ve1megg".center(WIDTH)}│")
        print("├────────────────────────────────────────────────────────────────────┤")
        print("│Выберите вкладку в меню:                                            │")
        print("│1 - Проверка ключей                                                 │")
        print("│2 - Благодарности и пожертвования                                   │")
        print("│3 - Выход                                                           │")
        print("└────────────────────────────────────────────────────────────────────┘")

        menu_choice = input("→ Введите цифру для выбора: ")

#Выбор проверки ключей
        if menu_choice == "1":
         os.system('cls' if os.name == 'nt' else 'clear')
         while True:
          print("┌────────────────────────────────────────────────────────────────────┐")
          print("│Выберите режим проверки ключей:                                     │")
          print("│1 - Только обычные VLESS ключи для VPN                              │")
          print("│2 - Только VLESS ключи с обходом \"Белых списков\" для VPN            │")
          print("│3 - Назад                                                           │")
          print("└────────────────────────────────────────────────────────────────────┘")

          choice = input("→ Введите цифру для выбора: ")

          if choice == "3":
              os.system('cls' if os.name == 'nt' else 'clear')
              break

#Обычные vless ключи
          elif choice == "1":
              while True:
                 os.system('cls' if os.name == 'nt' else 'clear')

#Vless-ключи с обходом чёрных списков
                 print("┌────────────────────────────────────────────────────────────────────┐")
                 print("│→ Выбран режим: Только обычные VLESS ключи для VPN                  │")
                 print("├────────────────────────────────────────────────────────────────────┤")
                 print("│Выберите тип вашего интернета:                                      │")
                 print("│1 - Домашний интернет                                               │")
                 print("│2 - Мобильный интернет                                              │")
                 print("│3 - ← Назад                                                         │")
                 print("└────────────────────────────────────────────────────────────────────┘")

                 sec_choice = input("→ Введите цифру для выбора: ")

                 if sec_choice == "1":
                     return Sources["Black_vless_home"]
                 elif sec_choice == "2":
                     return Sources["Black_vless_mobile"]
                 elif sec_choice == "3":
                     os.system('cls' if os.name == 'nt' else 'clear')
                     break
                 else:
                     pass

#Vless ключи с обходом белых списков
          elif choice == "2":
             while True:
                 os.system('cls' if os.name == 'nt' else 'clear')
                 print("┌────────────────────────────────────────────────────────────────────┐")
                 print("│→ Выбран режим: Только VLESS ключи с обходом \"Белых списков\" для VPN│")
                 print("├────────────────────────────────────────────────────────────────────┤")
                 print("│Выберите тип вашего интернета:                                      │")
                 print("│1 - Домашний интернет                                               │")
                 print("│2 - Мобильный интернет                                              │")
                 print("│3 - ← Назад                                                         │")
                 print("└────────────────────────────────────────────────────────────────────┘")

                 sec_choice = input("→ Введите цифру для выбора: ")

                 if sec_choice == "1":
                     return Sources["Whitelist_bypass_home"]
                 elif sec_choice == "2":
                     return Sources["Whitelist_bypass_mobile"]
                 elif sec_choice == "3":
                     os.system('cls' if os.name == 'nt' else 'clear')
                     break
                 else:
                     pass
          else:
              os.system('cls' if os.name == 'nt' else 'clear')
              pass

#Меню благодарностей и пожертвований
        elif menu_choice == "2":
            while True:
                os.system('cls' if os.name == 'nt' else 'clear')

                print("┌────────────────────────────────────────────────────────────────────┐")
                print(f"│{"ОСОБЫЕ БЛАГОДАРНОСТИ".center(WIDTH)}│")
                print("├────────────────────────────────────────────────────────────────────┤")
                print("│1 - tiagorrg (логика чекера, автор оригинала и сайта с ключами)     │")
                print("│2 - igareck (базы данных ключей и постоянное обновлений данных      │")
                print("│И вы дорогой пользователь, спасибо что пользуетесь утилитой         │")
                print("├────────────────────────────────────────────────────────────────────┤")
                print(f"│{"ПОЖЕРТВОВАНИЯ".center(WIDTH)}│")
                print("├────────────────────────────────────────────────────────────────────┤")
                print("│Если данная утилита помогла вам, сохранило время, деньги, или может │")
                print("│быть нервы то вы можете поддержать меня рублём, просто выбирите     │")
                print("│пункт 3 или 4. Оставшиеся пункты ведут на Github Акаунты            │")
                print("│3 - Помочь со сбором на Donation Alerts                             │")
                print("│4 - Просто поддержать рублём на DALINK                              │")
                print("└────────────────────────────────────────────────────────────────────┘")



                cred_menu = input(" → Введите число для выбора, для выхода в прошлое меню введите 5: ")

#Ссылки и выход в главное меню
                if cred_menu == "1":
                    os.system('cls' if os.name == 'nt' else 'clear')
                    webbrowser.open("https://github.com/tiagorrg")
                elif cred_menu == "2":
                    os.system('cls' if os.name == 'nt' else 'clear')
                    webbrowser.open("https://github.com/igareck")
                elif cred_menu == "3":
                    os.system('cls' if os.name == 'nt' else 'clear')
                    webbrowser.open("https://www.donationalerts.com/r/ve1megg")
                elif cred_menu == "4":
                    os.system('cls' if os.name == 'nt' else 'clear')
                    webbrowser.open("https://dalink.to/ve1megg")
                elif cred_menu == "5":
                    os.system('cls' if os.name == 'nt' else 'clear')
                    break
                else:
                    os.system('cls' if os.name == 'nt' else 'clear')
                    pass

        elif menu_choice == "3":
            sys.exit(0)

#Команда для проверки работы дисклеймера (удаляет json маркер)
        elif menu_choice == "del first_run.json":
            os.remove("first_run.json")
            os.system('cls' if os.name == 'nt' else 'clear')

        else:
            os.system('cls' if os.name == 'nt' else 'clear')
            pass

def fetch_keys(url):
    print(f"Загружаем ключи из Gitlab...")
    try:
        resp = requests.get(url, timeout=15)
        resp.raise_for_status()
        lines = resp.text.strip().splitlines()
        keys = [line.strip() for line in lines if line.strip().startswith("vless://")]
        print(f"[+] Найдено {len(keys)} VLESS-ключей\n")
        return keys
    except Exception as e:
        print(f"[-] Ошибка загрузки: {e}")
        time.sleep(2)
        sys.exit(1)

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
        return {"key": key, "host": "?", "port": "?", "status": "invalid", "latency_ms": None}

    start = time.time()
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(TEST_TIMEOUT)
        result = sock.connect_ex((host, port))
        sock.close()
        elapsed = round((time.time() - start) * 1000, 1)

        if result == 0:
            return {"key": key, "host": host, "port": port, "status": "ok", "latency_ms": elapsed}
        else:
            return {"key": key, "host": host, "port": port, "status": "closed", "latency_ms": None}
    except Exception:
        return {"key": key, "host": host, "port": port, "status": "error", "latency_ms": None}

def main():
    check_first_run()

    while True:

# Получаем ссылку на основе выбора из меню
        selected_url = select_sources_menu()

# Очистка экрана
        os.system('cls' if os.name == 'nt' else 'clear')

# Передаем в выбранный URL
        keys = fetch_keys(selected_url)

        if not keys:
            print("[-] В выбранном источники не найдено ключей...\n")
            input(f"\nНажмите Enter, чтобы вернуться в главное меню: ")
            continue

        print(f"Начинаем параллельный тест {len(keys)}")
        results = []

        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            futures = {executor.submit(test_key, key): key for key in keys}
            done = 0
            for future in as_completed(futures):
                r = future.result()
                done += 1
                icon = "[+]" if r["status"] == "ok" else "[-]"
                latency = f"{r['latency_ms']} мс" if r["latency_ms"] else "недоступен"
                print(f"[{done}/{len(keys)}] {icon} {r['host']}:{r['port']} — {latency}")
                results.append(r)

# Фильтруем и сортируем
        working = sorted(
            [r for r in results if r["status"] == "ok" and r["latency_ms"] <= MAX_LATENCY_MS],
            key=lambda x: x["latency_ms"]
        )

        print("\n" + "─" * 70)
        print(f"ИТОГ: рабочих {len(working)} из {len(keys)}")
        print("─" * 70)

        if working:
            print(f"\nТОП-5 самых быстрых:")
            for i, r in enumerate(working[:5], 1):
                print(f"  {i}. {r['host']}:{r['port']} — {r['latency_ms']} мс")

# Сохраняем рабочие ключи
            with open("working_keys.txt", "w") as f:
                for r in working:
                    f.write(r["key"] + "\n")
            print(f"\nВсе рабочие ключи сохранены в working_keys.txt")

            print(f"\nЛУЧШИЙ КЛЮЧ:")
            print(f"\n{working[0]['key']}\n")
            input(f"\nНажмите Enter, чтобы вернуться в главное меню: ")
        else:
            print("[-] Рабочих ключей не найдено. Попробуй позже.")

if __name__ == "__main__":
   main()