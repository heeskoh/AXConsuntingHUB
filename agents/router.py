# agents/router.py
import logging
import asyncio
from .gemini_agent import GeminiAgent
from .openai_agent import OpenAIAgent
from .claude_agent import ClaudeAgent
from utils.exceptions import APIException

logger = logging.getLogger(__name__)

class AgentRouter:
    """사용자 요청을 분석하여 적절한 에이전트로 라우팅합니다."""
    def __init__(self):
        self.agents = {
            "Gemini": GeminiAgent(),
            "OpenAI": OpenAIAgent(),
            "Claude": ClaudeAgent()
        }
        logger.info("AgentRouter initialized successfully.")

    async def handle_request(self, prompt, chat_history, model_choice, use_validation):
        """
        요청을 처리하고, 선택된 모델에 따라 적절한 에이전트를 호출합니다.
        """
        if model_choice not in self.agents:
            raise APIException(f"지원되지 않는 모델 선택: {model_choice}", 400)
        
        agent = self.agents[model_choice]
        logger.info(f"Routing request to '{agent.name}' agent.")
        
        response_data = await agent.process_request(prompt, chat_history, use_validation)
        
        return agent.name, agent.description, response_data