from unittest import TestCase, main
import os
from dotenv import load_dotenv
from pandas import DataFrame

load_dotenv()
GOVINFO_KEY = os.getenv('GOVINFO_KEY')

from crec.record import Record

class RecordTest(TestCase):
    def test_record(self):
        record = Record(start_date='2018-01-04', end_date='2018-01-04', print_logs=False, api_key=GOVINFO_KEY)

        self.assertIsInstance(record.paragraphs.to_df(), DataFrame)
        self.assertGreater(len(record.paragraphs.to_list()), len(record.passages.to_list()))


if __name__ == "__main__":
    main()