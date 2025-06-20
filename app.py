from flask import Flask, render_template, request, redirect, url_for, flash,jsonify,send_from_directory
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
import time
from threading import Thread, Event
import configparser
import json
import os
from queue import Queue
import logging
from parser_tandem import init_parsing
from unzip import unzip
from my_html import creatCsv
from FTPupload import upload
import json
import logging
from logging.handlers import RotatingFileHandler
import sys
from markupsafe import Markup 
from werkzeug.security import generate_password_hash, check_password_hash
app = Flask(__name__)
app.secret_key = '4483232327310370'  # Замените на случайный секретный ключ

# Настройка Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# Простая модель пользователя
class User(UserMixin):
    def __init__(self, id, username, password):
        self.id = id
        self.username = username
        self.password = password

# Создаем тестового пользователя (в реальном приложении храните хэши паролей и загружайте из БД)
users = {
    1: User(1, 'vakhonin', generate_password_hash('283509'))
}
# Установка лимитов в начале приложения
@login_manager.user_loader
def load_user(user_id):
    return users.get(int(user_id))

# Состояние приложения
app_output = "Готов к работе..."
is_running = False
stop_event = Event()
output_queue = Queue()

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def background_monitor():
    """Фоновая задача для обновления app_output из очереди"""
    global app_output
    while is_running:
        try:
            # Получаем все новые сообщения из очереди
            messages = []
            while not output_queue.empty():
                messages.append(output_queue.get_nowait())
            
            if messages:
                app_output = "\n".join(messages)
            
            time.sleep(0.5)
        except Exception as e:
            logger.error(f"Ошибка в background_monitor: {str(e)}")
            time.sleep(1)

def main():
    """Основная функция парсинга и обработки данных"""
    try:
        while not stop_event.is_set():
            config = configparser.ConfigParser()
            try:
                with open('templates/config.ini', encoding='utf-8-sig') as fp:
                    config.read_file(fp)
                # Получение параметров конфигурации
                HOSTNAME = config.get('ftp', 'hostname')
                USERNAME = config.get('ftp', 'username')
                PASSWORD = config.get('ftp', 'password')
                dirload = config.get('tndm', 'dirload')
                wakeup=config.get('time', 'wakeup')

                url = config.get('tndm', 'url')
                company=config.get('tndm', 'company')
                login_headers = json.loads(config.get('login', 'headers'))
                login_params = json.loads(config.get('login', 'params'))
                
                output_queue.put("Конфиг получен успешно")
                logging.info("Конфиг получен успешно") 
                # Инициализация парсинга
                downloaded_file,logs = init_parsing(url, login_params, login_headers,company,dirload)
                output_queue.put(f"Логи парсинга: {logs}")
                logging.info(f"Логи парсинга: {logs}") 
                if "Не удалось авторизоваться. Проверьте логин и пароль." in logs:
                    break
                try:
                    unzip(os.path.join(dirload, downloaded_file))
                    output_queue.put('Распаковка файла успешна')
                    logging.info('Распаковка файла успешна') 
                except Exception as e:
                    output_queue.put(f'Ошибка распаковки: {str(e)}')
                    logging.error(f'Ошибка распаковки: {str(e)}') 
                    break
                # Создание CSV и загрузка файлов
                listname = creatCsv(dirload, os.path.join(downloaded_file[:-4]))
                
                for name in listname:
                    upload(os.path.join(dirload, name + '.html'), 
                          name + '.html', HOSTNAME, USERNAME, PASSWORD)
                    output_queue.put(f"Загружено: {name}.html")
                    logging.info(f"Загружено: {name}.html") 

                output_queue.put('Все операции завершены')
                logging.info('Все операции завершены')
            except Exception as e:
                output_queue.put(f'Произошла ошибка: {str(e)}')
                logging.error(f"Ошибка в main: {str(e)}")
            # Ожидание перед следующей итерацией
            for _ in range(60):
                if stop_event.is_set():
                    break
                time.sleep(float(wakeup))
                
    finally:
        global is_running
        is_running = False
        output_queue.put("STOP_STREAM")
        logger.info("Основной процесс остановлен")

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        # Ищем пользователя
        user = None
        for u in users.values():
            if u.username == username:
                user = u
                break
        
        # Проверяем пользователя и пароль
        if user and check_password_hash(user.password, password):
            login_user(user)
            next_page = request.args.get('next')
            return redirect(next_page or url_for('index'))
        else:
            flash('Неверное имя пользователя или пароль')
    
    return render_template('login.html')

