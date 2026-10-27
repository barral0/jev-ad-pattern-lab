import unittest, tempfile
from pathlib import Path
from decimal import Decimal
class BudgetTests(unittest.TestCase):
    def test_atomic_reservations_survive_unknown_usage_and_stop_under_cap(self):
        from inference import Budget
        from labcore import Store
        with tempfile.TemporaryDirectory() as d:
            s=Store(Path(d)); b=Budget(s,'synthetic-run',Decimal('.01'))
            ids=[]
            while True:
                token=b.reserve()
                if token is None: break
                ids.append(token)
            self.assertEqual(len(ids),3)
            self.assertLessEqual(b.total(),Decimal('.01'))
            self.assertIsNone(Budget(s,'synthetic-run',Decimal('.01')).reserve())
            b.settle(ids[0],100,2)
            self.assertIsNotNone(b.reserve())
    def test_cap_cannot_exceed_point4999(self):
        from inference import Budget
        from labcore import Store
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(ValueError): Budget(Store(Path(d)),'x',Decimal('.50'))
