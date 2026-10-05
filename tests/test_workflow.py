import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class WorkflowSmokeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.work = Path(self.temp.name)
        for name in ('run.sh', 'AGENTS.md', 'prompt_market_research.md',
                     'prompt_improvement_points.md'):
            shutil.copy2(ROOT / name, self.work / name)
        shutil.copytree(ROOT / 'scripts', self.work / 'scripts')
        self.runner = self.work / 'mock-opencode'
        self.runner.write_text(
            '#!' + sys.executable + '\nimport runpy\nrunpy.run_path(' +
            repr(str(self.work / 'scripts/smoke_opencode_runner.py')) +
            ', run_name="__main__")\n'
        )
        self.runner.chmod(0o755)

    def run_phase(self, date, phase='all'):
        env = {key: value for key, value in os.environ.items()
               if not key.startswith(('RUN_', 'PREVIOUS_', 'OPENCODE_', 'AGENT_', 'SKIP_', 'KEEP_'))}
        env.update(AGENT_BACKEND='opencode', OPENCODE_COMMAND=str(self.runner),
                   RUN_DATE=date, RUN_PHASE=phase, SKIP_DISCORD_POST='1')
        return subprocess.run(['bash', './run.sh'], cwd=self.work, env=env,
                              capture_output=True, text=True)

    def test_report_and_next_day_review_without_external_services(self):
        for date in ('2026-10-04', '2026-10-05'):
            with self.subTest(date=date):
                result = self.run_phase(date)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertIn('validated report artifacts:', result.stdout)
                self.assertIn('skipping Discord post:', result.stderr)
                self.assertNotIn('illegal option', result.stderr)
                report = self.work / 'agy-market-report' / date / 'report'
                self.assertTrue((report / 'market_facts.json').is_file())
        review = self.work / 'agy-market-report/2026-10-04/result'
        self.assertTrue((review / 'prompt_improvement.md').is_file())
        self.assertTrue((review / 'input/market_score.json').is_symlink())
        self.assertEqual(self.run_phase('2026-10-05', 'validate').returncode, 0)

    def test_invalid_run_date_stops_before_creating_artifacts(self):
        for date in ('invalid', '2026-02-30'):
            with self.subTest(date=date):
                result = self.run_phase(date)
                self.assertEqual(result.returncode, 1)
                self.assertIn('Invalid RUN_DATE date:', result.stderr)
                self.assertFalse((self.work / 'agy-market-report').exists())


if __name__ == '__main__':
    unittest.main()
