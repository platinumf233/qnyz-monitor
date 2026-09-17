import unittest
from datetime import date
from unittest.mock import Mock
import flexible_monitor as fm


class DeploymentTests(unittest.TestCase):
    def test_booking_window_and_fifteen_nights(self):
        periods = fm.periods(date(2026, 9, 17))
        self.assertEqual(periods[0], ('2026-09-21', '2026-10-06'))
        self.assertEqual(periods[-1], ('2026-10-07', '2026-10-22'))
        self.assertEqual(len(periods), 17)
        self.assertEqual(fm.periods(date(2026, 9, 22))[0][0], '2026-09-24')

    def test_failure_does_not_mark_sent(self):
        state = {}
        with self.assertRaises(RuntimeError):
            fm.deliver({'x': '房源'}, state, '2026-09-17', Mock(side_effect=RuntimeError('failed')))
        self.assertEqual(state, {})

    def test_merge_dedupe_and_daily_limit(self):
        state = {}
        send = Mock()
        fm.deliver({'a': 'A', 'b': 'B'}, state, '2026-09-17', send)
        self.assertEqual(send.call_count, 1)
        fm.deliver({'a': 'A', 'b': 'B'}, state, '2026-09-17', send)
        self.assertEqual(send.call_count, 1)
        state['count'] = 4
        fm.deliver({'c': 'C'}, state, '2026-09-17', send)
        self.assertNotIn('c', state['sent'])
        fm.deliver({'c': 'C'}, state, '2026-09-18', send)
        self.assertIn('c', state['sent'])


if __name__ == '__main__':
    unittest.main()
