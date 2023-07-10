from crec import Record

api_key = 'VjAEDf7KZQF5WfSHJjuwz7HaEcbAkFdpQovrtf8S'

# TODO: add write outpath
r = Record(granule_ids=['CREC-2019-01-02-pt1-PgS8062-2', 'CREC-2019-01-02-pt1-PgS8051-8'], granule_class_filter=['SENATE'], write_logs=True, write_path='tests/logs.txt', api_key=api_key)
print(r.passages.to_df())