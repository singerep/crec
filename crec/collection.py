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

def validate_date(date, param_name):
    if isinstance(date, str):
        try:
            date = datetime.datetime.strptime(date, '%Y-%m-%d')
        except ValueError:
            raise ValueError(f'{param_name} string must in YYYY-mm-dd format')
    elif isinstance(date, datetime.datetime):
        pass
    else:
        raise TypeError(f'{param_name} must be a string in YYYY-mm-dd format or a datetime.datetime object')

    # TODO: make sure the date is in some range
    
    return date.strftime('%Y-%m-%d')

def generate_date_range(start_date: datetime.datetime, end_date: datetime.datetime):
    dates = []
    delta = end_date - start_date

    for i in range(delta.days + 1):
        day = start_date + datetime.timedelta(days=i)
        if day.weekday() not in [5, 6]:
            dates += [datetime.datetime.strftime(day, '%Y-%m-%d')]

    return dates


class Collection:
    def __init__(self, batch_size: int = 200, wait: Union[bool, int] = 300, api_key=None) -> None:
        self.granules : List[Granule] = []

        self.batch_size = batch_size
        self.client = GovInfoAPI(wait=wait)

        self.missing = {'days': [], 'granules': []}

    async def _get_granules_in_batch(self, granules: List[Granule], client: GovInfoAPI):
        batches = [granules[i:i + self.batch_size] for i in range(0, len(granules), self.batch_size)]
        for batch in batches:
            tasks = []
            for g in batch:
                tasks.append(asyncio.create_task(g.async_get(client=client)))
            
            await asyncio.gather(*tasks)

        self.missing['granules'] += [g for g in granules if g.valid is False]
        return [g for g in granules if g.valid is True]

    async def _get_granules_from_ids(self, granule_ids: List[str], client: GovInfoAPI) -> List[Granule]:
        granules = [Granule(granule_id=g_id) for g_id in granule_ids]

        # this should probably not be like this, but it works. otherwise need more functions
        if client._state == ClientState.OPENED:
            granules = await self._get_granules_in_batch(granules=granules, client=client)
        else:
            async with client as client:
                granules = await self._get_granules_in_batch(granules=granules, client=client)

        return granules

    def from_ids(self, granule_ids: List[str] = []):
        granules = asyncio.run(self._get_granules_from_ids(granule_ids=granule_ids, client=self.client))
        self.granules += granules

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

    def from_dates(self, start_date: Union[str, datetime.datetime] = None, end_date: Union[str, datetime.datetime] = None, dates: List[Union[str, datetime.datetime]] = None):
        if start_date is not None and end_date is not None and dates is None:
            start_date = validate_date(date=start_date, param_name='start date')
            end_date = validate_date(date=end_date, param_name='end date')
            dates = generate_date_range(start=start_date, end=end_date)
        elif start_date is None and end_date is None and dates is not None:
            dates = [validate_date(date=d, param_name='each date in dates') for d in dates]

        granules = asyncio.run(self._get_granules_from_dates(dates=dates))
        self.granules += granules

    @property
    def all_raw_text(self) -> List[str]:
        return [g.raw_text for g in self.granules]

    @property
    def all_clean_text(self) -> List[str]:
        return [g.clean_text for g in self.granules]

    def paragraphs(
        self, 
        include_titled_speakers: bool = False,
        include_unknown_speakers: bool = False,
        include_non_speaking: bool = False
    ) -> List[Paragraph]:

        paragraphs = (
            [
                p for p in g.paragraphs_collection.paragraphs if (p.speaker.titled is False or include_titled_speakers) and (p.speaker != UNKNOWN_SPEAKER or include_unknown_speakers) and (p.speaking is True or include_non_speaking)
            ] for g in self.granules
        )

        return list(chain(*paragraphs))

    def paragraph_df(
        self, 
        include_titled_speakers: bool = False,
        include_unknown_speakers: bool = False,
        include_non_speaking: bool = False,
        speaker_attributes: List[str] = ['bioGuideId']
    ) -> pd.DataFrame:
        paragraphs = self.paragraphs(include_titled_speakers=include_titled_speakers, include_unknown_speakers=include_unknown_speakers, include_non_speaking=include_non_speaking)
        paragraph_dicts = []
        for p in paragraphs:
            p_dict = {
                'granule_id': p.granule_id,
                'text': p.text,
                'speaker': p.speaker.first_last
            }
            for attr in speaker_attributes:
                p_dict[attr] = p.speaker.get_attribute(attribute=attr)
            paragraph_dicts.append(p_dict)

        return pd.DataFrame(paragraph_dicts)

    def documents(
        self, 
        include_titled_speakers: bool = False,
        include_unknown_speakers: bool = False,
        include_non_speaking: bool = False
    ) -> List[str]:
        ...