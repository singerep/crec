import requests # TODO: switch to httpx
import json
import datetime
from typing import Union, List, Dict
import zipfile
import io
import os
from xml.etree import ElementTree as et
import math
import time
import httpx
import asyncio
import queue

from crec import GovInfoAPI, OverRateLimit, OverRetryLimit, GovInfoAPIError
from crec.granule import Granule
from crec.document import DocumentCollection

dir_path = os.path.dirname(os.path.realpath(__file__))

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

class Package:
    def __init__(self, date: str, client: GovInfoAPI, group_by: str = 'speaker') -> None:
        self.date = date
        self.client = client
        self.group_by = group_by

        self.summary_url = client.root_url + f'packages/CREC-{date}/summary?api_key={client.api_key}'
        self.granules_url = client.root_url + f'packages/CREC-{date}/granules?offset=0&pageSize=100&api_key={client.api_key}'
        self.zip_url = client.root_url + f'packages/CREC-{date}/zip?api_key={client.api_key}'

        self.granule_ids = []
        self.granules : Dict[str, Granule] = {}
        self.document_collection = DocumentCollection(group_by=group_by)

    @staticmethod
    def get_granule_roots(root: et):
        return {c.attrib['ID'].split('id-')[1]: c for c in root if c.tag == '{http://www.loc.gov/mods/v3}relatedItem'}

    def _get_zip(self, write: bool = False, out_path: str = None):
        # this is code that will actually run (still more work to do), 
        # but it takes too long for testing purposes -- so I just downloaded some data
        # and open it directly

        # r = requests.get(self.zip_url)
        # z = zipfile.ZipFile(io.BytesIO(r.content))
        # htm_f_names = [f_name for f_name in z.namelist() if '.htm' in f_name]
        # mods_f_name = [f_name for f_name in z.namelist() if 'mods.xml' in f_name][0]

        mods_f_name = dir_path + '/data/CREC-2018-01-04/mods.xml'
        with open(mods_f_name) as mods:
            tree = et.fromstring(mods.read())
        
        granule_roots = self.get_granule_roots(tree)
        for g_id, g_root in granule_roots.items():
            g = Granule(granule_id=g_id, client=self.client, group_by=self.group_by)
            g.parse_xml(g_root)

            htm_f_name = dir_path + f'/data/CREC-2018-01-04/html/{g_id}.htm'
            with open(htm_f_name) as htm:
                raw_text = htm.read()
            g.parse_htm(raw_text)
            self.granules[g_id] = g

    async def get_granule_ids(self, client: GovInfoAPI):
        got_all_ids = False

        granules_resp_validity, granules_resp = await client.get(self.granules_url)
        if granules_resp_validity:
            got_all_ids = True
        else:
            return []
        
        granules_json = granules_resp.json()
        
        granules_count = granules_json['count']
        granule_ids = [g['granuleId'] for g in granules_json['granules']]

        if granules_count > 100:
            got_all_ids = False
            remaining_pages = math.ceil((granules_count - 100)/100)
            for p in range(1, remaining_pages + 1):
                offset = 100*p
                next_granules_resp_validity, next_granules_resp = await client.get(self.granules_url.replace('offset=0', f'offset={offset}'))
                if next_granules_resp_validity:
                    pass
                else:
                    break
                next_granules_json = next_granules_resp.json()
                granule_ids += [g['granuleId'] for g in next_granules_json['granules']]
            got_all_ids = True
        
        return got_all_ids, granule_ids


class Record:
    def __init__(self, group_by: str = 'speaker', batch_size: int = 200, wait: Union[bool, int] = 300, api_key=None) -> None:
        self.group_by = group_by
        self.document_collection = DocumentCollection(group_by=group_by)

        self.client = GovInfoAPI(wait=wait)
        self.batch_size = batch_size

        self.missing = {'days': [], 'granules': []}

    async def _get_granules_in_batch(self, granules: List[Granule], client: GovInfoAPI):
        batches = [granules[i:i + self.batch_size] for i in range(0, len(granules), self.batch_size)]
        for batch in batches:
            tasks = []
            for g in batch:
                tasks.append(asyncio.create_task(g.async_get(client=client)))
                await asyncio.gather(*tasks, return_exceptions=True)

        for g in granules:
            if g.valid is False:
                self.missing['granules'].append(g.granule_id)

    async def _get_granules_from_ids(self, granule_ids: List[str], client: GovInfoAPI) -> List[Granule]:
        granules = [Granule(granule_id=g_id, client=client, group_by=self.group_by) for g_id in granule_ids]
        
        await self._get_granules_in_batch(granules=granules, client=client)

        return granules

    def get_documents_from_ids(self, granule_ids: List[str] = []):
        granules = asyncio.run(self._get_granules_from_ids(granule_ids=granule_ids))
        for g in granules:
            self.document_collection.merge(g.document_collection)

    async def _get_granule_ids_from_dates(self, dates: List[str], client: GovInfoAPI) -> List[str]:
        granule_ids = []
        for d in dates:
            p = Package(date=d, client=client, group_by=self.group_by)
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

    def get_documents_from_dates(self, start_date: Union[str, datetime.datetime] = None, end_date: Union[str, datetime.datetime] = None, dates: List[Union[str, datetime.datetime]] = None):
        if start_date is not None and end_date is not None and dates is None:
            start_date = validate_date(date=start_date, param_name='start date')
            end_date = validate_date(date=end_date, param_name='end date')
            dates = generate_date_range(start=start_date, end=end_date)
        elif start_date is None and end_date is None and dates is not None:
            dates = [validate_date(date=d, param_name='each date in dates') for d in dates]

        granules = asyncio.run(self._get_granules_from_dates(dates=dates))
        # for g in granules:
        #     self.document_collection.merge(g.document_collection)