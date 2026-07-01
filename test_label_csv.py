import os
import tempfile
import unittest

import pandas as pd

import main


class LabelCsvLoggingTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.original_output_dir = main.HEADERS_OUTPUT_DIR
        self.original_label_file = main.LABELS_OUTPUT_FILE
        main.HEADERS_OUTPUT_DIR = self.temp_dir.name
        main.LABELS_OUTPUT_FILE = os.path.join(self.temp_dir.name, "label_info.csv")

    def tearDown(self):
        main.HEADERS_OUTPUT_DIR = self.original_output_dir
        main.LABELS_OUTPUT_FILE = self.original_label_file
        self.temp_dir.cleanup()

    def test_adds_only_new_headers_for_existing_filename(self):
        main.persist_label_info("sample.csv", ["Age", "Name"])
        main.persist_label_info("sample.csv", ["Age", "Name", "Email"])
        main.persist_label_info("sample.csv", ["Age", "Name", "Email"])

        self.assertTrue(os.path.exists(main.LABELS_OUTPUT_FILE))
        df = pd.read_csv(main.LABELS_OUTPUT_FILE)

        self.assertEqual(list(df["file name"]), ["sample.csv", "sample.csv", "sample.csv"])
        self.assertEqual(list(df["header text"]), ["Age", "Name", "Email"])


if __name__ == "__main__":
    unittest.main()
