import httpx
import time
from typing import Union
import asyncio
from collections import defaultdict
from enum import Enum


class RateLimitError(BaseException):
    pass


class ResponseMeta:
    def __init__(self) -> None:
        pass


class GovInfoAPI(httpx.AsyncClient):
    def __init__(self, wait: Union[bool, int] = 300, retry_limit: Union[bool, int] = 5):
        super().__init__(base_url='https://api.govinfo.gov/')

        self.api_key = 'VjAEDf7KZQF5WfSHJjuwz7HaEcbAkFdpQovrtf8S'
        self.root_url = 'https://api.govinfo.gov/' # this is unnecessary - should use logic from client for relative urls, params
        self.wait = wait
        self.retry_limit = retry_limit
    
    async def get(self, url: str, params: dict = {}):
        params.update({'api_key': self.api_key})
        request_counter = 0
        response_validity = False
        while self.retry_limit is False or request_counter < self.retry_limit:
            request_counter += 1
            try:
                response = await super().get(url=url, params=params)
            except (httpx.ConnectTimeout, httpx.ReadTimeout):
                response = None

            if response is None:
                await asyncio.sleep(2)
                continue

            if 'OVER_RATE_LIMIT' in response.text:
                if isinstance(self.wait, int):
                    await asyncio.sleep(self.wait)
                else:
                    raise RateLimitError

            if response.status_code != 200:
                await asyncio.sleep(2)
                continue

            response_validity = True
            break

        return response_validity, response