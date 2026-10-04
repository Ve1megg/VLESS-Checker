#!/usr/bin/env bash

cd "$(dirname "$0")"

if command -v python3 &>/dev/null; then
python3 checker.py
exit 0
fi

echo ""
echo "[!] Python 3 не обнаружен в вашей системе."
read -p "Хотите установить Python 3 автоматически? (y/n / д/н): " choice

case "$choice" in
[Yy1Дд]* )
echo ""
echo "[*] Установка Python 3..."
if command -v apt &>/dev/null; then
sudo apt update && sudo apt install -y python3 python3-pip
elif command -v dnf &>/dev/null; then
sudo dnf install -y python3
elif command -v pacman &>/dev/null; then
sudo pacman -S --noconfirm python
elif command -v brew &>/dev/null; then
brew install python
else
echo "[!] Не удалось определить пакетный менеджер. Пожалуйста, установите python3 вручную."
exit 1
fi
;;
* )
echo "Установка отменена. Завершение работы."
exit 0
;;
esac

if command -v python3 &>/dev/null; then
echo "[✓] Python успешно установлен! Запускаем checker.py..."
python3 checker.py
else
echo "[!] Ошибка установки Python. Попробуйте установить его вручную."
fi