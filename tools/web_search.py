import logging
import json
import os
import aiohttp
import asyncio

from utils.exceptions import APIException
from utils.config import get_api_key

logger = logging.getLogger(__name__)

async def web_search_tool(query):
    """
    Tavily API를 사용하여 비동기 웹 검색을 수행하고, 결과를 JSON 형식으로 반환합니다.
    
    Args:
        query (str): 검색할 질의어.
    
    Returns:
        dict: 검색 결과를 포함하는 딕셔너리.
    """
    tavily_api_key = get_api_key("TAVILY_API_KEY")
    if not tavily_api_key:
        logger.error("TAVILY_API_KEY 환경 변수가 설정되지 않았습니다.")
        raise APIException("Tavily API 키가 설정되지 않았습니다.", 500)

    url = "https://api.tavily.com/search"
    headers = {"Content-Type": "application/json"}
    payload = {
        "api_key": tavily_api_key,
        "query": query,
        "search_depth": "basic",
        "include_answer": True,
        "include_raw_content": False,
        "max_results": 5
    }

    logger.info(f"Tavily API 호출 시작: query='{query}'")

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=headers, json=payload) as response:
                response.raise_for_status()
                search_results = await response.json()
                logger.info("Tavily API 호출 성공.")
                return search_results
    except aiohttp.ClientError as e:
        logger.error(f"Tavily API 호출 중 클라이언트 오류 발생: {e}")
        raise APIException(f"웹 검색 API 호출에 실패했습니다: {str(e)}", 500)
    except Exception as e:
        logger.error(f"Tavily API 호출 중 알 수 없는 오류 발생: {e}")
        raise APIException(f"웹 검색 중 오류가 발생했습니다: {str(e)}", 500)
