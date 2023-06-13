import datetime
from typing import Union, List, Dict
from xml.etree import ElementTree as et
import math
import asyncio
from httpx._client import ClientState
import pandas as pd
from itertools import chain

from crec import GovInfoAPI
from crec.granule import Granule
from crec.package import Package
from crec.paragraph import Paragraph
from crec.speaker import UNKNOWN_SPEAKER


class Downloader:
    def __init__(self, batch_size: int = 200, wait: Union[bool, int] = 300, api_key=None) -> None:
        self.batch_size = batch_size
        self.client = GovInfoAPI(wait=wait)

        self.missing = {'days': [], 'granules': []}

    async def _get_granules_in_batch(self, granules: List[Granule], client: GovInfoAPI):
        batches = [granules[i:i + self.batch_size] for i in range(0, len(granules), self.batch_size)]
        for i, batch in enumerate(batches):
            print(f'getting batch {i + 1} out of {len(batches)}')
            tasks = []
            for g in batch:
                tasks.append(asyncio.create_task(g.async_get(client=client)))
            
            await asyncio.gather(*tasks)

        self.missing['granules'] += [g for g in granules if g.valid is False]
        # return [g for g in granules if g.valid is True]
        return granules

    async def _get_granules_from_ids(self, granule_ids: List[str], client: GovInfoAPI) -> List[Granule]:
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

    async def _get_granule_ids_from_dates(self, dates: List[str], client: GovInfoAPI) -> List[str]:
        granule_ids = []
        for d in dates:
            p = Package(date=d, client=client)
            got_all_ids, p_granule_ids = await p.get_granule_ids(client=client)
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