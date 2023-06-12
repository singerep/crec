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

from crec import GovInfoAPI
from crec.granule import Granule

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
    def __init__(self, date: str, client: GovInfoAPI) -> None:
        self.date = date
        self.client = client

        self.summary_url = f'packages/CREC-{date}/summary?api_key={client.api_key}'
        self.granules_url = f'packages/CREC-{date}/granules?offset=0&pageSize=100&api_key={client.api_key}'
        self.zip_url = f'packages/CREC-{date}/zip?api_key={client.api_key}'

        self.granule_ids = []
        self.granules : Dict[str, Granule] = {}

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
            g = Granule(granule_id=g_id, client=self.client)
            g.parse_xml(g_root)

            htm_f_name = dir_path + f'/data/CREC-2018-01-04/html/{g_id}.htm'
            with open(htm_f_name) as htm:
                raw_text = htm.read()
            g.parse_htm(raw_text)
            self.granules[g_id] = g

    async def get_granule_ids(self, client: GovInfoAPI):
        got_all_ids = False

        granules_resp_validity, granules_resp = await client.get(self.granules_url, params={'offset': '0', 'pageSize': '100'})
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
                next_granules_resp_validity, next_granules_resp = await client.get(self.granules_url, params={'offset': f'{offset}', 'pageSize': '100'})
                if next_granules_resp_validity:
                    pass
                else:
                    break
                next_granules_json = next_granules_resp.json()
                granule_ids += [g['granuleId'] for g in next_granules_json['granules']]
            got_all_ids = True
        
        return got_all_ids, granule_ids