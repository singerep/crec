import requests # TODO: switch to httpx
import json
import datetime
import typing
import zipfile
import io
import os
from xml.etree import ElementTree as et
import math
import time
import httpx
import asyncio

from crec import GovInfoAPI
from crec.granule import Granule

dir_path = os.path.dirname(os.path.realpath(__file__))

def validate_date(date, param_name):
    if isinstance(date, str):
        try:
            datetime.datetime.strptime(date, '%Y-%m-%d')
        except ValueError:
            raise ValueError('date string must in YYYY-mm-dd format')
    elif isinstance(date, datetime.datetime):
        date = date.strftime('%Y-%m-%d')
    else:
        raise TypeError(f'{param_name} must be a string in YYYY-mm-dd format or a datetime.datetime object')
    
    return date

def generate_date_range(start: str, end: str):
    start_obj = datetime.datetime.strptime(start, '%Y-%m-%d')
    end_obj = datetime.datetime.strptime(end, '%Y-%m-%d')
    dates = []
    delta = end_obj - start_obj

    for i in range(delta.days + 1):
        day = start_obj + datetime.timedelta(days=i)
        if day.weekday() not in [5, 6]:
            dates += [datetime.datetime.strftime(day, '%Y-%m-%d')]

    return dates

class Package(GovInfoAPI):
    def __init__(self, date: typing.Union[str, datetime.datetime], api_key=None) -> None:
        super().__init__(api_key)

        date = validate_date(date, 'date')

        self.date = date

        self.summary_url = self.base_url + f'packages/CREC-{date}/summary?api_key={self.api_key}'
        self.granules_url = self.base_url + f'packages/CREC-{date}/granules?offset=0&pageSize=100&api_key={self.api_key}'
        self.zip_url = self.base_url + f'packages/CREC-{date}/zip?api_key={self.api_key}'

        self.granules = {}

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
            g = Granule(g_id)
            g.parse_xml(g_root)

            htm_f_name = dir_path + f'/data/CREC-2018-01-04/html/{g_id}.htm'
            with open(htm_f_name) as htm:
                raw_text = htm.read()
            g.parse_htm(raw_text)
            self.granules[g_id] = g

    async def _get_individual(self):
        granules_json = requests.get(self.granules_url).json()
        
        granules_count = granules_json['count']
        granule_ids = [g['granuleId'] for g in granules_json['granules']]

        if granules_count > 100:
            remaining_pages = math.ceil((granules_count - 100)/100)
            for p in range(1, remaining_pages + 1):
                offset = 100*p
                next_granules_json = requests.get(self.granules_url.replace('offset=0', f'offset={offset}')).json()
                granule_ids.append([g['granuleId'] for g in next_granules_json['granules']])

        async with httpx.AsyncClient() as client:
            tasks = []
            for g_id in granule_ids:
                print(g_id)
                g = Granule(g_id)
                self.granules[g_id] = g
                tasks.append(asyncio.create_task(g.async_get(client)))
                # g.get(client=client)

            await asyncio.gather(*tasks)

    def get(self, method: str = 'individual'):
        if method == 'zip':
            self._get_zip()
        elif method == 'individual':
            asyncio.run(self._get_individual())
        else:
            # raise some error
            ...


class DocumentCollection(GovInfoAPI):
    def __init__(self, start_date: str = None, end_date: str = None, dates: list = None, api_key=None) -> None:
        super().__init__(api_key)

        if (start_date is not None and end_date is not None and dates is None) or (start_date is None and end_date is None and dates is not None):
            pass
        else:
            # raise some error
            ...

        if start_date is not None:
            dates = generate_date_range(start_date, end_date)
        else:
            for date in dates:
                # TODO: does not work
                validate_date(date, 'each date within dates')

        self.packages = {}
        for date in dates:
            p = Package(date)
            self.packages[date] = p

    def get(self, method: str = 'zip'):
        for date, package in self.packages.items():
            package.get(method=method)

    @property
    def documents(self):
        docs = {}
        for date, p in self.packages.items():
            for g_id, g in p.granules.items():
                for speaker, text in g.documents.items():
                    docs[f'{g_id}-{speaker}'] = text
        return docs