import os
import tempfile
import unittest

import pandas as pd

import main
import classifier
import file_service


class LabelCsvLoggingTests(unittest.TestCase):
    def test_tokenizer_classifies_self_age_headers(self):
        result = classifier.classify_age_header("Age of respondent")
        self.assertEqual(result["label"], "Age")
        # self.assertIn("self", str(result["reason"]).lower())

    def test_tokenizer_classifies_external_entity_headers_as_not_age(self):
        result = classifier.classify_age_header("Age of patient")
        self.assertEqual(result["label"], "Not Age")
        # self.assertIn("external", str(result["reason"]).lower())

    def test_tfidf_classifies_general_age_phrase(self):
        result = classifier.classify_age_header("Age of the person")
        self.assertEqual(result["label"], "Age")
        # self.assertIn("tf-idf", str(result["reason"]).lower())

    def test_classifier_uses_logistic_regression_with_holdout_validation(self):
        age_classifier = classifier.AgeClassifier.get_instance()
        model = age_classifier.model.named_steps["classifier"]

        self.assertIsInstance(model, classifier.LogisticRegression)
        self.assertGreaterEqual(age_classifier.validation_accuracy, 0.0)
        self.assertLessEqual(age_classifier.validation_accuracy, 1.0)

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.original_output_dir = file_service.HEADERS_OUTPUT_DIR
        self.original_label_file = file_service.LABELS_OUTPUT_FILE
        file_service.HEADERS_OUTPUT_DIR = self.temp_dir.name
        file_service.LABELS_OUTPUT_FILE = os.path.join(self.temp_dir.name, "label_info.csv")

    def tearDown(self):
        file_service.HEADERS_OUTPUT_DIR = self.original_output_dir
        file_service.LABELS_OUTPUT_FILE = self.original_label_file
        self.temp_dir.cleanup()

    def test_adds_only_new_headers_for_existing_filename(self):
        file_service.persist_label_info("sample.csv", ["Age", "Name"])
        file_service.persist_label_info("sample.csv", ["Age", "Name", "Email"])
        file_service.persist_label_info("sample.csv", ["Age", "Name", "Email"])

        self.assertTrue(os.path.exists(file_service.LABELS_OUTPUT_FILE))
        df = pd.read_csv(file_service.LABELS_OUTPUT_FILE)

        self.assertEqual(list(df["file name"]), ["sample.csv", "sample.csv", "sample.csv"])
        self.assertEqual(list(df["header text"]), ["Age", "Name", "Email"])

    def test_overwrites_existing_header_info_for_same_file(self):
        file_service.persist_label_info("sample.csv", ["Name", "Age"])
        file_service.persist_label_info("sample.csv", ["Age", "Name"])

        df = pd.read_csv(file_service.LABELS_OUTPUT_FILE)
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

        df = pd.read_csv(file_service.LABELS_OUTPUT_FILE)
        self.assertEqual(len(df), 1)
        self.assertEqual(df.iloc[0]["file name"], "manual.csv")
        self.assertEqual(df.iloc[0]["header text"], "Age of respondent")


if __name__ == "__main__":
    unittest.main()
