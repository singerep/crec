from unittest import TestCase, main
from httpx import Response
from typing import List
import asyncio
import os
from dotenv import load_dotenv

load_dotenv()
GOVINFO_KEY = os.getenv('GOVINFO_KEY')

from crec.api import GovInfoClient, RateLimitError, APIKeyError
from crec.record import Record
from crec.logger import Logger

class APITest(TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.logger = Logger(rate_limit_wait=False, print_logs=False, write_logs=False, write_path=None)

    def test_govinfo_client(self):
        client = GovInfoClient(100, 100, logger=self.logger, api_key=GOVINFO_KEY)
        response_validity, response = asyncio.run(client.get('packages/CREC-2018-01-04/granules/CREC-2018-01-04-pt1-PgS27-8/htm'))
        self.assertIsInstance(response_validity, bool)
        self.assertEqual(response_validity, True)
        self.assertIsInstance(response, Response)
        self.assertIn('FUNDING THE GOVERNMENT', response.text)

        with self.assertRaises(RateLimitError):
            Record(start_date='2018-01-04', end_date='2018-02-04', parse=True, zipped=False, batch_size=10000, batch_wait=0, rate_limit_wait=False, retry_limit=False, print_logs=False, api_key=GOVINFO_KEY)


if __name__ == "__main__":
    main()