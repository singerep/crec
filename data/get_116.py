from crec import Record

api_key = 'VjAEDf7KZQF5WfSHJjuwz7HaEcbAkFdpQovrtf8S'
r = Record(start_date='2019-01-03', end_date='2021-01-03', granule_class_filter=['SENATE', 'HOUSE'], batch_wait=5, retry_limit=False, api_key=api_key)
r.paragraphs.to_df().to_csv('data/116_paragraphs.csv')
r.passages.to_df().to_csv('data/116_passages.csv')