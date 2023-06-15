import httpx
import time
from typing import Union
import asyncio
from collections import defaultdict
from enum import Enum

from crec.logger import Logger


class RateLimitError(BaseException):
    pass


class ResponseMeta:
    def __init__(self) -> None:
        pass


class GovInfoClient(httpx.AsyncClient):
    def __init__(self, wait: Union[bool, int], retry_limit: Union[bool, int], logger: Logger):
        super().__init__(base_url='https://api.govinfo.gov/')

        self.api_key = 'VjAEDf7KZQF5WfSHJjuwz7HaEcbAkFdpQovrtf8S'
        self.root_url = 'https://api.govinfo.gov/' # this is unnecessary - should use logic from client for relative urls, params
        self.wait = wait
        self.retry_limit = retry_limit
        self.logger = logger
    
    async def get(self, url: str, params: dict = {}):
        params.update({'api_key': self.api_key})
        request_counter = 0
        response_validity = False
        while self.retry_limit is False or request_counter < self.retry_limit:
            request_counter += 1
            try:
                response = await super().get(url=url, params=params)
            except (httpx.ConnectTimeout, httpx.ConnectError, httpx.ReadTimeout, httpx.PoolTimeout):
                response = None

            if response is None:
                self.logger.log(message=f'httpx error')
                await asyncio.sleep(2)
                continue

            if 'OVER_RATE_LIMIT' in response.text:
                if isinstance(self.wait, int):
                    self.logger.log(message=f'exceeded rate limit; pausing for {self.wait} seconds now')
                    await asyncio.sleep(self.wait)
                else:
                    raise RateLimitError

            if response.status_code != 200:
                self.logger.log(message=f'api error')
                await asyncio.sleep(2)
                continue

            response_validity = True
            break

        return response_validity, response