import datetime
from typing import Union, List, Dict, Set
from xml.etree import ElementTree as et
import math
import asyncio
from httpx._client import ClientState
import pandas as pd
from itertools import chain
import logging

from crec.api import GovInfoClient
from crec.granule import Granule, get_granule_ids
from crec.logger import Logger
from crec.constants import GRANULE_CLASSES


class Downloader:
    """
    Supervises and controls requests made through a :class:`.GovInfoClient` object.

    Parameters
    -----------
    granule_class_filter : List[str] = None
        If provided, only granules with a class listed in ``granule_class_filter``
        will be retrieved. If ``granule_class_filter`` is ``None``, all granules
        are included. The class options are:

        * ``HOUSE``
        * ``SENATE``
        * ``EXTENSIONS``
        * ``DAILYDIGEST``
    parse : bool = True
        A boolean that indicates whether or not the text of granules should be parsed.
    write : Union[bool, str] = False
        If ``write`` is ``False``, then granule text (htm files) and metadata (xml files)
        will not be written to disk. Otherwise, ``write`` should be a path where those
        files should be written to.
    batch_size: int = 200
        The number of granules to asynchronously attempt to get at the same time.
        Too high of a number will result in frequent rate limit issues.
    batch_wait : Union[int, bool] = 2
        If ``batch_wait`` is an ``int``, then after requesting granule data in each
        batch of size ``batch_size``, the program will halt for ``batch_wait`` seconds.
        Otherwise, ``batch_size`` should be ``False``, and the program will not pause
        after each batch.
    rate_limit_wait : Union[int, bool] = 300
        If ``rate_limit_wait`` is an ``int``, then exceeding the GovInfo rate limit 
        will cause the program to halt for ``rate_limit_wait`` seconds. Otherwise, 
        ``rate_limit_wait`` should be ``False``, and exceeding the rate limit will 
        throw an uncaught exception.
    retry_limit : Union[bool, int] = 5
        If ``retry_limit`` is an ``int``, then the program will attempt to request
        URLs up to ``retry_limit`` times before moving on. Otherwise, ``retry_limit``
        should be ``False``, and URLs will only be tried once.
    api_key : str = None
        API key from GovInfo. Can be obtained by visiting 
        https://www.govinfo.gov/api-signup
    logger : :class:`.Logger`
        An object that handles outputting logs.

    Attributes
    -----------
    client : :class:`.GovInfoClient`
        A :class:`.GovInfoClient` object that is used to make requests.
    incomplete_days : Set[str]
        A set of date strings that did *not* have all of their associated granule
        identifiers retrieved.
    incomplete_granules : Set[str]
        A set of granule identifiers that did *not* have their data retrieved, 
        parsed, or written to disk (depending on requested behavior).
    """
    def __init__(self, granule_class_filter: List[str], parse: bool, write: Union[bool, str], batch_size: int, batch_wait: Union[bool, int], rate_limit_wait: Union[bool, int], retry_limit: Union[bool, int], api_key: str, logger: Logger) -> None:
        if parse is False and write is False:
            raise Exception("You are neither parsing nor writing text and metadata; you must do at least one.")
        self.granule_class_filters = granule_class_filter
        self.valid_classes = [c for c in GRANULE_CLASSES if c in granule_class_filter] if granule_class_filter is not None else GRANULE_CLASSES
        self.invalid_classes = [c for c in GRANULE_CLASSES if c not in granule_class_filter] if granule_class_filter is not None else []
        self.parse = parse
        self.write = write
        self.batch_size = batch_size
        self.batch_wait = batch_wait
        self.client = GovInfoClient(rate_limit_wait=rate_limit_wait, retry_limit=retry_limit, logger=logger, api_key=api_key)
        self.logger = logger

        self.incomplete_days : Set[str] = set()
        self.incomplete_granules : Set[str] = set()

    async def get_granules_in_batch(self, granules: List[Granule], client: GovInfoClient) -> List[Granule]:
        """
        Takes as an input a list of :class:`.Granule` objects and a 
        :class:`GovInfoClient`. Splits the granules into batches of 
        size ``self.batch_size``. Within each batch, a :class:`asyncio.Task` is created
        which consists of getting the granule's data, and potentially parsing and
        writing it (depending on ``self.parse`` and ``self.write``). 
        Should only be called internally.
        """
        self.incomplete_granules = set([g.attributes['granuleId'] for g in granules])

        batches = [granules[i:i + self.batch_size] for i in range(0, len(granules), self.batch_size)]
        for i, batch in enumerate(batches):
            self.logger.log(message=f'getting granules in batch {i + 1} of {len(batches)}')
            tasks = []
            for g in batch:
                tasks.append(asyncio.create_task(g.async_get(client=client, parse=self.parse, write=self.write)))
            
            await asyncio.gather(*tasks)

            if type(self.batch_wait) == int:
                await asyncio.sleep(self.batch_wait)
        
        for g in granules:
            if g.complete:
                self.incomplete_granules.remove(g.attributes['granuleId'])

        if self.parse is True and isinstance(self.write, str):
            action_string = 'got, parsed, and wrote'
        elif self.parse is False and isinstance(self.write, str):
            action_string = 'got and wrote'
        elif self.parse is True and self.write is False:
            action_string = 'got and parsed'
        else:
            action_string = 'got'

        self.logger.log(f'successfully {action_string} {len(granules) - len(self.incomplete_granules)} of {len(granules)} granules; there were {len(self.incomplete_granules)} failures')
        return granules

    async def get_granules_from_ids(self, granule_ids: List[str], client: GovInfoClient) -> List[Granule]:
        """
        Takes as an input a list of granule identifiers and a 
        :class:`.GovInfoClient`. Initializes a :class:`.Granule` object for each
        identifier. Hands the initialized granules over to 
        :meth:`.Downloader.get_granules_in_batch()`. Should only be called internally.
        """
        granules = [Granule(granule_id=g_id) for g_id in granule_ids]

        # this should probably not be like this, but it works. otherwise need more functions
        if client._state == ClientState.OPENED:
            granules = await self.get_granules_in_batch(granules=granules, client=client)
        else:
            async with client as client:
                granules = await self.get_granules_in_batch(granules=granules, client=client)

        return granules

    def get_from_ids(self, granule_ids: List[str] = []) -> List[Granule]:
        """
        Takes as an input a list of granule identifiers and executes the 
        :meth:`.Downloader.get_granules_from_ids()` coroutine.
        """
        if self.valid_classes != GRANULE_CLASSES:
            self.logger.log("Since you've passed in your own granule ids, granule class filters are being ignored", level='warning')
        granules = asyncio.run(self.get_granules_from_ids(granule_ids=granule_ids, client=self.client))
        return granules

    async def get_granule_ids_from_dates(self, dates: List[str], client: GovInfoClient) -> List[str]:
        """
        Takes as an input a list of date strings and a :class:`GovInfoClient`. 
        Then, creates a :class:`.Package` object for each date. Then, calls
        :meth:`.Package.get_granule_ids()` to get the granule identifiers associated
        with that given day. Also keeps track of whether all granule identifiers
        from a particular day were retrieved; if not, that day will be listed under
        ``self.incomplete_days``.
        """
        self.logger.log(f'getting ids for granules with the following classes: {self.valid_classes}; skipping granules with the following classes: {self.invalid_classes}')
        self.incomplete_days = set(dates)
        granule_ids = []
        for d in dates:
            got_all_ids, date_granule_ids = await get_granule_ids(date=d, client=client, granule_class_filters=self.valid_classes, logger=self.logger)
            if got_all_ids:
                granule_ids += date_granule_ids
                self.incomplete_days.remove(d)

        return granule_ids

    async def get_granules_from_dates(self, dates: List[str]) -> List[Granule]:
        """
        Takes as an input a list of date strings. Gets the granule identifiers
        associated with those dates using 
        :meth:`.Downloader.get_granule_ids_from_dates`, and passes those along to
        :meth:`.Downloader.get_granules_from_ids`.
        """
        async with self.client as client:
            granule_ids = await self.get_granule_ids_from_dates(dates=dates, client=client)
            granules = await self.get_granules_from_ids(granule_ids=granule_ids, client=client)

        return granules

    def get_from_dates(self, dates: List[str] = []) -> List[Granule]:
        """
        Takes as an input a list of date strings and executes the 
        :meth:`.Downloader.get_granules_from_dates()` coroutine.
        """
        granules = asyncio.run(self.get_granules_from_dates(dates=dates))
        return granules