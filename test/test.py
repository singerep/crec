from crec.package import Package
from crec.granule import Granule

p = Package('2018-01-04')
p.get(method='individual')

for g_id, g in p.granules.items():
    print(g.raw_text)

# g = Granule('CREC-2018-01-04-pt1-PgD7')
# g.get()

# for g in p.granules:
#     print(p.granules[g].documents)