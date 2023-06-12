from crec.package import Package
from crec.granule import Granule
from crec.api import GovInfoAPI
from crec.collection import Collection

import time

c = Collection()
c.from_dates(dates=[
    '2018-01-04',
    # '2018-01-05',
    # '2018-01-06',
    # '2018-01-07',
    # '2018-01-08',
    # '2018-01-09',
    # '2018-01-10',
    # '2018-01-11',
    # '2018-01-12',
    # '2018-01-13',
    # '2018-01-14',
    # '2018-01-15',
    # '2018-01-16',
    # '2018-01-17',
])

# for g in c.granules:
#     print(g.granule_id, g.speakers, len(g.paragraphs))
# c.from_ids(granule_ids=['CREC-2018-01-04-pt1-PgS27-7'])
# print(c.all_clean_text)
# for p in c.paragraphs(include_non_speaking=True, include_unknown_speaker=True):
#     print(p)

# print(c.granules)
# print(c.paragraphs())
print(c.paragraph_df())
# print(len(c.missing['granules']))

# needs review
# CREC-2018-01-04-pt1-PgS44-3