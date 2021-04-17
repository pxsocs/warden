# Run unit tests from the warden directory:
# $ python3 test_Simulator.py
import unittest
from simulator.simulator import simulate_portfolio


class TestSimulator(unittest.TestCase):

    def test_simulator(self):
        print("Testing Portfolio Simulator...")
        # Test if this url can be reached
        assets = ['BTC', 'AAPL']
        weights = [0.9, 0.1]
        rebalance = 'daily'
        fx = 'USD'
        short_term_tax_rate = 0.15
        # Run the simulator
        simulate_portfolio(
            assets=assets,
            weights=weights,
            rebalance=rebalance,
            fx=fx,
            short_term_tax_rate=short_term_tax_rate)


if __name__ == '__main__':
    print("Running tests... Please wait...")

    unittest.main()
