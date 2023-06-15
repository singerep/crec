from crec.package import Package
from crec.granule import Granule
from crec.downloader import Downloader
from crec.record import Record

import time

# r = Record(dates=[
#     '2018-01-04',
#     '2018-01-05',
#     '2018-01-06',
#     '2018-01-07',
#     '2018-01-08',
#     '2018-01-09',
#     '2018-01-10',
#     '2018-01-11',
#     '2018-01-12',
#     '2018-01-13',
#     '2018-01-14',
#     '2018-01-15'
# ])

r = Record(start_date='2018-01-04', end_date='2019-01-04')

# print(r.passages.to_df(speaker_attributes=['bioGuideId', 'party']))

# r = Record.from_granule_ids(['CREC-2018-01-11-pt1-PgS153-3'])
# print(r.granules[0].raw_text)
# print(r.passages.to_list())
# print(r.passages.to_df(speaker_attributes=['bioGuideId', 'party']))

# print(len(r.downloader.missing['granules']))

# print(r.paragraphs)