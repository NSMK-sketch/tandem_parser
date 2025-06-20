import requests
from urllib.parse import urljoin
from bs4 import BeautifulSoup
import os
import time
import re

def login_to_portal(base_url, params, login_header):
    logs = []
    session = requests.Session()
    session.headers.update(login_header)
    logs.append("Получаем начальную страницу...")
    try:
        initial_response = session.get(base_url)
        initial_response.raise_for_status()
        logs.append(f"Статус: {initial_response.status_code}, Куки: {session.cookies.get_dict()}")
    except Exception as e:
        logs.append(f"Ошибка при получении начальной страницы: {e}")
        return None, logs

    try:
        soup = BeautifulSoup(initial_response.text, 'html.parser')
        seedids = soup.find('input', {'name': 'seedids'})['value'] if soup.find('input', {'name': 'seedids'}) else ""
        bc = soup.find('input', {'name': 'bc'})['value'] if soup.find('input', {'name': 'bc'}) else ""
    except Exception as e:
        logs.append(f"Ошибка при парсинге HTML: {e}")
        return None, logs

    logs.append("\nОтправляем данные для входа...")
    try:
        login_response = session.post(
            base_url,
            headers={
                "Referer": base_url,
                "X-KL-kfa-Ajax-Request": "Ajax_Request",
                "dojo-ajax-request": "true"
            },
            data={"formids": "",
                  "seedids": seedids,
                  "bc": bc, **params})
        login_response.raise_for_status()
    except Exception as e:
        logs.append(f"Ошибка при отправке данных входа: {e}")
        return None, logs

    if login_response.status_code == 200 and "ajax-response" in login_response.text:
        logs.append("\nОбнаружен AJAX-редирект, извлекаем новый URL...")
        redirect_match = re.search(r'window\.location\s*=\s*"([^"]+)"', login_response.text)
        
        if redirect_match:
            redirect_url = redirect_match.group(1)
            logs.append(f"Редирект на: {redirect_url}")
            return follow_redirect(session, base_url, redirect_url, "login_redirect")
        else:
            logs.append("❌ Не удалось извлечь URL редиректа")
    else:
        logs.append("❌ Не получен ожидаемый AJAX-ответ")
    
    return None, logs

def follow_redirect(session, base_url, redirect_url_or_html, step):
    logs = []
    try:
        if isinstance(redirect_url_or_html, str) and '<html' in redirect_url_or_html.lower():
            link = extract_link_from_html(redirect_url_or_html)
            if not link:
                logs.append("❌ Не удалось извлечь ссылку из HTML")
                return None, logs
            full_redirect_url = urljoin(base_url, link)
        else:
            full_redirect_url = urljoin(base_url, redirect_url_or_html)
        
        logs.append(f"Выполняем редирект на: {full_redirect_url}")
        redirected_response = session.get(full_redirect_url)
        redirected_response.raise_for_status()
        
        if "Введите логин и пароль" not in redirected_response.text:
            logs.append("✅ Вход/переход выполнен успешно!")
            
            if step == "login_redirect":
                filename = "logs/success_page1.html"
            elif step == "menu_redirect": 
                filename = "logs/success_page2.html"
            elif step == "service_redirect":
                filename = "logs/success_page3.html"
            else:
                filename = f"logs/success_unknown_{int(time.time())}.html"
            
            with open(filename, "w", encoding="utf-8") as f:
                f.write(redirected_response.text)
                logs.append("\n" + "="*50)
                logs.append(f"Полное содержимое сохранено в {filename}")
            return session, logs
        else:
            logs.append("❌ Ошибка: Форма входа снова отобразилась")
    except Exception as e:
        logs.append(f"Ошибка при выполнении редиректа: {e}")
    
    return None, logs

def extract_link_from_html(html_content):
    soup = BeautifulSoup(html_content, 'html.parser')
    link_element = soup.find('a', {'id': 'bcLink_0'})
    if link_element:
        return link_element.get('href')
    return None

