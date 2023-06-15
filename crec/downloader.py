import datetime
from typing import Union, List, Dict
from xml.etree import ElementTree as et
import math
import asyncio
from httpx._client import ClientState
import pandas as pd
from itertools import chain
import logging

from crec import GovInfoClient
from crec.granule import Granule
from crec.package import Package
from crec.logger import Logger


class Downloader:
    def __init__(self, granule_class_filter: List[str], parse: bool, write: Union[bool, str], batch_size: int, wait: Union[bool, int], retry_limit: Union[bool, int], api_key: str, logger: Logger) -> None:
        self.granule_class_filters = granule_class_filter
        self.parse = parse
        self.write = write
        self.batch_size = batch_size
        self.client = GovInfoClient(wait=wait, retry_limit=retry_limit, logger=logger)
        self.logger = logger

        self.missing = {'days': [], 'granules': []}

    async def _get_granules_in_batch(self, granules: List[Granule], client: GovInfoClient):
        batches = [granules[i:i + self.batch_size] for i in range(0, len(granules), self.batch_size)]
        for i, batch in enumerate(batches):
            self.logger.log(message=f'getting granules in batch {i + 1} of {len(batches)}')
            tasks = []
            for g in batch:
                tasks.append(asyncio.create_task(g.async_get(client=client)))
            
            await asyncio.gather(*tasks)

        successes = [g for g in granules if g.valid is True]
        failures = [g for g in granules if g.valid is False]
        self.missing['granules'] += failures
        self.logger.log(f'successfully got {len(successes)} of {len(granules)} granules; there were {len(failures)} failures')
        return granules

    async def _get_granules_from_ids(self, granule_ids: List[str], client: GovInfoClient) -> List[Granule]:
        granules = [Granule(granule_id=g_id) for g_id in granule_ids]

        # this should probably not be like this, but it works. otherwise need more functions
        if client._state == ClientState.OPENED:
            granules = await self._get_granules_in_batch(granules=granules, client=client)
        else:
            async with client as client:
                granules = await self._get_granules_in_batch(granules=granules, client=client)

        return granules

    def get_from_ids(self, granule_ids: List[str] = []):
        granules = asyncio.run(self._get_granules_from_ids(granule_ids=granule_ids, client=self.client))
        return granules

    async def _get_granule_ids_from_dates(self, dates: List[str], client: GovInfoClient) -> List[str]:
        granule_ids = []
        for d in dates:
            p = Package(date=d, client=client, logger=self.logger)
            got_all_ids, p_granule_ids = await p.get_granule_ids(client=client, granule_class_filters=self.granule_class_filters)
            if got_all_ids:
                granule_ids += p_granule_ids
            else:
                self.missing['days'].append(d)

        return granule_ids

    async def _get_granules_from_dates(self, dates: List[str]) -> List[Granule]:
        async with self.client as client:
            granule_ids = await self._get_granule_ids_from_dates(dates=dates, client=client)
            granules = await self._get_granules_from_ids(granule_ids=granule_ids, client=client)

        return granules

    def get_from_dates(self, dates: List[str] = []):
        granules = asyncio.run(self._get_granules_from_dates(dates=dates))
        return granules

    # @property
    # def all_raw_text(self) -> List[str]:
    #     return [g.raw_text for g in self.granules]

    # @property
    # def all_clean_text(self) -> List[str]:
    #     return [g.clean_text for g in self.granules]

    # @property
    # def paragraphs(self):
    #     return list(chain(*(g.paragraphs for g in self.granules)))

    # @property
    # def passages(self):
    #     return list(chain(*(g.passages for g in self.granules)))