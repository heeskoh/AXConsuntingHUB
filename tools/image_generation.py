import logging
import os
import json
import asyncio
import aiohttp
from openai import OpenAI
from utils.exceptions import APIException
from utils.config import get_api_key

logger = logging.getLogger(__name__)

async def image_generation_tool(prompt, model_choice="Gemini"):
    """
    사용자의 LLM 모델 선택에 따라 적절한 이미지 생성 API를 호출합니다.

    Args:
        prompt (str): 이미지를 생성하기 위한 프롬프트.
        model_choice (str): 사용자가 선택한 LLM 모델 ("Gemini", "OpenAI", "Claude").

    Returns:
        dict: 생성된 이미지 데이터(Base64)가 포함된 응답.
    """
    logger.info(f"'{model_choice}' 모델을 위한 이미지 생성 요청: prompt='{prompt[:50]}'")

    if model_choice == "Gemini":
        return await _generate_with_gemini(prompt)
    elif model_choice in ["OpenAI", "Claude"]:
        return await _generate_with_dalle(prompt)
    else:
        raise APIException("지원하지 않는 모델입니다.", 400)


async def _generate_with_gemini(prompt):
    """
    Imagen-3.0을 사용하여 이미지를 비동기적으로 생성합니다.
    """
    api_key = get_api_key("GEMINI_API_KEY")
    if not api_key:
        raise APIException("Gemini API 키가 설정되지 않았습니다.", 500)

    url = "https://generativelanguage.googleapis.com/v1beta/models/imagen-3.0-generate-002:predict"
    headers = {"Content-Type": "application/json"}
    payload = {
        "instances": {"prompt": prompt},
        "parameters": {"sampleCount": 1}
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(f"{url}?key={api_key}", headers=headers, json=payload) as response:
                response.raise_for_status()
                return await response.json()
    except aiohttp.ClientError as e:
        logger.error(f"Imagen-3.0 API 호출 중 오류 발생: {e}")
        raise APIException(f"이미지 생성에 실패했습니다: {str(e)}", 500)


async def _generate_with_dalle(prompt):
    """
    OpenAI DALL-E 3를 사용하여 이미지를 비동기적으로 생성합니다.
    """
    api_key = get_api_key("OPENAI_API_KEY")
    if not api_key:
        raise APIException("OpenAI API 키가 설정되지 않았습니다.", 500)

    try:
        client = OpenAI(api_key=api_key)
        # run_in_executor를 사용하여 동기식 OpenAI 호출을 비동기적으로 만듦
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            None,
            lambda: client.images.generate(
                model="dall-e-3",
                prompt=prompt,
                size="1024x1024",
                quality="standard",
                n=1,
                response_format="b64_json" # Base64 JSON 형식 요청
            )
        )
        
        # DALL-E 응답을 Imagen-3.0과 유사한 형식으로 변환하여 반환
        if response.data:
            return {
                "predictions": [{
                    "bytesBase64Encoded": response.data[0].b64_json
                }]
            }
        else:
            raise APIException("DALL-E로부터 응답 데이터가 없습니다.", 500)

    except Exception as e:
        logger.error(f"DALL-E API 호출 중 오류 발생: {e}")
        raise APIException(f"이미지 생성에 실패했습니다: {str(e)}", 500)
