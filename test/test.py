from crec.package import Package
from crec.granule import Granule

# p = Package('2018-01-04')
# p.get()

# for g_id, g in p.granules.items():
#     print(g.raw_text)

g = Granule('CREC-2018-01-04-pt1-PgS27-8')
g.get()
# for p in g.paragraphs:
#     print(p.speaker)
#     print(p.text)

for d_id, d in g.documents.items():
    print(d_id)
    print(d)
    print()

# print(g.htm_url)

# for g in p.granules:
#     print(p.granules[g].documents)