@app.route('/download_log/<filename>')

def download_log(filename):
    return send_from_directory('logs', filename, as_attachment=True)

@app.route('/download_html/<filename>')
def download_html(filename):
    return send_from_directory('logs', filename, as_attachment=True)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

# Защищаем все основные маршруты декоратором @login_required
@app.route('/')
@login_required
def index():
    return render_template('index.html', output_content=app_output)

@app.route('/start')
@login_required
def start_app():
    global is_running, stop_event
    if not is_running:
        is_running = True
        stop_event.clear()
        output_queue.put("Приложение запущено")
        Thread(target=background_monitor, daemon=True).start()
        Thread(target=main, daemon=True).start()
    return app_output

@app.route('/stop')
@login_required
def stop_app():
    global is_running
    if is_running:
        output_queue.put("Приложение остановлено")
        stop_event.set()
        is_running = False
    return app_output

@app.route('/get_output')
@login_required
def get_output():
    return app_output

@app.template_filter('clean_json')
def clean_json_filter(value):
    try:
        # Удаляем все HTML-теги если они есть
        clean_value = str(value).replace('<pre>', '').replace('</pre>', '').strip()
        if not clean_value:
            return '{}'
        
        # Парсим и переформатируем JSON
        parsed = json.loads(clean_value)
        return json.dumps(parsed, indent=2, ensure_ascii=False)
    except json.JSONDecodeError:
        return value  # Возвращаем как есть если невалидный JSON

@app.route('/edit_config', methods=['GET', 'POST'])
@login_required
def edit_config():
    if request.method == 'POST':
        config = configparser.ConfigParser()
        config.read_dict({
            'tndm': {
                'dirload': request.form.get('tndm_dirload'),
                'url': request.form.get('tndm_url'),
                'company': request.form.get('tndm_company')
            },
            'ftp': {
                'hostname': request.form.get('ftp_hostname'),
                'username': request.form.get('ftp_username'),
                'password': request.form.get('ftp_password')
            },
            'time': {
                'wakeup': request.form.get('time_wakeup')
            },
            'login': {
                'headers': request.form.get('login_headers'),
                'params': request.form.get('login_params')
            }
        })
        
        with open('templates/config.ini', 'w', encoding='utf-8') as configfile:
            config.write(configfile)
        
        return redirect(url_for('index'))
    
    config = configparser.ConfigParser()
    config.read('templates/config.ini', encoding='utf-8-sig')
    return render_template('edit_config.html', config=config)

# Настройка логгера
@app.route('/status')
def server_status():
    import psutil
    import threading
    status = {
        'memory': psutil.virtual_memory()._asdict(),
        'cpu': psutil.cpu_percent(),
        'disk': psutil.disk_usage('/')._asdict(),
        'is_running': is_running,
        'threads': threading.active_count()
    }
    return jsonify(status)
def setup_logger():
    # Создаем директорию для логов если ее нет
    log_dir = 'logs'
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
    
    # Останавливаем все предыдущие обработчики
    for handler in logging.root.handlers[:]:
        logging.root.removeHandler(handler)
    
    # Настройка формата логов
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Файловый обработчик с ротацией
    file_handler = RotatingFileHandler(
        'logs/app.log',
        maxBytes=10*1024*1024,  # 10 MB
        backupCount=5,
        encoding='utf-8'
    )
    file_handler.setFormatter(formatter)
    file_handler.setLevel(logging.INFO)
    
    # Обработчик для stdout
    stdout_handler = logging.StreamHandler(sys.stdout)
    stdout_handler.setFormatter(formatter)
    stdout_handler.setLevel(logging.INFO)
    
    # Получаем корневой логгер
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    
    # Удаляем все существующие обработчики
    logger.handlers.clear()
    
    # Добавляем наши обработчики
    logger.addHandler(file_handler)
    logger.addHandler(stdout_handler)
    
    # Настройка для предотвращения рекурсии
    logging.getLogger('werkzeug').setLevel(logging.WARNING)
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    logging.getLogger('asyncio').setLevel(logging.WARNING)

# Класс для перенаправления stdout/stderr в логгер
class StreamToLogger(object):
    def __init__(self, logger, log_level):
        self.logger = logger
        self.log_level = log_level
        self.linebuf = ''
    
    def write(self, buf):
        for line in buf.rstrip().splitlines():
            self.logger.log(self.log_level, line.rstrip())
    
    def flush(self):
        pass

# Инициализация логгера при старте
setup_logger()
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=6565, debug=True)