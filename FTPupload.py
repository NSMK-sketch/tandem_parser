import ftplib
import socket
import logging

def upload(file_path, file_names, HOSTNAME, USERNAME, PASSWORD, timeout=30):
    """
    Загружает файл на FTP сервер с обработкой ошибок
    
    :param file_path: Локальный путь к файлу
    :param file_names: Имя файла на сервере
    :param HOSTNAME: Адрес FTP сервера
    :param USERNAME: Имя пользователя FTP
    :param PASSWORD: Пароль FTP
    :param timeout: Таймаут соединения в секундах
    :return: True если успешно, False в случае ошибки
    """
    ftp = None
    try:
        # Устанавливаем таймаут и создаем соединение
        ftp = ftplib.FTP(timeout=timeout)
        ftp.connect(HOSTNAME)
        ftp.login(USERNAME, PASSWORD)
        
        # Устанавливаем пассивный режим (часто помогает с проблемами соединения)
        ftp.set_pasv(True)
        
        # Загружаем файл
        with open(file_path, 'rb') as upload_file:
            ftp.storbinary(f'STOR {file_names}', upload_file)
            
        return True
        
    except socket.timeout:
        logging.error(f"Timeout при подключении к FTP серверу {HOSTNAME}")
    except ftplib.all_errors as e:
        logging.error(f"FTP ошибка: {e}")
    except IOError as e:
        logging.error(f"Ошибка чтения файла {file_path}: {e}")
    except Exception as e:
        logging.error(f"Неожиданная ошибка: {e}")
    finally:
        # Всегда закрываем соединение
        if ftp:
            try:
                ftp.quit()
            except:
                # Игнорируем ошибки при закрытии
                pass
                
    return False