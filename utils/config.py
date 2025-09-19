import os
import logging
from logging.handlers import RotatingFileHandler

def get_api_key(api_name):
    """
    환경 변수에서 API 키를 가져옵니다.
    """
    return os.getenv(api_name)

def setup_logging():
    """
    애플리케이션의 로깅 설정을 초기화합니다.
    - 콘솔에 INFO 레벨 이상 로그 출력
    - 파일에 DEBUG 레벨 이상 로그 저장 (10MB, 5개 파일)
    """
    log_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)

    # 콘솔 핸들러
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(log_formatter)
    console_handler.setLevel(logging.INFO)
    root_logger.addHandler(console_handler)

    # 파일 핸들러
    file_handler = RotatingFileHandler('app.log', maxBytes=10485760, backupCount=5, encoding='utf-8')
    file_handler.setFormatter(log_formatter)
    file_handler.setLevel(logging.DEBUG)
    root_logger.addHandler(file_handler)

    logging.getLogger('werkzeug').setLevel(logging.WARNING)
    