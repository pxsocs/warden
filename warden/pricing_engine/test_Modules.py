# Run by executing from warden directory:
# python3 -m pricing_engine.test_Modules

import unittest

from backend.utils import load_config
from backend.warden_modules import current_path, home_path, specter_df

import pandas as pd


class TestPricing(unittest.TestCase):

    def test_paths(self):
        print("Checking that current and home paths can be returned...")
        print(f"Current Path: {current_path()}")
        print(f"Home Path: {home_path()}")
        self.assertIsNotNone(current_path())
        self.assertIsNotNone(home_path())

    def test_specter_txs(self):
        print("Testing Specter Transactions...")
        df = specter_df()
        print(df)
        self.assertIsInstance(df, pd.DataFrame)
        self.assertFalse(df.empty)


if __name__ == '__main__':
    print("Running tests... Please wait...")

    unittest.main()
