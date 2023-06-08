from crec.package import Package, Record
from crec.granule import Granule
from crec.api import GovInfoAPI
import asyncio
import matplotlib.pyplot as plt

r = Record()
r.get_documents_from_dates(dates=[
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
    # '2018-01-15'
])


# pre_times = [t[0] for t in r.client.limit_log]
# post_times = [t[1] for t in r.client.limit_log]
# limits = [t[2] for t in r.client.limit_log]

# plt.scatter(pre_times, limits)
# plt.show()

# plt.scatter(post_times, limits)
# plt.show()

# print(r.document_collection)


# api = GovInfoAPI()
# print(api.)

# p = Package('2018-01-04')
# p.get()

# for g_id, g in p.granules.items():
#     print(g_id)

# g = Granule('CREC-2018-01-04-pt1-PgS27-8')
# print(g.htm_url)
# g.get()
# for p in g.paragraphs:
#     print(p.speaker)
#     print(p.text)

# print(p.document_collection)

# print(g.htm_url)

# for g in p.granules:
#     print(p.granules[g].documents)