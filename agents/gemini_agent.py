import logging
import json
import markdown
import re
from .base_agent import BaseAgent
from tools.web_search import web_search_tool
from tools.image_generation import image_generation_tool
from utils.api_calls import fetch_with_exponential_backoff
from utils.exceptions import APIException
from utils.config import get_api_key

logger = logging.getLogger(__name__)

class GeminiAgent(BaseAgent):
    """Gemini API를 호출하고 Function Calling을 처리하는 에이전트."""
    def __init__(self):
        self.name = "Gemini 에이전트"
        self.description = "Google Gemini 모델과 다양한 툴을 사용하여 복합적인 작업을 수행합니다."
        self.api_key = get_api_key("GEMINI_API_KEY")
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY is not set.")
        self.api_base_url = "https://generativelanguage.googleapis.com/v1beta/models/"
        self.tools = [
            {
                "functionDeclarations": [
                    {
                        "name": "web_search_tool",
                        "description": "Performs a web search to find current information, news, or data. Use this tool for queries that require real-time or external data.",
                        "parameters": {
                            "type": "object",
                            "properties": { "query": {"type": "string", "description": "The search query."} },
                            "required": ["query"],
                        },
                    },
                    {
                        "name": "image_generation_tool",
                        "description": "Generates an image based on a given prompt. Use this tool for image creation requests.",
                        "parameters": {
                            "type": "object",
                            "properties": { "prompt": {"type": "string", "description": "The image generation prompt."} },
                            "required": ["prompt"],
                        },
                    },
                ],
            }
        ]

    async def process_request(self, prompt, chat_history, use_validation):
        """
        요청을 처리하고 Gemini 모델을 호출합니다.
        """
        logger.info(f"Gemini 에이전트 요청 처리 시작. 프롬프트: {prompt[:50]}...")
        
        try:
            # 1. 초기 프롬프트에 대한 Gemini 응답 받기
            response, agent_info = await self._call_gemini_with_tools(prompt, chat_history)

            response_content = ""
            source_info = []
            
            # 응답 구조를 확인하고 적절한 에이전트 로직을 실행
            if "agent" in agent_info:
                if agent_info["agent"] == "web_search":
                    self.name = "실시간 웹 검색 에이전트"
                    self.description = "Tavily를 통해 실시간 인터넷 정보를 검색하고 결과를 바탕으로 답변을 생성합니다."
                    final_answer = response["candidates"][0]["content"]["parts"][0]["text"]
                    grounding_metadata = response["candidates"][0].get("groundingMetadata")
                    if grounding_metadata and grounding_metadata.get("groundingAttributions"):
                        for attr in grounding_metadata["groundingAttributions"]:
                            if "web" in attr:
                                source_info.append({"type": "Web Search", "info": f"{attr['web'].get('title', '제목 없음')} ({attr['web'].get('uri', 'URL 없음')})"})
                    response_content = markdown.markdown(final_answer)
                elif agent_info["agent"] == "image_generation":
                    self.name = "이미지 생성 에이전트"
                    self.description = "Imagen-3.0을 사용하여 프롬프트에 맞는 이미지를 생성합니다."
                    if response and "predictions" in response and response["predictions"]:
                        base64_image = response["predictions"][0]["bytesBase64Encoded"]
                        response_content = f"<img src='data:image/png;base64,{base64_image}' alt='Generated Image' class='max-w-full h-auto rounded-md shadow-md mt-4'>"
                        source_info.append({"type": "Image Generation", "info": "Imagen-3.0"})
                    else:
                        response_content = "<p class='text-red-500'>이미지 생성에 실패했습니다.</p>"
                else: # 기본 LLM 응답인 경우
                    final_answer = response["candidates"][0]["content"]["parts"][0]["text"]
                    response_content = markdown.markdown(final_answer)
            else:
                # 툴 호출이 실패했거나, agent_info가 없는 경우
                raise APIException(agent_info, 500)

            # 2. 결과 검증 (선택적)
            if use_validation:
                validation_result = await self._call_validation_agent(prompt, response_content, chat_history)
                if validation_result.get("refinement_content"):
                    response_content = validation_result["refinement_content"]
                response_content += f"<div class='mt-4 p-4 border border-blue-200 rounded-md bg-blue-50'><h3 class='font-semibold text-blue-800'>수행 결과 검증 </h3>{validation_result['feedback_html']}</div>"
                source_info.append({"type": "Validation", "info": "최종 검토 에이전트 (Gemini)"})
                self.name = f"{self.name} (검증 완료)"

            return {"response_content": response_content, "source_info": source_info}

        except Exception as e:
            logger.error(f"Gemini 에이전트 처리 실패: {e}")
            raise APIException(f"Gemini 에이전트 처리 중 오류가 발생했습니다: {str(e)}", 500)
    
    async def _call_gemini_with_tools(self, prompt, chat_history):
        """Gemini API를 호출하고 Function Calling을 처리합니다."""
        url = f"{self.api_base_url}gemini-2.5-flash:generateContent?key={self.api_key}"
        
        contents = []
        for chat in chat_history:
            contents.append({"role": "user" if chat["role"] == "user" else "model", "parts": chat["parts"]})
        contents.append({"role": "user", "parts": [{"text": prompt}]})

        payload = {
            "contents": contents,
            "tools": self.tools,
            "toolConfig": { "functionCallingConfig": { "mode": "AUTO" } }
        }

        try:
            response = await fetch_with_exponential_backoff(url, payload)
            
            candidates = response.get("candidates", [])
            if not candidates:
                raise APIException("No candidates found in the response.", 500)

            candidate = candidates[0]
            parts = candidate.get("content", {}).get("parts", [])

            tool_call = None
            for p in parts:
                if isinstance(p, dict) and "functionCall" in p:
                    tool_call = p["functionCall"]
                    break

            if tool_call:
                tool_name = tool_call.get("name")
                tool_args = tool_call.get("args", {})
                logger.info(f"LLM requested tool: {tool_name} with args: {tool_args}")

                if tool_name == "web_search_tool":
                    result = await web_search_tool(**tool_args)
                    followup_contents = contents[:]
                    followup_contents.append({"role": "model", "parts": [{"functionCall": tool_call}]})
                    followup_contents.append({"role": "function", "parts": [{"functionResponse": {"name": "web_search_tool", "response": result}}]})
                    
                    followup_payload = {
                        "contents": followup_contents,
                        "tools": self.tools,
                        "toolConfig": {"functionCallingConfig": {"mode": "AUTO"}}
                    }
                    final_response = await fetch_with_exponential_backoff(url, followup_payload)
                    return final_response, {"agent": "web_search"}

                elif tool_name == "image_generation_tool":
                    result = await image_generation_tool(**tool_args)
                    return result, {"agent": "image_generation"}
                else:
                    raise APIException(f"Unknown tool requested: {tool_name}", 400)
            
            return response, {"agent": "basic_llm"}
            
        except Exception as e:
            logger.error(f"Error in _call_gemini_with_tools: {e}")
            raise APIException(f"API call failed: {str(e)}", 500)

    async def _call_validation_agent(self, original_prompt, generated_content, chat_history):
        """
        최종 검토 에이전트 로직.
        """
        logger.info(f"Validating content for prompt: '{original_prompt[:50]}'")

        validation_prompt = f"""
        아래는 원본 질문과 생성된 답변입니다.

        ### 원본 질문
        {original_prompt}

        ### 생성된 답변
        {generated_content}

        다음 5가지 기준에 따라 100점 만점으로 점수를 매기고, 각 항목에 대한 구체적인 피드백을 제공해주세요.
        점수는 오직 숫자만 반환해야 합니다.

        1. **정확성**: 답변의 내용이 사실에 부합하는가?
        2. **관련성**: 답변이 원본 질문의 의도와 목적에 얼마나 부합하는가?
        3. **완전성**: 질문의 모든 측면을 충분히 다루고 있는가?
        4. **명확성 및 간결성**: 내용이 이해하기 쉽고 불필요한 부분이 없는가?
        5. **논리적 일관성**: 내용의 흐름이 자연스럽고 논리적인가?

        응답은 반드시 아래와 같은 JSON 형식으로 반환해야 합니다.
        {{
            "scores": {{
                "정확성": 0,
                "관련성": 0,
                "완전성": 0,
                "명확성_간결성": 0,
                "논리적_일관성": 0
            }},
            "feedback": {{
                "정확성": "피드백 내용",
                "관련성": "피드백 내용",
                "완전성": "피드백 내용",
                "명확성_간결성": "피드백 내용",
                "논리적_일관성": "피드백 내용"
            }}
        }}
        """
        
        url = f"{self.api_base_url}gemini-2.5-flash:generateContent?key={self.api_key}"
        headers = {"Content-Type": "application/json"}
        payload = {
            "contents": [{"role": "user", "parts": [{"text": validation_prompt}]}],
            "generationConfig": {"responseMimeType": "application/json"}
        }
        
        try:
            response = await fetch_with_exponential_backoff(url, payload)
            validation_data = json.loads(response["candidates"][0]["content"]["parts"][0]["text"])
        except Exception as e:
            logger.error(f"Validation API call failed: {e}")
            return {
                "scores": {"정확성": 0, "관련성": 0, "완전성": 0, "명확성_간결성": 0, "논리적_일관성": 0},
                "feedback": {"error": "검증 시스템 오류가 발생했습니다."},
                "feedback_html": f"<p class='text-red-600 mt-2'>검증 시스템 오류가 발생했습니다: {str(e)}</p>",
                "reconsideration_prompt": None,
                "refinement_content": None
            }

        scores = validation_data.get("scores", {})
        feedback = validation_data.get("feedback", {})
        
        total_score = sum(scores.values())
        average_score = total_score / len(scores) if len(scores) > 0 else 0

        feedback_html = "<div>"
        feedback_html += f"<p class='font-semibold'>평가 점수 (100점 만점):</p><ul class='list-disc list-inside'>"
        for c, score in scores.items():
            feedback_html += f"<li>{c}: {score}점</li>"
        feedback_html += f"</ul><p class='font-bold mt-2'>전체 평균 점수: {average_score:.2f}점</p>"
        
        reconsideration_prompt = None
        if average_score < 60:
            feedback_html += "<p class='text-red-600 mt-2'>평균 점수가 60점 이하이므로 프롬프트 재설계를 통한 재수행을 제안합니다.</p>"
            reconsideration_prompt = f"원본 프롬프트: '{original_prompt}'에 대한 결과의 평균 점수가 {average_score:.2f}점이므로, 프롬프트를 재설계하여 더 나은 답변을 생성해주세요."
            
            logger.info("Performing refinement...")
            refinement_prompt = f"""
            다음은 사용자의 원본 질문과 생성된 답변, 그리고 그에 대한 피드백입니다.
            피드백을 참고하여 답변을 개선하고, 더 정확하고 완전한 답변을 다시 작성해주세요.

            ### 원본 질문
            {original_prompt}

            ### 기존 답변
            {generated_content}
            
            ### 피드백
            {json.dumps(feedback, ensure_ascii=False, indent=2)}

            개선된 답변만 작성해주세요.
            """
            
            try:
                refinement_response = await fetch_with_exponential_backoff(url, {"contents": [{"role": "user", "parts": [{"text": refinement_prompt}]}]})
                refinement_content = refinement_response["candidates"][0]["content"]["parts"][0]["text"]
                return {
                    "scores": scores,
                    "average_score": average_score,
                    "feedback_html": feedback_html,
                    "reconsideration_prompt": reconsideration_prompt,
                    "refinement_content": markdown.markdown(refinement_content)
                }
            except Exception as e:
                logger.error(f"Refinement failed: {e}")
                feedback_html += f"<p class='text-red-600 mt-2'>답변 개선에 실패했습니다: {str(e)}</p>"
        else:
            feedback_html += "<p class='text-green-600 mt-2'>전반적으로 좋은 결과입니다.</p>"

        feedback_html += "</div>"

        return {
            "scores": scores,
            "average_score": average_score,
            "feedback_html": feedback_html,
            "reconsideration_prompt": reconsideration_prompt,
            "refinement_content": None
        }
