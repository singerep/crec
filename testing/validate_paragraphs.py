from selenium import webdriver
from selenium.webdriver.chrome.service import Service
import pandas as pd

# api_key = 'VjAEDf7KZQF5WfSHJjuwz7HaEcbAkFdpQovrtf8S'
# r = Record(start_date='2021-01-01', end_date='2021-01-03', granule_class_filter=['SENATE'], batch_wait=0, api_key=api_key)

paragraphs = pd.read_csv('tests/files/116_passages.csv', index_col=0)

service = Service("/Users/ethansinger/Downloads/chromedriver_114")
driver = webdriver.Chrome(service=service)

for idx, p in paragraphs.iterrows():
    granule_id = p['granuleId']
    package = p['granuleId'][:15]
    url = f'https://api.govinfo.gov/packages/{package}/granules/{granule_id}/htm?api_key=VjAEDf7KZQF5WfSHJjuwz7HaEcbAkFdpQovrtf8S'
    driver.get(url)
    input("correct?")
    # break





# driver.get('https://www.google.com')