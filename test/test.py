from crec.package import Package

p = Package('2018-01-04')
p.get_individually()

# for g in p.granules:
#     print(p.granules[g].documents)