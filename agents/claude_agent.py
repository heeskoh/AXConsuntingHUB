import logging
import markdown
import asyncio
from openai import OpenAI
import anthropic
from .base_agent import BaseAgent
from utils.exceptions import APIException
from utils.config import get_api_key

logger = logging.getLogger(__name__)

class ClaudeAgent(BaseAgent):
    """Anthropic Claude API를 호출하여 응답을 생성하는 에이전트."""
    def __init__(self):
        self.name = "Claude 에이전트"
        self.description = "Anthropic Claude 모델에 프롬프트를 전달하여 응답을 생성합니다."
        self.api_key = get_api_key("ANTHROPIC_API_KEY")
        if not self.api_key:
            raise ValueError("ANTHROPIC_API_KEY is not set.")
        self.client = anthropic.Anthropic(api_key=self.api_key)

    async def process_request(self, prompt, chat_history, use_validation):
        """
        요청을 처리하고 Claude 모델을 호출합니다.
        """
        logger.info(f"Claude 에이전트 요청 처리 시작. 프롬프트: {prompt[:50]}...")
        try:
            # Claude API 호출은 동기식이므로, 비동기 처리를 위해 run_in_executor 사용
            response = await asyncio.to_thread(self._call_claude_api, prompt, chat_history)

            # Claude 응답(Message 객체)에서 텍스트 추출
            text = "".join([p.text for p in response.content if getattr(p, "text", None)])
            
            response_content = markdown.markdown(text)
            source_info = []
            
            # 선택적: 수행 결과 검증
            if use_validation:
                validation_result = await self._call_validation_agent(prompt, response_content, chat_history)
                if validation_result.get("refinement_content"):
                    response_content = validation_result["refinement_content"]
                response_content += f"<div class='mt-4 p-4 border border-blue-200 rounded-md bg-blue-50'><h3 class='font-semibold text-blue-800'>수행 결과 검증 </h3>{validation_result['feedback_html']}</div>"
                source_info.append({"type": "Validation", "info": "최종 검토 에이전트 (Gemini)"})
                self.name = f"{self.name} (검증 완료)"

            return {"response_content": response_content, "source_info": source_info}

        except Exception as e:
            logger.error(f"Claude API 호출 실패: {e}")
            raise APIException(f"Claude API 호출에 실패했습니다: {e}", 500)

    def _call_claude_api(self, prompt, chat_history):
        """
        Anthropic Claude Messages 간단 래퍼
        """
        # chat_history를 Claude messages 형식에 맞게 변환
        messages = [{"role": "user" if chat["role"] == "user" else "assistant", "content": chat["parts"][0]["text"]} for chat in chat_history]
        messages.append({"role": "user", "content": prompt})
         
        msg = self.client.messages.create(
            model="claude-3-5-sonnet-latest",
            max_tokens=1024, 
            messages=messages
        )
         
        return msg

    async def _call_validation_agent(self, original_prompt, generated_content, chat_history):
        # GeminiAgent의 검증 로직을 복사하거나, 별도의 유틸리티 함수로 분리하여 사용
        # 여기서는 설명을 위해 임시로 복사함. 실제로는 코드 재사용을 권장.
        from agents.gemini_agent import GeminiAgent
        gemini_agent = GeminiAgent()
        validation_result = await gemini_agent._call_validation_agent(original_prompt, generated_content, chat_history)
        return validation_result
