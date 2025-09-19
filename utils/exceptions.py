class APIException(Exception):
    """
    API 요청 처리 중 발생하는 사용자 정의 예외 클래스.
    
    이 예외는 특정 HTTP 상태 코드와 사용자에게 보여줄 메시지를 포함합니다.
    """
    def __init__(self, message, status_code=500):
        self.message = message
        self.status_code = status_code
        super().__init__(self.message)
