import httpx
from typing import Union, Tuple
import asyncio

from crec.logger import Logger


class RateLimitError(BaseException):
    """
    Thrown if the rate limit is exceeded and the Record object's ``wait``
    parameter is ``False``.
    """
    pass


class APIKeyError(BaseException):
    """
    Thrown if an API key is not provided or is invalid.
    """
    pass


class GovInfoClient(httpx.AsyncClient):
    """
    Handles requesting data from the GovInfo API. Inherits from 
    :class:`httpx.AsyncClient` so that requests can be made asynchronously.

    Parameters
    ----------
    wait : Union[bool, int]
        If ``wait`` is an ``int``, then exceeding the GovInfo rate limit will cause the 
        program to wait for ``wait`` seconds. Otherwise, ``wait`` should be ``False``, 
        and exceeding the rate limit will throw an uncaught exception.
    retry_limit : Union[bool, int]
        If ``retry_limit`` is an ``int``, then the program will attempt to request
        URLs up to ``retry_limit`` times before moving on. Otherwise, ``retry_limit``
        should be ``False``, and URLs will only be tried once.
    logger : :class:`.Logger`
        An object that handles outputting logs.
    api_key : str = None
        API key from GovInfo. Can be obtained by visiting 
        https://www.govinfo.gov/api-signup
    """
    def __init__(self, rate_limit_wait: Union[bool, int], retry_limit: Union[bool, int], logger: Logger, api_key: str):
        super().__init__(base_url='https://api.govinfo.gov/')

        self.api_key = api_key
        self.rate_limit_wait = rate_limit_wait
        self.retry_limit = retry_limit
        self.logger = logger
    
    async def get(self, url: str, params: dict = {}) -> Tuple[bool, Union[httpx.Response, None]]:
        """
        Extends :meth:`httpx.AsyncClient.get()`. Controls waiting and retrying URLs, 
        and handles GovInfo-specific query parameters like the ``api_key``. 
        Returns a tuple consisting of a boolean indicating whether or not the request 
        was successful and the response itself (the response could be ``None`` 
        if the request fails ``self.retry_limit`` times).
        """
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
                self.logger.log(message=f'httpx error; trying again')
                await asyncio.sleep(2)
                continue

            if response.status_code == 401:
                raise APIKeyError('api_key is invalid or not provided')

            if 'OVER_RATE_LIMIT' in response.text:
                if type(self.rate_limit_wait) == int:
                    self.logger.log(message=f'exceeded rate limit; pausing for {self.rate_limit_wait} seconds now')
                    await asyncio.sleep(self.rate_limit_wait)
                    continue
                else:
                    raise RateLimitError('you have exceeded the rate limit; halting now')

            if response.status_code != 200:
                self.logger.log(message=f'api error; trying again')
                await asyncio.sleep(2)
                continue

            response_validity = True
            break

        return response_validity, response