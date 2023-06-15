from typing import List, Union
import datetime
import itertools


from crec.granule import Granule
from crec.downloader import Downloader
from crec.logger import Logger
from crec.text import TextCollection

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
    def __init__(
        self, 
        start_date: Union[str, datetime.datetime] = None, 
        end_date: Union[str, datetime.datetime] = None, 
        dates: List[Union[str, datetime.datetime]] = None, 
        granule_ids: List[str] = None,
        granule_class_filter: List[str] = None,
        parse: bool = True,
        write: Union[bool, str] = False,
        batch_size: int = 200,
        wait: Union[int, bool] = 300,
        retry_limit: Union[bool, int] = 5,
        api_key: str = None,
        verbose: bool = True,
        logger_outpath: str = None
    ) -> None:
        self.logger = Logger(verbose=verbose, logger_outpath=logger_outpath)
        self.downloader = Downloader(granule_class_filter=granule_class_filter, parse=parse, batch_size=batch_size, wait=wait, retry_limit=retry_limit, api_key=api_key, logger=self.logger)

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
            
        elif start_date is None and end_date is None and dates is None and granule_ids is not None:
            self.granules = self.downloader.get_from_ids(granule_ids=granule_ids)

        else:
            raise ValueError("Must specify a start date and an end date or a list of dates or a list of granule ids")

        self.paragraphs = TextCollection()
        self.passages = TextCollection()

        for g in self.granules:
            self.paragraphs.merge(g.paragraphs)
            self.passages.merge(g.passages)

    @property
    def raw_text(self) -> List[str]:
        return [g.raw_text for g in self.granules]

    @property
    def clean_text(self) -> List[str]:
        return [g.clean_text for g in self.granules]