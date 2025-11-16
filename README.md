## Локальный запуск (для разработки)

### 1. Установка зависимостей
```bash
# Клонируйте репозиторий
git clone <repository-url>
cd films

# Установите зависимости
pip install -r requirements.txt
2. Настройка базы данных
bash
# Вариант 1: Запуск PostgreSQL в Docker
docker run --name movie-db -e POSTGRES_PASSWORD=password -e POSTGRES_DB=movie_reviews -p 5432:5432 -d postgres:13

# Вариант 2: Использование существующей PostgreSQL
# Убедитесь, что PostgreSQL запущен на порту 5432
3. Настройка окружения
Создайте файл .env в корне проекта:

env
DB_HOST=localhost
DB_PORT=5432
DB_USER=postgres
DB_PASSWORD=password
DB_NAME=movie_reviews
TELEGRAM_BOT_TOKEN=your_bot_token_here
4. Инициализация базы данных
bash
# Создание таблиц (автоматически при первом запуске)
# Или вручную:
psql -h localhost -U postgres -d movie_reviews -f schema.sql
5. Создание Telegram бота
Найдите @BotFather в Telegram

Отправьте /newbot

Укажите имя бота

Получите токен

Добавьте токен в .env файл

6. Запуск приложения
bash
python run.py
7. Проверка работы
Веб-приложение: http://localhost:8000

API документация: http://localhost:8000/api/docs

Бот: найдите в Telegram по имени

Развертывание в Yandex Cloud
1. Подготовка облака
Создайте аккаунт Yandex Cloud

Активируйте сертификат Education

Создайте каталог

2. Создание Виртуальной Машины
В Console Yandex Cloud → Compute Cloud

Создать ВМ:

Имя: movie-app-vm

Образ: Ubuntu 22.04

Платформа: Intel Cascade Lake

Пресет: 2 vCPU, 2 GB RAM

Диск: 20 GB SSD

Публичный IP: Автоматически

Настройте Security Groups (откройте порты):

22 (SSH)

80 (HTTP)

443 (HTTPS)

8000 (Приложение)

3. Настройка сервера
bash
# Подключитесь к серверу
ssh ubuntu@<ВНЕШНИЙ_IP_АДРЕС>

# Обновите систему
sudo apt update && sudo apt upgrade -y

# Установите пакеты
sudo apt install python3-pip python3-venv nginx postgresql-client git -y

# Настройте брандмауэр
sudo ufw allow 22
sudo ufw allow 80
sudo ufw allow 443
sudo ufw allow 8000
sudo ufw enable
4. Развертывание приложения
bash
# Клонируйте проект
git clone <ВАШ_REPO_URL>
cd films

# Создайте виртуальное окружение
python3 -m venv venv
source venv/bin/activate

# Установите зависимости
pip install -r requirements.txt
5. Настройка базы данных
В Yandex Cloud → Managed Service for PostgreSQL

Создайте кластер БД

Получите параметры подключения:

Хост

Пользователь

Пароль

Создайте файл .env:

env
DB_HOST=<YANDEX_DB_HOST>
DB_PORT=5432
DB_USER=<DB_USER>
DB_PASSWORD=<DB_PASSWORD>
DB_NAME=movie_reviews
TELEGRAM_BOT_TOKEN=<BOT_TOKEN>
Импортируйте схему:

bash
psql -h <DB_HOST> -U <USER> -d movie_reviews -f schema.sql
6. Настройка Nginx
bash
# Создайте конфиг
sudo nano /etc/nginx/sites-available/movie-app
Добавьте:

nginx
server {
    listen 80;
    server_name ваш-домен.ru;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
Активируйте:

bash
sudo ln -s /etc/nginx/sites-available/movie-app /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
7. Запуск как сервиса
bash
# Создайте сервисный файл
sudo nano /etc/systemd/system/movie-app.service
Добавьте:

ini
[Unit]
Description=Movie Reviews App
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/ubuntu/films
Environment=PATH=/home/ubuntu/films/venv/bin
ExecStart=/home/ubuntu/films/venv/bin/python run.py
Restart=always

[Install]
WantedBy=multi-user.target
Запустите:

bash
sudo systemctl daemon-reload
sudo systemctl enable movie-app
sudo systemctl start movie-app
