from __future__ import annotations

from typing import TypedDict

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


class AgeClassificationResult(TypedDict):
    label: str
    age_score: float
    not_age_score: float
    confidence: float  # New field for overall confidence


class AgeClassifier:
    MIN_AGE_SCORE = 0.25
    CONFIDENCE_THRESHOLD = 0.3  # Minimum difference between scores to be confident

    TRAINING_EXAMPLES: list[tuple[str, str]] = [
        ("age of respondent", "Age"),
        ("your age", "Age"),
        ("how old are you", "Age"),
        ("current age", "Age"),
        ("respondent age", "Age"),
        ("age of the participant", "Age"),
        ("age of the person", "Age"),
        ("what is your age", "Age"),
        ("what is your current age", "Age"),
        ("just to ensure we represent different groups what is your age", "Age"),
        ("age group", "Age"),
        ("into which of the following ranges does your current age fall", "Age"),
        ("what is your exact age", "Age"),
        ("could you please tell me your age", "Age"),
        ("my age", "Age"),

        ("age of patient", "Not Age"),
        ("age of child", "Not Age"),
        ("age of customer", "Not Age"),
        ("date of birth", "Not Age"),
        ("birth date", "Not Age"),
        ("patient age", "Not Age"),
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
        self.training_examples = training_examples

        self.vectorizer = TfidfVectorizer(
            lowercase=True,
            ngram_range=(1, 3),
            stop_words="english",
        )

        texts = [text for text, _ in training_examples]
        transformed = self.vectorizer.fit_transform(texts)

        self.class_vectors = self._build_class_vectors(transformed)

    @classmethod
    def get_instance(cls) -> "AgeClassifier":
        if cls._instance is None:
            cls._instance = cls(list(cls.TRAINING_EXAMPLES))
        return cls._instance

    def _build_class_vectors(self, transformed) -> dict[str, np.ndarray]:
        class_vectors: dict[str, np.ndarray] = {}

        for label in ("Age", "Not Age"):
            indices = [
                i
                for i, (_, example_label) in enumerate(self.training_examples)
                if example_label == label
            ]

            if indices:
                class_vectors[label] = transformed[indices].mean(axis=0).A1

        return class_vectors

    def predict(self, text: str) -> tuple[str, float, float]:
        input_vector = self.vectorizer.transform([text])

        age_vector = self.class_vectors["Age"]
        not_age_vector = self.class_vectors["Not Age"]

        age_score = float(
            cosine_similarity(
                input_vector,
                age_vector.reshape(1, -1)
            )[0][0]
        )

        not_age_score = float(
            cosine_similarity(
                input_vector,
                not_age_vector.reshape(1, -1)
            )[0][0]
        )

        # Use scores for better decision making
        score_diff = age_score - not_age_score
        
        # If both scores are low, default to "Not Age" (conservative approach)
        if max(age_score, not_age_score) < 0.15:
            return "Not Age", age_score, not_age_score
        
        # If age_score is significantly higher and above threshold
        if (
            age_score >= self.MIN_AGE_SCORE
            and score_diff > self.CONFIDENCE_THRESHOLD
        ):
            return "Age", age_score, not_age_score

        return "Not Age", age_score, not_age_score


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


def _predict_with_tfidf(text: str) -> tuple[str, float, float]:
    classifier = AgeClassifier.get_instance()
    return classifier.predict(text)


def classify_age_header(header: str) -> AgeClassificationResult:
    normalized = normalize_header_text(header)

    if not normalized:
        return {
            "label": "Not Age",
            "age_score": 0.0,
            "not_age_score": 0.0,
            "confidence": 0.0
        }

    prediction, age_score, not_age_score = _predict_with_tfidf(normalized)
    
    # Calculate confidence based on score difference
    confidence = abs(age_score - not_age_score)
    
    # Optional: Add a confidence-based label override
    if confidence < 0.1:  # Very low confidence
        prediction = "Not Age"  # Conservative fallback

    return {
        "label": prediction,
        "age_score": age_score,
        "not_age_score": not_age_score,
        "confidence": confidence
    }


# Optional: Helper function to get classification with confidence level
def classify_age_header_with_confidence(header: str) -> dict:
    """Returns classification with confidence level for better decision making."""
    result = classify_age_header(header)
    
    # Determine confidence level
    if result["confidence"] > 0.4:
        confidence_level = "high"
    elif result["confidence"] > 0.2:
        confidence_level = "medium"
    else:
        confidence_level = "low"
    
    return {
        **result,
        "confidence_level": confidence_level
    }