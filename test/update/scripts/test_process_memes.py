import importlib.util
import shutil
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[3] / "frontend/scripts/process-memes.py"
spec = importlib.util.spec_from_file_location("process_memes", SCRIPT)
processor = importlib.util.module_from_spec(spec)
spec.loader.exec_module(processor)


@unittest.skipUnless(shutil.which("magick"), "ImageMagick is required")
class ProcessMemesTests(unittest.TestCase):
    def test_shared_crop_preserves_motion_timing_and_source(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source, output = root / "source.gif", root / "result.webp"
            processor.magick(
                "-size",
                "80x60",
                "xc:none",
                "-fill",
                "red",
                "-draw",
                "rectangle 5,10 24,39",
                root / "a.png",
            )
            processor.magick(
                "-size",
                "80x60",
                "xc:none",
                "-fill",
                "blue",
                "-draw",
                "rectangle 45,10 64,39",
                root / "b.png",
            )
            processor.magick(
                "-delay",
                "7",
                root / "a.png",
                "-delay",
                "13",
                root / "b.png",
                "-loop",
                "0",
                source,
            )
            original = source.read_bytes()
            frames, duration = processor.process(source, output)
            self.assertEqual((frames, duration), (2, 200))
            self.assertEqual(source.read_bytes(), original)
            bounds = processor.magick(
                output, "-coalesce", "-format", "%@\n", "info:"
            ).splitlines()
            self.assertNotEqual(bounds[0], bounds[1])

    def test_opaque_background_requires_explicit_color_and_keeps_old_output(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source, output = root / "source.gif", root / "result.webp"
            processor.magick(
                "-size",
                "40x40",
                "xc:black",
                "-fill",
                "red",
                "-draw",
                "rectangle 10,10 30,30",
                source,
            )
            output.write_bytes(b"previous output")
            with self.assertRaisesRegex(ValueError, "--background"):
                processor.process(source, output)
            self.assertEqual(output.read_bytes(), b"previous output")
            processor.process(source, output, background="#000000", fuzz=0)
            self.assertEqual(
                processor.magick(output, "-format", "%[opaque]", "info:").lower(),
                "false",
            )

    def test_source_cannot_be_overwritten(self):
        with self.assertRaisesRegex(ValueError, "覆盖源文件"):
            processor.process("same.webp", "same.webp")


if __name__ == "__main__":
    unittest.main()
