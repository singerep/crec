from unittest import TestCase, main
import os
from dotenv import load_dotenv
from pandas import DataFrame

load_dotenv()
GOVINFO_KEY = os.getenv('GOVINFO_KEY')

from crec.record import Record

class RecordTest(TestCase):
    def test_record(self):
        with self.assertRaises(ValueError):
            Record(print_logs=False, api_key=GOVINFO_KEY)
        
        record = Record(start_date='2018-01-04', end_date='2018-01-04', print_logs=False, api_key=GOVINFO_KEY)
        self.assertEqual(len(record.granules), 53)

        self.assertIsInstance(record.paragraphs.to_df(), DataFrame)

if __name__ == "__main__":
    main()