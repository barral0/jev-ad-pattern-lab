import unittest
from unittest.mock import patch
import media

class TesseractDiscoveryTests(unittest.TestCase):
    def test_standard_windows_install_without_path(self):
        with patch.object(media.shutil, 'which', return_value=None), patch.object(media.Path, 'is_file', return_value=True):
            self.assertTrue(media.find_tesseract().endswith('tesseract.exe'))
            self.assertEqual(media.ocr_status(), 'available')

    def test_missing_install_reports_unavailable(self):
        with patch.object(media.shutil, 'which', return_value=None), patch.object(media.Path, 'is_file', return_value=False):
            self.assertIsNone(media.find_tesseract())
            self.assertIn('unavailable', media.ocr_status())
