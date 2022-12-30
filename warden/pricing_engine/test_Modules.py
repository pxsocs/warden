# Run by executing from warden directory:
# python3 -m pricing_engine.test_Modules

import unittest

from backend.utils import home_dir
from backend.warden_modules import specter_df
from backend.config import basedir

import pandas as pd


class TestPricing(unittest.TestCase):

    def test_paths(self):
        print("Checking that current and home paths can be returned...")
        print(f"Current Path: {basedir}")
        print(f"Home Path: {home_dir}")
        self.assertIsNotNone(basedir)
        self.assertIsNotNone(home_dir)

    def test_specter_txs(self):
        print("Testing Specter Transactions...")
        df = specter_df()
        print(df)
        self.assertIsInstance(df, pd.DataFrame)
        self.assertFalse(df.empty)


if __name__ == '__main__':
    print("Running tests... Please wait...")

    unittest.main()
