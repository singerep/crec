from typing import Union, List, Set, Tuple
import asyncio
from httpx._client import ClientState
from httpx import Response
import zipfile
from io import BytesIO
import re
from xml.etree import ElementTree as et
from xml.etree.ElementTree import Element
import os
from collections import defaultdict
import threading

from crec.api import GovInfoClient
from crec.granule import Granule, get_granule_ids
from crec.logger import Logger
from crec.constants import GRANULE_CLASSES


class AsyncLoopHandler(threading.Thread):
    """
    Class to handle asynchronous requests. Useful especially in the case where a user
    is writing code inside an IPython environment.

    Adapted from https://stackoverflow.com/a/66055205/17834461
    """
    def __init__(self):
        super().__init__(daemon=True)
        self.loop = asyncio.new_event_loop()

    def run(self):
        asyncio.set_event_loop(self.loop)
        self.loop.run_forever()
        return self.loop


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
    zipped : bool = True
        Determines if granules should be requested individually or in zips. Only applies
        to calls where dates are used; if you are requesting individual granule
        identifiers, granules are always requested individually.
    batch_size: int = 3
        The number of request to asynchronously send at the same time. Too high of a 
        number will result in frequent rate limit issues. When requesting zip files,
        this number should be low. When requesting files individually, this should be
        much higher. To avoid rate limiting, try around 200.
    batch_wait : Union[int, bool] = False
        If ``batch_wait`` is an ``int``, then after requesting granule data in each
        batch of size ``batch_size``, the program will halt for ``batch_wait`` seconds.
        Otherwise, ``batch_size`` should be ``False``, and the program will not pause
        after each batch. When requesting zip files, a ``batch_wait`` is not necessary.
        When requesting files individually, the ``batch_wait`` should be around 2-5
        seconds.
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
    def __init__(self, granule_class_filter: List[str], parse: bool, write: Union[bool, str], zipped: bool, batch_size: int, batch_wait: Union[bool, int], rate_limit_wait: Union[bool, int], retry_limit: Union[bool, int], api_key: str, logger: Logger) -> None:
        if parse is False and write is False:
            raise Exception("You are neither parsing nor writing text and metadata; you must do at least one.")
        self.granule_class_filters = granule_class_filter
        self.valid_classes = [c for c in GRANULE_CLASSES if c in granule_class_filter] if granule_class_filter is not None else GRANULE_CLASSES
        self.invalid_classes = [c for c in GRANULE_CLASSES if c not in granule_class_filter] if granule_class_filter is not None else []
        self.parse = parse
        self.write = write
        self.zipped = zipped
        self.batch_size = batch_size
        self.batch_wait = batch_wait
        self.client = GovInfoClient(rate_limit_wait=rate_limit_wait, retry_limit=retry_limit, logger=logger, api_key=api_key)
        self.logger = logger

        self.incomplete_days : Set[str] = set()
        self.incomplete_granules : Set[str] = set()

        self._loop_handler = AsyncLoopHandler()
        self._loop_handler.start()

    async def get_granules_in_batch(self, granules: List[Granule], client: GovInfoClient) -> List[Granule]:
        """
        Takes as an input a list of :class:`.Granule` objects and a 
        :class:`GovInfoClient`. Splits the granules into batches of 
        size ``self.batch_size``. Within each batch, a :class:`asyncio.Task` is created
        which consists of getting the granule's data, and potentially parsing and
        writing it (depending on ``self.parse`` and ``self.write``). 
        Should only be called internally.
        """
        if self.batch_size < 10 or self.batch_wait is False:
            self.logger.log(message='since you are requested granules individually, for optimal performance, you can safely increase the batch_size parameter to 200 with a batch_wait time of 2 seconds')

        self.incomplete_granules = set([g.attributes['granuleId'] for g in granules])

        batches = [granules[i:i + self.batch_size] for i in range(0, len(granules), self.batch_size)]
        for i, batch in enumerate(batches):
            self.logger.log(message=f'getting granules individually in batch {i + 1} of {len(batches)}')
            tasks = []
            for g in batch:
                tasks.append(self._loop_handler.loop.create_task(g.async_get(client=client, parse=self.parse, write=self.write)))
            
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
        future = asyncio.run_coroutine_threadsafe(self.get_granules_from_ids(granule_ids=granule_ids, client=self.client), self._loop_handler.loop)
        granules = future.result()
        return granules

    def get_from_directory(self, directory: str) -> List[Granule]:
        """
        Takes as an input a path and a creates a :class:`.Granule` object for each set
        of XML and HTML files in that directory.
        """
        self.logger.log(f"getting granules from '{directory}'")
        granules = []

        granule_file_map = defaultdict(dict)
        for f in os.listdir(directory):
            if f.endswith('.xml'):
                granule_id = f[:-4]
                granule_file_map[granule_id]['mods'] = directory + '/' + f
            elif f.endswith('.htm'):
                granule_id = f[:-4]
                granule_file_map[granule_id]['htm'] = directory + '/' + f

        for granule_id, files in granule_file_map.items():
            granule = Granule(granule_id=granule_id)
            with open(files['mods']) as mods_file:
                mods = et.fromstring(mods_file.read())
            with open(files['htm']) as htm_file:
                htm = htm_file.read()

            if self.parse:
                granule.parse_responses(xml_response=mods, htm_response=htm)
            if self.write:
                granule.write_responses(write=self.write, xml_response=mods, htm_response=htm)
            if (granule.parsed or not self.parse) and (granule.written or not self.write):
                granule.complete = True

            granule_class = granule.attributes.get('granuleClass', None)
            if granule_class is not None and granule_class in self.valid_classes:
                granules.append(granule)
                if granule.complete is False:
                    self.incomplete_granules.add(granule.id)

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

    async def get_granule_ids_from_dates(self, dates: List[str], client: GovInfoClient) -> List[str]:
        """
        Takes as an input a list of date strings and a :class:`GovInfoClient`. 
        Then, for each date, calls the :meth:`.get_granule_ids` function to get the 
        granule identifiers associated with that given day. Also keeps track of whether 
        all granule identifiers from a particular day were retrieved; if not, that day 
        will be added to ``self.incomplete_days``.
        """
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

    async def get_zips_from_dates_in_batch(self, dates: List[str], client: GovInfoClient) -> List[zipfile.ZipFile]:
        """
        Takes as an input a list of date strings. Returns the zipped files associated
        with those dates.
        """
        responses : List[Tuple[bool, Response]] = []
        zips = []

        batches = [dates[i:i + self.batch_size] for i in range(0, len(dates), self.batch_size)]
        for i, batch in enumerate(batches):
            self.logger.log(message=f'getting granules in zipped files in batch {i + 1} of {len(batches)}')
            tasks = []
            for date in batch:
                tasks.append(self._loop_handler.loop.create_task(client.get(url=f'content/pkg/CREC-{date}.zip', use_api=False)))

            batch_responses = await asyncio.gather(*tasks)
            responses.extend(batch_responses)

            if type(self.batch_wait) == int and i != len(batches) - 1:
                await asyncio.sleep(self.batch_wait)

        for response_validity, response in responses:
            if response_validity is True:
                zip_bytes = BytesIO(response.read())
                date_zip = zipfile.ZipFile(zip_bytes)
                zips.append(date_zip)
            elif response is not None:
                date = re.search(pattern='\d{4}-\d{2}-\d{2}', string=str(response.url))
                if date:
                    self.incomplete_days.add(str(response.url)[date.start():date.end()])

        self.logger.log(f'successfully got zipped files for {len(zips)} of {len(zips) + len(self.incomplete_days)} valid dates; there were {len(self.incomplete_days)} failures')

        return zips

    def granules_from_zips(self, zips: List[zipfile.ZipFile]) -> List[Granule]:
        """
        Takes as an input a set of zipped files. For each zipped file, generates a set
        of :class:`.Granule` objects corresponding to the files within those zips.
        """
        granules = []
        for date_zip in zips:
            file_names = date_zip.namelist()
            mods_file_name = list(filter(lambda f : re.match(pattern='CREC-\d+-\d+-\d+\/mods\.xml', string=f), file_names))[0]
            mods_file = date_zip.read(mods_file_name)
            mods_xml = et.fromstring(mods_file)
            
            for related_item in mods_xml.iter('{http://www.loc.gov/mods/v3}relatedItem'):
                if related_item.attrib.get('type', None) == 'constituent':
                    granule_id = related_item.get('ID', None)
                    if granule_id is None:
                        continue
                    if granule_id[:3] == 'id-':
                        granule_id = granule_id[3:]

                    htm_file_name = list(filter(lambda f : re.search(pattern=f'{granule_id}.htm', string=f), file_names))[0]
                    htm_file = date_zip.read(htm_file_name)
                    htm_content = htm_file.decode()
                    
                    granule = Granule(granule_id=granule_id)
                    if self.parse:
                        granule.parse_responses(xml_response=related_item, htm_response=htm_content)
                    if self.write:
                        granule.write_responses(write=self.write, xml_response=related_item, htm_response=htm_content)
                    if (granule.parsed or not self.parse) and (granule.written or not self.write):
                        granule.complete = True

                    granule_class = granule.attributes.get('granuleClass', None)
                    if granule_class is not None and granule_class in self.valid_classes:
                        granules.append(granule)
                        if granule.complete is False:
                            self.incomplete_granules.add(granule.id)

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

    async def get_granules_from_zips(self, dates: List[str]) -> List[Granule]:
        """
        Takes as an input a list of date strings. Returns a set of :class:`.Granule`
        objects from those days, but requests the granules in zip files as opposed to
        one at a time.
        """
        async with self.client as client:
            zips = await self.get_zips_from_dates_in_batch(dates=dates, client=client)
            granules = self.granules_from_zips(zips=zips)
        return granules

    def get_from_dates(self, dates: List[str] = []) -> List[Granule]:
        """
        Takes as an input a list of date strings and executes the 
        :meth:`.Downloader.get_granules_from_zips()` coroutine if ``self.zipped`` is 
        ``True`` or the :meth:`.Downloader.get_granules_from_dates()` coroutine if 
        ``self.zipped`` is ``False``.
        """
        self.logger.log(f'getting granules with the following classes: {self.valid_classes}; skipping granules with the following classes: {self.invalid_classes}')
        if self.zipped:
            future = asyncio.run_coroutine_threadsafe(self.get_granules_from_zips(dates=dates), self._loop_handler.loop)
            granules = future.result()
            return granules
        else:
            future = asyncio.run_coroutine_threadsafe(self.get_granules_from_dates(dates=dates), self._loop_handler.loop)
            granules = future.result()
            return granules