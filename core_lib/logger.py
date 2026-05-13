import logging
import os
from logging.handlers import RotatingFileHandler

# Создаем папку для логов в корне проекта
LOGS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "logs")
os.makedirs(LOGS_DIR, exist_ok=True)

def setup_logger(module_name: str) -> logging.Logger:
    """
    Настраивает и возвращает логгер для конкретного модуля.
    Создает отдельный .log файл для каждого переданного имени.
    """
    logger = logging.getLogger(module_name)
    
    # Устанавливаем уровень логирования
    logger.setLevel(logging.INFO)
    
    # Чтобы избежать дублирования хэндлеров при повторных вызовах
    if not logger.handlers:
        # 1. Файловый обработчик (ротация: макс 5МБ, храним 3 последних файла)
        log_file = os.path.join(LOGS_DIR, f"{module_name}.log")
        file_handler = RotatingFileHandler(
            filename=log_file,
            maxBytes=5 * 1024 * 1024,
            backupCount=3,
            encoding='utf-8'
        )
        
        # 2. Консольный обработчик (чтобы видеть логи и в терминале тоже)
        console_handler = logging.StreamHandler()
        
        # 3. Единый формат
        formatter = logging.Formatter(
            fmt='%(asctime)s | %(levelname)-8s | [%(name)s] %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)
        
        logger.addHandler(file_handler)
        logger.addHandler(console_handler)
        
        # Чтобы сообщения не уходили логгеру-родителю и не дублировались
        logger.propagate = False
        
    return logger
