import abc

class BaseAgent(abc.ABC):
    """
    모든 에이전트 클래스가 상속받아야 하는 추상 기본 클래스입니다.
    
    이 클래스는 모든 에이전트가 가져야 할 필수 속성과 메서드를 정의하여,
    에이전트 시스템의 구조를 통일하고 확장성을 보장합니다.
    """
    
    def __init__(self):
        self.name = "기본 에이전트"
        self.description = "기본적인 LLM 응답을 생성하는 에이전트입니다."
    
    @abc.abstractmethod
    async def process_request(self, prompt, chat_history, use_validation):
        """
        사용자의 요청을 처리하고 응답을 생성하는 추상 메서드입니다.
        
        하위 클래스에서 반드시 이 메서드를 구현해야 합니다.
        
        Args:
            prompt (str): 사용자의 현재 프롬프트.
            chat_history (list): 이전 대화 기록.
            use_validation (bool): 결과 검증 여부.
            
        Returns:
            dict: 응답 콘텐츠와 소스 정보를 포함하는 딕셔너리.
        """
        raise NotImplementedError("하위 클래스는 process_request() 메서드를 반드시 구현해야 합니다.")
