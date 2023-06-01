import httpx
import time
from typing import Union
import asyncio
from collections import defaultdict


class GovInfoAPIError(BaseException):
    pass


class OverRateLimit(BaseException):
    pass


class OverRetryLimit(BaseException):
    pass


class GovInfoAPI(httpx.AsyncClient):
    def __init__(self, wait: Union[bool, int] = 300, retry_limit: Union[bool, int] = 5):
        super().__init__()

        self.api_key = 'VjAEDf7KZQF5WfSHJjuwz7HaEcbAkFdpQovrtf8S'
        self.root_url = 'https://api.govinfo.gov/' # this is unnecessary - should use logic from client for relative urls, params
        self.wait = wait

        self.retry_limit = retry_limit

    @staticmethod
    def validate_response(response: httpx.Response):
        return response.status_code == 200
    
    async def get(self, url):
        request_counter = 0
        while self.retry_limit is False or request_counter < self.retry_limit:
            response = await super().get(url=url)
            request_counter += 1

            if 'OVER_RATE_LIMIT' in response.text:
                if self.wait is True:
                    asyncio.sleep(self.wait)
                else:
                    raise OverRateLimit
            if self.validate_response(response=response):
                break
            
        # return response and some response metadata (could be dataclass)

        return response