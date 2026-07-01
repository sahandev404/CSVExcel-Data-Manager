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

    def test_overwrites_existing_header_info_for_same_file(self):
        main.persist_label_info("sample.csv", ["Name", "Age"])
        main.persist_label_info("sample.csv", ["Age", "Name"])

        df = pd.read_csv(main.LABELS_OUTPUT_FILE)
        self.assertEqual(len(df), 2)

        age_row = df[(df["file name"] == "sample.csv") & (df["header text"] == "Age")].iloc[0]
        self.assertEqual(age_row["header index"], 0)

    def test_persist_manual_label_text_stores_manual_entry(self):
        result = main.persist_manual_label_text("Age of respondent", "manual.csv")

        self.assertEqual(result["rows_added"], 1)
        self.assertEqual(result["rows_updated"], 0)
        self.assertEqual(result["label_info"]["label"], "Age")
        self.assertEqual(result["label_info"]["header_text"], "Age of respondent")
        self.assertEqual(result["label_info"]["filename"], "manual.csv")

        df = pd.read_csv(main.LABELS_OUTPUT_FILE)
        self.assertEqual(len(df), 1)
        self.assertEqual(df.iloc[0]["file name"], "manual.csv")
        self.assertEqual(df.iloc[0]["header text"], "Age of respondent")


if __name__ == "__main__":
    unittest.main()
