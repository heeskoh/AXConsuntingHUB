import asyncio
import aiohttp
import logging
from utils.exceptions import APIException

logger = logging.getLogger(__name__)

async def fetch_with_exponential_backoff(url, payload, retries=5, delay=1.0):
    """
    지수 백오프를 사용하여 비동기 HTTP POST 요청을 수행합니다.

    API 호출이 실패할 경우, 지정된 횟수만큼 재시도하며 지수적으로 대기 시간을 늘립니다.

    Args:
        url (str): API 엔드포인트 URL.
        payload (dict): 요청 바디에 포함될 데이터.
        retries (int): 재시도 최대 횟수.
        delay (float): 초기 대기 시간 (초).

    Returns:
        dict: 성공적인 API 응답의 JSON 데이터.

    Raises:
        APIException: 재시도 횟수를 모두 소진하거나 치명적인 오류가 발생한 경우.
    """
    safe_url = url.split("?")[0] # API 키 등 민감 정보를 제외
    
    for i in range(retries):
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=payload) as response:
                    # HTTP 상태 코드가 4xx 또는 5xx일 경우 예외 발생
                    response.raise_for_status()
                    return await response.json()
        
        except aiohttp.ClientResponseError as e:
            if 400 <= e.status < 500:
                # 4xx 클라이언트 오류는 재시도하지 않고 바로 예외 발생
                logger.error(f"Client error ({e.status}) from {safe_url}. Not retrying.")
                raise APIException(f"API 요청에 실패했습니다: {e.message}", e.status)
            else:
                # 5xx 서버 오류는 재시도
                logger.warning(f"Server error ({e.status}) from {safe_url}. Retrying ({i+1}/{retries}).")
        
        except (aiohttp.ClientError, asyncio.TimeoutError) as e:
            logger.warning(f"Network error or timeout on {safe_url}. Retrying ({i+1}/{retries}). Error: {e}")
        
        if i < retries - 1:
            wait_time = delay * (2 ** i)
            logger.info(f"Waiting for {wait_time:.2f} seconds before next retry.")
            await asyncio.sleep(wait_time)
    
    # 모든 재시도 실패
    logger.error(f"Failed to fetch from {safe_url} after {retries} attempts.")
    raise APIException("API 호출에 지속적으로 실패했습니다. 잠시 후 다시 시도해주세요.", 500)