def post_to_success_page2(base_url, session):
    logs = []
    try:
        with open("logs/success_page2.html", "r", encoding="utf-8") as f:
            html_content = f.read()
    except Exception as e:
        logs.append(f"Ошибка при чтении файла success_page2.html: {e}")
        return None, logs

    soup = BeautifulSoup(html_content, 'html.parser')
    form_hidden = soup.find('div', {'id': 'formhidden'})
    if not form_hidden:
        logs.append("❌ Не найдена скрытая форма с параметрами")
        return None, logs

    post_data = {}
    for input_tag in form_hidden.find_all('input', {'type': 'hidden'}):
        name = input_tag.get('name')
        value = input_tag.get('value', '')
        if name:
            post_data[name] = value

    post_data.update({
        "submitmode": "refresh",
        "submitname": "submitButton_exportRatings",
        "_searchDiv__": "",
        "_searchDiv___id": "searchDiv___w"
    })

    collapsed_params = [
        "unienr14_SysActPanel_SettingsKey", "unischedule_SysActPanel_SettingsKey",
    ]
    for param in collapsed_params:
        post_data[f"{param}_collapsed"] = "0"

    form = soup.find('form', {'id': 'form'})
    action_url = urljoin(base_url, form['action']) if form else base_url

    headers = {
        "Referer": f"{base_url}?bc={post_data.get('bc', '')}&service=bcs&site={post_data.get('site', '')}"
    }

    logs.append("Отправляем POST-запрос с параметрами из success_page2.html...")
    try:
        response = session.post(
            action_url,
            headers=headers,
            data=post_data
        )
        response.raise_for_status()
        
        logs.append(f"POST-запрос выполнен успешно! Статус: {response.status_code}")
        
        with open("logs/success_page3.html", "w", encoding="utf-8") as f:
            f.write(response.text)
            
        return response, logs
    except Exception as e:
        logs.append(f"Ошибка при выполнении POST-запроса: {e}")
        return None, logs

def post_to_success_page3(base_url,session,company):
    logs = []
    try:
        with open("logs/success_page3.html", "r", encoding="utf-8") as f:
            html_content = f.read()
    except Exception as e:
        logs.append(f"Ошибка при чтении файла success_page3.html: {e}")
        return None, logs

    soup = BeautifulSoup(html_content, 'html.parser')
    form_hidden = soup.find('div', {'id': 'formhidden'})
    if not form_hidden:
        logs.append("❌ Не найдена скрытая форма с параметрами")
        return None, logs

    post_data = {}
    for input_tag in form_hidden.find_all('input', {'type': 'hidden'}):
        name = input_tag.get('name')
        value = input_tag.get('value', '')
        if name:
            post_data[name] = value

    post_data.update({
        "submitmode": "",
        "submitname": "mSubmit_bcDialog",
        "_searchDiv__": "",
        "_searchDiv___id": "searchDiv___w",
        "_enrollmentCampaign_bcDialog": company,
        "_enrollmentCampaign_bcDialog_id":"enrollmentCampaign_bcDialog_w"
    })

    collapsed_params = [
        "unienr14_SysActPanel_SettingsKey", "unischedule_SysActPanel_SettingsKey",
    ]
    for param in collapsed_params:
        post_data[f"{param}_collapsed"] = "0"

    form = soup.find('form', {'id': 'form'})
    action_url = urljoin(base_url, form['action']) if form else base_url

    headers = {
        "Accept": "*/*",
        "Accept-Encoding": "gzip, deflate",
        "Accept-Language": "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7",
        "Connection": "keep-alive",
        "Content-Type": "application/x-www-form-urlencoded",
        "Referer": f"{base_url}?bc={post_data.get('bc', '')}&service=bcs&site={post_data.get('site', '')}",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36",
        "X-KL-kfa-Ajax-Request": "Ajax_Request",
        "dojo-ajax-request": "true"
    }

    logs.append("Отправляем POST-запрос с параметрами из success_page2.html...")
    try:
        response = session.post(
            action_url,
            headers=headers,
            data=post_data
        )
        response.raise_for_status()
        
        logs.append(f"POST-запрос выполнен успешно! Статус: {response.status_code}")
        
        with open("logs/success_page4.html", "w", encoding="utf-8") as f:
            f.write(response.text)
            
        return response, logs
    except Exception as e:
        logs.append(f"Ошибка при выполнении POST-запроса: {e}")
        return None, logs

