from typing import List, Union
import datetime
import itertools

from crec.granule import Granule
from crec.downloader import Downloader
from crec.paragraph import Paragraph
from crec.passage import Passage
from crec.text_collection import TextCollection

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

def generate_date_range(start_date: datetime.datetime, end_date: datetime.datetime) -> List[str]:
    dates = []
    delta = end_date - start_date

    for i in range(delta.days + 1):
        day = start_date + datetime.timedelta(days=i)
        if day.weekday() not in [5, 6]:
            dates += [datetime.datetime.strftime(day, '%Y-%m-%d')]

    return dates


class Record:
    def __init__(self, granules: List[Granule], downloader: Downloader = None) -> None:
        self.granules = granules
        self.downloader = downloader

        self.paragraphs = TextCollection()
        self.passages = TextCollection()

        for g in self.granules:
            self.paragraphs.merge(g.paragraphs)
            self.passages.merge(g.passages)

    @classmethod
    def from_granule_ids(cls, granule_ids: List[str]):
        downloader = Downloader()
        granules = downloader.get_from_ids(granule_ids=granule_ids)
        return cls(granules, downloader)

    @classmethod
    def from_dates(cls, start_date: Union[str, datetime.datetime] = None, end_date: Union[str, datetime.datetime] = None, dates: List[Union[str, datetime.datetime]] = None):
        if start_date is not None and end_date is not None and dates is None:
            start_date = validate_date(date=start_date, param_name='start date')
            end_date = validate_date(date=end_date, param_name='end date')
            dates = generate_date_range(start=start_date, end=end_date)
        elif start_date is None and end_date is None and dates is not None:
            dates = [validate_date(date=d, param_name='each date in dates') for d in dates]
        
        downloader = Downloader()
        granules = downloader.get_from_dates(dates=dates)
        return cls(granules, downloader)

    @property
    def raw_text(self) -> List[str]:
        return [g.raw_text for g in self.granules]

    @property
    def clean_text(self) -> List[str]:
        return [g.clean_text for g in self.granules]