from __future__ import annotations

from typing import TypedDict

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline


class AgeClassificationResult(TypedDict):
    label: str
    age_score: float
    not_age_score: float
    confidence: float


class AgeClassifier:
    LABELS = ("Age", "Not Age")
    TEST_SIZE = 0.2
    RANDOM_STATE = 42

    TRAINING_EXAMPLES: list[tuple[str, str]] = [
        ("age of respondent", "Age"),
        ("your age", "Age"),
        ("how old are you", "Age"),
        ("how old", "Age"),
        ("how old you are", "Age"),
        ("current age", "Age"),
        ("respondent age", "Age"),
        ("what is your age", "Age"),
        ("what is your current age", "Age"),
        ("just to ensure we represent different groups what is your age", "Age"),
        ("age group", "Age"),
        ("into which of the following ranges does your current age fall", "Age"),
        ("what is your exact age", "Age"),
        ("could you please tell me your age", "Age"),
        ("my age", "Age"),
        ("age of the person", "Age"),
        ("age of individual", "Age"),
        ("age of the participant", "Not Age"),
        ("age of the patient", "Not Age"),
        ("age of patient", "Not Age"),
        ("age of child", "Not Age"),
        ("age of customer", "Not Age"),
        ("date of birth", "Not Age"),
        ("birth date", "Not Age"),
        ("patient age", "Not Age"),
        ("dog age", "Not Age"),
        ("age of the dog", "Not Age"),
        ("age of the cat", "Not Age"),
        ("age of the bird", "Not Age"),
        ("god age","Not Age"),
        ("horse age","Not Age"),
        ("town age","Not Age"),
        ("book age","Not Age"),
        ("name of respondent", "Not Age"),
        ("your name", "Not Age"),
        ("what age group of patients do you work with", "Not Age"),
        ("employees age", "Not Age"),
        ("how old are you when you start the diploma", "Not Age"),
        ("how many old people you know", "Not Age"),
        ("how you describe the life at your age", "Not Age"),
        ("what is the age of your first born child", "Not Age"),
        ("have you lived in or visited israel since the age of 12", "Not Age"),
        ("how old are they", "Not Age"),
        ("what is your childrens age", "Not Age"),
        ("which of the following age groups do you work with", "Not Age"),
        ("please describe the type of job or the field you work in that involves adults 25 35 years old", "Not Age"),
    ]

    _instance: "AgeClassifier | None" = None

    def __init__(self, training_examples: list[tuple[str, str]]) -> None:
        if len(training_examples) < 2:
            raise ValueError("At least two training examples are required")

        texts, labels = zip(*training_examples)
        if set(labels) != set(self.LABELS):
            raise ValueError(f"Training examples must contain labels: {self.LABELS}")

        train_texts, test_texts, train_labels, test_labels = train_test_split(
            texts,
            labels,
            test_size=self.TEST_SIZE,
            random_state=self.RANDOM_STATE,
            stratify=labels,
        )

        self.validation_model = self._create_model()
        self.validation_model.fit(train_texts, train_labels)
        self.validation_accuracy = float(
            self.validation_model.score(test_texts, test_labels)
        )

        self.model = self._create_model()
        self.model.fit(texts, labels)

    @staticmethod
    def _create_model() -> Pipeline:
        return Pipeline([
            (
                "vectorizer",
                TfidfVectorizer(
                    lowercase=True,
                    analyzer="char_wb",
                    ngram_range=(2, 5),
                    sublinear_tf=True,
                ),
            ),
            (
                "classifier",
                LogisticRegression(
                    C=2.0,
                    class_weight="balanced",
                    max_iter=2000,
                    random_state=AgeClassifier.RANDOM_STATE,
                ),
            ),
        ])

    @classmethod
    def get_instance(cls) -> "AgeClassifier":
        if cls._instance is None:
            cls._instance = cls(list(cls.TRAINING_EXAMPLES))
        return cls._instance

    def predict(self, text: str) -> tuple[str, float, float]:
        probabilities = self.model.predict_proba([text])[0]
        classifier = self.model.named_steps["classifier"]
        scores = dict(zip(classifier.classes_, probabilities))
        age_score = float(scores["Age"])
        not_age_score = float(scores["Not Age"])
        prediction = str(self.model.predict([text])[0])
        return prediction, age_score, not_age_score


def tokenize_text(text: str) -> list[str]:
    if not text:
        return []
    tokens: list[str] = []
    current: list[str] = []
    for char in text.lower():
        if char.isalnum():
            current.append(char)
        elif current:
            tokens.append("".join(current))
            current = []
    if current:
        tokens.append("".join(current))
    return tokens


def normalize_header_text(text: str) -> str:
    return " ".join(tokenize_text(text))


def _predict_header(text: str) -> tuple[str, float, float]:
    return AgeClassifier.get_instance().predict(text)


def classify_age_header(header: str) -> AgeClassificationResult:
    normalized = normalize_header_text(header)
    if not normalized:
        return {
            "label": "Not Age",
            "age_score": 0.0,
            "not_age_score": 0.0,
            "confidence": 0.0,
        }

    prediction, age_score, not_age_score = _predict_header(normalized)
    return {
        "label": prediction,
        "age_score": age_score,
        "not_age_score": not_age_score,
        "confidence": abs(age_score - not_age_score),
    }


# def classify_age_header_with_confidence(header: str) -> dict[str, object]:
#     """Return a classification together with a human-readable confidence level."""
#     result = classify_age_header(header)
#     if result["confidence"] > 0.4:
#         confidence_level = "high"
#     elif result["confidence"] > 0.2:
#         confidence_level = "medium"
#     else:
#         confidence_level = "low"

#     return {**result, "confidence_level": confidence_level}
