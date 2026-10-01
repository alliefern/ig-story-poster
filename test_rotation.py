"""Offline schedule checks: python -m unittest -v test_rotation.py.

Node is used to verify the dashboard's real schedule against the poster.
No publishing or insights calls are made.
"""
import json
from datetime import date, timedelta
from pathlib import Path
import subprocess
import unittest
from unittest.mock import patch

import post_story as poster


class RotationTest(unittest.TestCase):
    def test_only_two_slots_change_and_manual_days_stay_baseline(self):
        for day in range(1, 13):
            baseline = poster.CYCLE[day - 1]
            for when in (date(2026, 10, 1), date(2026, 10, 16), date(2027, 10, 3)):
                self.assertEqual(poster.plan_for_day(day, when), baseline)
            for when in (date(2026, 10, 2), date(2026, 10, 15)):
                expected = {6: poster.CYCLE[0], 10: poster.CYCLE[2]}.get(day, baseline)
                self.assertEqual(poster.plan_for_day(day, when), expected)
                self.assertEqual(poster.plan_for_day(day, when, manual_override=True), baseline)

    def test_calendar_exposures_and_early_rollback(self):
        days = [date(2026, 10, 2) + timedelta(days=i) for i in range(14)]
        groups = [poster.plan_for_day(poster.cycle_day('2026-09-04', d), d)[0] for d in days]
        self.assertEqual(groups, ['SET_THREE', 'SET_ONE', 'SET_FOUR', 'QUIZ_STANDALONE',
                                 'SET_FIVE', 'SET_TWO', 'SET_SIX', 'QUIZ_STANDALONE',
                                 'SET_ONE', 'QUIZ', 'SET_TWO', 'QUIZ_STANDALONE',
                                 'SET_THREE', 'SET_ONE'])
        with patch.object(poster, 'ROTATION_EXPERIMENT_SLOTS', {}):
            self.assertEqual(poster.plan_for_day(6, days[1]), poster.CYCLE[5])

    def test_dashboard_matches_poster_before_during_and_after(self):
        html = Path('index.html').read_text()
        config = html.split('  const CONFIG = ', 1)[1].split('\n  if (window.', 1)[0]
        helpers = html.split('  const cycleDay = ', 1)[1].split('\n  const esc = ', 1)[0]
        dates = [date(2026, 9, 3) + timedelta(days=i) for i in range(70)]
        script = ('const CONFIG = ' + config + '\nconst DAY = 86400000;'
                  '\nconst utcDate = s => new Date(s + "T00:00:00Z");'
                  '\nconst isoDay = d => d.toISOString().slice(0,10);'
                  '\nconst cycleDay = ' + helpers + '\nconsole.log(JSON.stringify('
                  + json.dumps([d.isoformat() for d in dates])
                  + '.map(d => planFor(utcDate(d)))));')
        plans = json.loads(subprocess.check_output(['node', '-e', script], text=True))
        for d, plan in zip(dates, plans):
            day = poster.cycle_day('2026-09-04', d)
            if day is None:
                self.assertIsNone(plan)
            else:
                group, slides = poster.plan_for_day(day, d)
                self.assertEqual(plan, dict(day=day, group=group, slides=slides), str(d))


if __name__ == '__main__':
    unittest.main()