def download_document(base_url, session, number, dirload=None):
    logs = []
    url = base_url
    headers = {
        "Accept-Encoding": "gzip, deflate",
        "Accept-Language": "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7",
        "Cache-Control": "no-cache",
        "Connection": "keep-alive",
        "Content-Type": "application/x-www-form-urlencoded",
        "Pragma": "no-cache",
        "Referer": f"{base_url}?bc={session.cookies.get('bc', '')}&service=bcs&site=509858054516",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36",
        "X-KL-kfa-Ajax-Request": "Ajax_Request",
        "dojo-ajax-request": "true"
    }

    try:
        payload = {
            "parameter": str(number).strip(),
            "provider": "savedRenderer",
            "service": "documentService"
        }
        
        logs.append(f"\nПытаемся скачать документ {number}...")
        response = session.post(url, headers=headers, data=payload, stream=True)
        response.raise_for_status()

        content_disposition = response.headers.get('Content-Disposition', '')
        filename = content_disposition.split('filename=')[1].strip('"\'') if 'filename=' in content_disposition else f"document_{number}.zip"

        # Если указана папка для скачивания, добавляем ее к имени файла
        if dirload:
            # Создаем папку, если она не существует
            os.makedirs(dirload, exist_ok=True)
            filepath = os.path.join(dirload, filename)
        else:
            filepath = filename

        with open(filepath, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)

        logs.append("\n" + "="*50)
        logs.append("Файл успешно скачан!")
        logs.append(f"Имя файла: {filepath}")
        logs.append(f"Размер: {os.path.getsize(filepath)} байт")
        logs.append("="*50)
        
        return filepath, logs

    except requests.exceptions.RequestException as e:
        logs.append(f"Ошибка при запросе: {e}")
        return None, logs
    except Exception as e:
        logs.append(f"Неожиданная ошибка: {e}")
        return None, logs
    
def param(html_content):
    try:
        try:
            with open(html_content, "r", encoding="utf-8") as f:
                content = f.read()
        except (IOError, OSError, TypeError):
            content = html_content
        
        match = re.search(r'parameter=([^&"\']+)', content)
        if match:
            return match.group(1)
        else:
            return None
    except Exception as e:
        return None

def init_parsing(base_url, params, login_headers,company,dirload):
    logs = []
    print(company)
    session, login_logs = login_to_portal(base_url, params, login_headers)
    logs.extend(login_logs)
    
    if session:  
        with open("logs/success_page1.html", "r", encoding="utf-8") as f:
            html_content = f.read()
        
        session, redirect_logs = follow_redirect(session, base_url, html_content, "menu_redirect")
        logs.extend(redirect_logs)
        
        if session:
            export_response, export_logs = post_to_success_page2(base_url,session)
            logs.extend(export_logs)
            
            export_response, export_logs = post_to_success_page3(base_url,session,company)
            logs.extend(export_logs)
            
            parametr = param('logs/success_page4.html')
            logs.append(f"Найден параметр: {parametr}")
            document_number = parametr
                
            downloaded_file, download_logs = download_document(base_url,session, document_number,dirload)
            logs.extend(download_logs)
            
            if not downloaded_file:
                logs.append("\nНе удалось скачать документ. Проверьте параметры запроса.")
    else:
        logs.append("\nНе удалось авторизоваться. Проверьте логин и пароль.")
    return downloaded_file,"\n".join(logs)  # Возвращаем логи в виде строки
