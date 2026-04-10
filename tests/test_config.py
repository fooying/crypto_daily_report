import unittest
from pathlib import Path

from crypto_report.config import load_script_config


class ConfigLoadTests(unittest.TestCase):
    def test_relative_output_dir_resolves_to_base(self):
        base_dir = Path(__file__).resolve().parent.parent
        config = load_script_config(base_dir=base_dir, runtime_overrides={"report_output_dir": "./out"})
        self.assertEqual(config.report_dir, base_dir / "out")

    def test_report_dir_defaults_to_report_dir_name(self):
        base_dir = Path(__file__).resolve().parent.parent
        config = load_script_config(base_dir=base_dir, runtime_overrides={"report_output_dir": None})
        self.assertEqual(config.report_dir, base_dir / config.report_dir_name)

    def test_runtime_override_can_enable_netlify_deploy(self):
        base_dir = Path(__file__).resolve().parent.parent
        config = load_script_config(base_dir=base_dir, runtime_overrides={"enable_netlify_deploy": True})
        self.assertTrue(config.enable_netlify_deploy)


if __name__ == "__main__":
    unittest.main()
