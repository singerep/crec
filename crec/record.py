from typing import List, Set, Union
import datetime
import functools

# TODO: add jupyter notebook tutorial/guide

from crec.granule import Granule
from crec.downloader import Downloader
from crec.logger import Logger
from crec.text import PassageCollection, ParagraphCollection

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
    
    return date.strftime('%Y-%m-%d')

def generate_date_range(start_date: str, end_date: str) -> List[str]:
    dates = []
    start_date = datetime.datetime.strptime(start_date, '%Y-%m-%d')
    end_date = datetime.datetime.strptime(end_date, '%Y-%m-%d')
    delta = end_date - start_date

    for i in range(delta.days + 1):
        day = start_date + datetime.timedelta(days=i)
        if day.weekday() not in [5, 6]:
            dates += [datetime.datetime.strftime(day, '%Y-%m-%d')]

    return dates


class Record:
    """
    A collection of Congressional Record data from GovInfo's Congressional Record API. 

    Parameters
    ----------
    start_date : Union[str, datetime.datetime] = None
        First date for which CREC data will be retrieved.
    end_date : Union[str, datetime.datetime] = None
        Last date for which CREC data will be retrieved.
    dates : List[Union[str, datetime.datetime]] = None
        A custom list of dates to be used instead of the range created by
        ``start_date`` and ``end_date``.
    granule_ids : List[str] = None
        A list of official granule identifiers to be used instead of
        ``start_date`` and ``end_date`` or ``dates``.
    read_directory : str = None
        A directory to read in XML and HTML files from. There should be one XML file
        and one HTML file per granule in this directory.
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
        See :meth:`.Granule.parse_htm()` for more information.
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
    print_logs : bool
        A boolean that determines whether or not logs are printed to stdout.
    write_logs : bool
        A boolean that determines whether or not logs are written to disk.
    write_path : str = None
        A filename to write logs to. Must be provided if ``write_logs`` is ``True``.

    Attributes
    ----------
    passages : :class:`.PassageCollection`
        Stores the :class:`.Passage` objects associated with this retrieved granule.
    paragraphs : :class:`.ParagraphCollection`
        Stores the :class:`.Paragraph` objects associated with the retrieved granules.
    """
    # TODO add repr
    def __init__(
        self, 
        start_date: Union[str, datetime.datetime] = None, 
        end_date: Union[str, datetime.datetime] = None, 
        dates: List[Union[str, datetime.datetime]] = None, 
        granule_ids: List[str] = None,
        read_directory : str = None,
        granule_class_filter: List[str] = None,
        parse: bool = True,
        write: Union[bool, str] = False,
        zipped: bool = True,
        batch_size: int = 3,
        batch_wait: Union[int, bool] = False,
        rate_limit_wait: Union[int, bool] = 30,
        retry_limit: Union[bool, int] = 5,
        api_key: str = None,
        print_logs: bool = True,
        write_logs: bool = False,
        write_path: str = None
    ) -> None:
        self.logger = Logger(rate_limit_wait=rate_limit_wait, print_logs=print_logs, write_logs=write_logs, write_path=write_path)
        self.downloader = Downloader(granule_class_filter=granule_class_filter, parse=parse, write=write, zipped=zipped, batch_size=batch_size, batch_wait=batch_wait, rate_limit_wait=rate_limit_wait, retry_limit=retry_limit, api_key=api_key, logger=self.logger)

        if start_date is not None or end_date is not None or dates is not None:
            if start_date is not None and end_date is not None and dates is None:
                start_date = validate_date(date=start_date, param_name='start date')
                end_date = validate_date(date=end_date, param_name='end date')
                dates = generate_date_range(start_date=start_date, end_date=end_date)

            elif start_date is None and end_date is None and dates is not None:
                dates = [validate_date(date=d, param_name='each date in dates') for d in dates]

            else:
                raise ValueError("Must specify a start date and an end date or a list of dates")

            self.granules = self.downloader.get_from_dates(dates=dates)
            
        elif granule_ids is not None:
            self.granules = self.downloader.get_from_ids(granule_ids=granule_ids)

        elif read_directory is not None:
            self.granules = self.downloader.get_from_directory(directory=read_directory)

        else:
            raise ValueError("Must specify a start date and an end date or a list of dates or a list of granule ids or a path to a directory")

        self._passage_collection = PassageCollection()

        if self.granules is not None:
            for g in self.granules:
                self._passage_collection.merge(g.passages)

        self.logger.listener.stop()

    @property
    def incomplete_days(self) -> Set[str]:
        """
        A set of date strings that did *not* have all of their associated granule
        identifiers retrieved.
        """
        return self.downloader.incomplete_days
    
    @property
    def incomplete_granules(self) -> Set[str]:
        """
        A set of granule identifiers that did *not* have their data retrieved, 
        parsed, or written to disk (depending on requested behavior).
        """
        return self.downloader.incomplete_granules

    @property
    def raw_text(self) -> List[str]:
        """
        A list containing the text of each granule without elements like headers,
        page numbers, and times removed.
        """
        return [g.raw_text for g in self.granules]

    @property
    def clean_text(self) -> List[str]:
        """
        A list containing the text of each granule with elements like headers,
        page numbers, and times removed.
        """
        return [g.clean_text for g in self.granules]

    @property
    def passages(self) -> PassageCollection:
        return self._passage_collection

    @property
    def paragraphs(self) -> ParagraphCollection:
        return self._passage_collection.paragraphs