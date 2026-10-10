import contextlib
import io
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
import instalador_posix as posix
import modelos_enlace


class PosixInstallerTests(unittest.TestCase):
    def test_profiles_are_limited_to_the_supported_hosts(self):
        name, profile = posix.select_profile("Linux", "x86_64")
        self.assertEqual(name, "linux-nvidia")
        self.assertEqual(profile["platform"], "linux")
        name, profile = posix.select_profile("Darwin", "arm64")
        self.assertEqual(name, "macos-apple-silicon")
        with self.assertRaises(posix.InstallerError):
            posix.select_profile("Darwin", "x86_64")

    def test_dry_run_never_creates_the_destination(self):
        with tempfile.TemporaryDirectory() as folder, contextlib.redirect_stdout(io.StringIO()):
            destination = Path(folder) / "ComfyUI"
            config = {"comfyui": {"revision": "v-test", "repository": "https://example.invalid/ComfyUI.git"}}
            profile = {"label": "Test", "platform": "linux", "required_commands": [], "torch_arguments": []}
            self.assertIsNone(posix.install(destination, profile, config, dry_run=True))
            self.assertFalse(destination.exists())

    def test_launcher_uses_the_venv_and_preserves_arguments(self):
        with tempfile.TemporaryDirectory() as folder:
            launcher = posix.write_launcher(Path(folder), "linux")
            content = launcher.read_text(encoding="utf-8")
            self.assertIn('.venv/bin/python', content)
            self.assertIn('"$@"', content)
            if os.name != "nt":
                self.assertTrue(launcher.stat().st_mode & 0o111)

    def test_registry_uses_macos_and_xdg_locations(self):
        with patch.dict("os.environ", {"XDG_DATA_HOME": "/tmp/cineconia-xdg"}, clear=True):
            with patch.object(modelos_enlace.sys, "platform", "linux"):
                self.assertEqual(modelos_enlace.ruta_registro(), os.path.join(
                    "/tmp/cineconia-xdg", "CineConIA", "bibliotecas.json"
                ))
            with patch.object(modelos_enlace.sys, "platform", "darwin"):
                location = modelos_enlace.ruta_registro()
                self.assertIn("Library", location)
                self.assertIn("Application Support", location)
                self.assertTrue(location.endswith("bibliotecas.json"))


if __name__ == "__main__":
    unittest.main()
