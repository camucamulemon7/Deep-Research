import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class ArtifactValidationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.report_dir = Path(self.temp.name)
        subprocess.run([
            sys.executable, str(ROOT / 'scripts/smoke_opencode_runner.py'),
            'run', '--dir', str(self.report_dir),
        ], check=True)

    def validate(self):
        return subprocess.run([
            sys.executable, str(ROOT / 'scripts/validate_report_artifacts.py'),
            str(self.report_dir),
        ], capture_output=True, text=True)

    def test_complete_smoke_artifacts_pass(self):
        result = self.validate()
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_each_required_markdown_file_must_exist_and_have_content(self):
        for name in ('research_context.md', 'market_thesis.md',
                     'morning_market_report.md', 'report_audit.md'):
            path = self.report_dir / name
            original = path.read_text()
            for content in (None, '', ' \n\t'):
                with self.subTest(name=name, content=content):
                    if content is None:
                        path.unlink()
                    else:
                        path.write_text(content)
                    result = self.validate()
                    self.assertEqual(result.returncode, 1, result.stdout)
                    self.assertIn(name, result.stderr)
                    path.write_text(original)

    def test_normalizer_handles_malformed_confidence(self):
        for confidence in ([], {}, None):
            with self.subTest(confidence=confidence):
                path = self.report_dir / 'market_score.json'
                data = json.loads(path.read_text())
                data['scores'][0]['confidence'] = confidence
                path.write_text(json.dumps(data))
                result = subprocess.run([
                    sys.executable, str(ROOT / 'scripts/normalize_report_artifacts.py'),
                    str(self.report_dir),
                ], capture_output=True, text=True)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(json.loads(path.read_text())['scores'][0]['confidence'], 'low')
                self.assertEqual(self.validate().returncode, 0)

    def test_json_null_is_rejected_as_non_object(self):
        for name in ('market_facts.json', 'market_score.json'):
            path = self.report_dir / name
            original = path.read_text()
            with self.subTest(name=name):
                path.write_text('null')
                result = self.validate()
                self.assertEqual(result.returncode, 1, result.stdout)
                self.assertIn(f'{name} must contain a JSON object', result.stderr)
                path.write_text(original)

    def test_malformed_confidence_reports_validation_error_without_traceback(self):
        for confidence in ([], {}, None, 'unknown'):
            with self.subTest(confidence=confidence):
                path = self.report_dir / 'market_score.json'
                data = json.loads(path.read_text())
                data['scores'][0]['confidence'] = confidence
                path.write_text(json.dumps(data))
                result = self.validate()
                self.assertEqual(result.returncode, 1)
                self.assertIn('validation error:', result.stderr)
                self.assertNotIn('Traceback', result.stderr)


if __name__ == '__main__':
    unittest.main()
