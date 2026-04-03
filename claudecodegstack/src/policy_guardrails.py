#!/usr/bin/env python3
"""
Policy guardrails for book recommendations.
Ensures grade-appropriate and district-suitable book suggestions.
"""

import pandas as pd
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass
from enum import Enum


class PolicyViolationType(Enum):
    GRADE_LEVEL_TOO_HIGH = "grade_level_too_high"
    GRADE_LEVEL_TOO_LOW = "grade_level_too_low"
    READING_LEVEL_INAPPROPRIATE = "reading_level_inappropriate"
    CONTENT_FLAGGED = "content_flagged"
    SERIES_CONTINUITY = "series_continuity_issue"
    AVAILABILITY = "not_available"


@dataclass
class PolicyResult:
    """Result of policy evaluation for a book recommendation."""
    allowed: bool
    violations: List[PolicyViolationType]
    confidence_adjustment: float  # Multiplier for recommendation confidence
    explanation: str


class PolicyGuardrails:
    """Policy enforcement for book recommendations."""

    def __init__(self):
        # Content flags - books with these keywords require review
        self.content_flags = {
            'mature_themes': ['mature', 'adult', 'explicit', 'violence', 'graphic'],
            'sensitive_topics': ['suicide', 'depression', 'abuse', 'drugs', 'alcohol'],
            'controversial': ['religion', 'politics', 'controversial', 'banned']
        }

        # Grade-level reading ranges (Lexile levels)
        self.grade_reading_ranges = {
            6: (500, 950),   # 6th grade: 500L-950L
            7: (650, 1050),  # 7th grade: 650L-1050L
            8: (750, 1150)   # 8th grade: 750L-1150L
        }

        # Maximum deviation from grade level (flexibility)
        self.grade_flexibility = 1  # Can recommend books +/- 1 grade level

    def check_grade_appropriateness(self, book: pd.Series, student_grade: int) -> Tuple[bool, List[PolicyViolationType], str]:
        """Check if book is appropriate for student's grade level."""
        violations = []
        explanation_parts = []

        # Check target grade range
        book_min_grade = book.get('target_grade_min', 6)
        book_max_grade = book.get('target_grade_max', 8)

        # Allow some flexibility around grade levels
        min_allowed = student_grade - self.grade_flexibility
        max_allowed = student_grade + self.grade_flexibility

        if book_max_grade < min_allowed:
            violations.append(PolicyViolationType.GRADE_LEVEL_TOO_LOW)
            explanation_parts.append(f"book is for grades {book_min_grade}-{book_max_grade}, too easy for grade {student_grade}")

        elif book_min_grade > max_allowed:
            violations.append(PolicyViolationType.GRADE_LEVEL_TOO_HIGH)
            explanation_parts.append(f"book is for grades {book_min_grade}-{book_max_grade}, too advanced for grade {student_grade}")

        # Check reading level
        reading_level = book.get('reading_level', 800)
        grade_range = self.grade_reading_ranges.get(student_grade, (600, 1000))
        min_reading, max_reading = grade_range

        # Allow 20% flexibility on reading level
        flexibility = 0.2
        min_flex = min_reading * (1 - flexibility)
        max_flex = max_reading * (1 + flexibility)

        if reading_level < min_flex:
            violations.append(PolicyViolationType.READING_LEVEL_INAPPROPRIATE)
            explanation_parts.append(f"reading level {reading_level}L too low for grade {student_grade} ({min_reading}-{max_reading}L)")

        elif reading_level > max_flex:
            violations.append(PolicyViolationType.READING_LEVEL_INAPPROPRIATE)
            explanation_parts.append(f"reading level {reading_level}L too high for grade {student_grade} ({min_reading}-{max_reading}L)")

        is_appropriate = len(violations) == 0
        explanation = "; ".join(explanation_parts) if explanation_parts else "grade-appropriate"

        return is_appropriate, violations, explanation

    def check_content_suitability(self, book: pd.Series) -> Tuple[bool, List[PolicyViolationType], str]:
        """Check if book content is suitable for middle school students."""
        violations = []
        explanation_parts = []

        # Check title, description, and genre for content flags
        text_to_check = (
            str(book.get('title', '')).lower() + ' ' +
            str(book.get('description', '')).lower() + ' ' +
            str(book.get('genre', '')).lower()
        )

        flagged_categories = []
        for category, keywords in self.content_flags.items():
            for keyword in keywords:
                if keyword in text_to_check:
                    flagged_categories.append(category)
                    break

        if flagged_categories:
            violations.append(PolicyViolationType.CONTENT_FLAGGED)
            explanation_parts.append(f"flagged for: {', '.join(flagged_categories)}")

        # Specific genre checks
        genre = book.get('genre', '').lower()
        if genre in ['horror'] and book.get('target_grade_max', 8) <= 6:
            violations.append(PolicyViolationType.CONTENT_FLAGGED)
            explanation_parts.append("horror genre restricted for younger grades")

        is_suitable = len(violations) == 0
        explanation = "; ".join(explanation_parts) if explanation_parts else "content appropriate"

        return is_suitable, violations, explanation

    def check_series_continuity(self, book: pd.Series, student_history: List[str],
                               books_df: pd.DataFrame) -> Tuple[bool, List[PolicyViolationType], str]:
        """Check if recommending a series book makes sense given reading history."""
        violations = []
        explanation = "series continuity ok"

        if not book.get('is_series', False):
            return True, violations, explanation

        series_name = book.get('series_name', '')
        book_position = book.get('series_position', 1)

        if series_name and book_position > 1:
            # Check if student has read earlier books in the series
            series_books = books_df[
                (books_df['series_name'] == series_name) &
                (books_df['series_position'] < book_position)
            ]

            if len(series_books) > 0:
                read_series_books = [
                    book_id for book_id in student_history
                    if book_id in series_books['book_id'].values
                ]

                # Should have read at least the previous book
                previous_book = series_books[series_books['series_position'] == book_position - 1]

                if len(previous_book) > 0 and previous_book.iloc[0]['book_id'] not in student_history:
                    violations.append(PolicyViolationType.SERIES_CONTINUITY)
                    explanation = f"recommending book {book_position} in {series_name} series, but student hasn't read book {book_position - 1}"

        return len(violations) == 0, violations, explanation

    def check_availability(self, book: pd.Series) -> Tuple[bool, List[PolicyViolationType], str]:
        """Check if book is available for checkout."""
        violations = []

        copies_available = book.get('copies_available', 0)
        if copies_available <= 0:
            violations.append(PolicyViolationType.AVAILABILITY)
            explanation = "no copies currently available"
        else:
            explanation = f"{copies_available} copies available"

        return len(violations) == 0, violations, explanation

    def evaluate_book(self, book: pd.Series, student_grade: int,
                     student_history: List[str], books_df: pd.DataFrame,
                     require_availability: bool = True) -> PolicyResult:
        """Comprehensive policy evaluation for a book recommendation."""

        all_violations = []
        explanation_parts = []
        confidence_multiplier = 1.0

        # Check grade appropriateness
        grade_ok, grade_violations, grade_explanation = self.check_grade_appropriateness(book, student_grade)
        all_violations.extend(grade_violations)
        if grade_explanation != "grade-appropriate":
            explanation_parts.append(grade_explanation)

        # Reduce confidence for grade mismatches but don't block completely
        if grade_violations:
            confidence_multiplier *= 0.7

        # Check content suitability
        content_ok, content_violations, content_explanation = self.check_content_suitability(book)
        all_violations.extend(content_violations)
        if content_explanation != "content appropriate":
            explanation_parts.append(content_explanation)

        # Content flags require librarian review but don't block
        if content_violations:
            confidence_multiplier *= 0.5

        # Check series continuity
        series_ok, series_violations, series_explanation = self.check_series_continuity(
            book, student_history, books_df
        )
        all_violations.extend(series_violations)
        if series_explanation != "series continuity ok":
            explanation_parts.append(series_explanation)

        # Series issues reduce confidence
        if series_violations:
            confidence_multiplier *= 0.8

        # Check availability
        if require_availability:
            available, avail_violations, avail_explanation = self.check_availability(book)
            all_violations.extend(avail_violations)
            explanation_parts.append(avail_explanation)

            # Unavailable books are completely blocked
            if avail_violations:
                confidence_multiplier = 0.0

        # Determine if recommendation is allowed
        # Only block for availability issues or severe content flags
        blocking_violations = [
            PolicyViolationType.AVAILABILITY,
            PolicyViolationType.CONTENT_FLAGGED  # Could be made configurable
        ]

        is_allowed = not any(v in blocking_violations for v in all_violations)

        # Create explanation
        full_explanation = "; ".join(explanation_parts) if explanation_parts else "passes all policy checks"

        return PolicyResult(
            allowed=is_allowed,
            violations=all_violations,
            confidence_adjustment=confidence_multiplier,
            explanation=full_explanation
        )

    def filter_recommendations(self, recommendations: List[Dict], student_grade: int,
                             student_history: List[str], books_df: pd.DataFrame) -> List[Dict]:
        """Filter and adjust recommendations based on policy guardrails."""

        filtered_recommendations = []

        for rec in recommendations:
            book_id = rec['book_id']
            book_info = books_df[books_df['book_id'] == book_id]

            if len(book_info) == 0:
                continue  # Skip if book not found

            book = book_info.iloc[0]

            # Evaluate against policies
            policy_result = self.evaluate_book(book, student_grade, student_history, books_df)

            if policy_result.allowed:
                # Adjust confidence based on policy evaluation
                original_confidence = rec.get('confidence', 1.0)
                adjusted_confidence = original_confidence * policy_result.confidence_adjustment

                # Add policy information to recommendation
                filtered_rec = rec.copy()
                filtered_rec['confidence'] = adjusted_confidence
                filtered_rec['policy_violations'] = [v.value for v in policy_result.violations]
                filtered_rec['policy_explanation'] = policy_result.explanation
                filtered_rec['requires_review'] = len(policy_result.violations) > 0

                filtered_recommendations.append(filtered_rec)

        return filtered_recommendations

    def get_policy_summary(self, recommendations: List[Dict]) -> Dict:
        """Generate summary of policy enforcement results."""
        total_recs = len(recommendations)
        requires_review = sum(1 for r in recommendations if r.get('requires_review', False))

        violation_counts = {}
        for rec in recommendations:
            for violation in rec.get('policy_violations', []):
                violation_counts[violation] = violation_counts.get(violation, 0) + 1

        return {
            'total_recommendations': total_recs,
            'requires_librarian_review': requires_review,
            'auto_approved': total_recs - requires_review,
            'violation_counts': violation_counts,
            'review_rate': requires_review / total_recs if total_recs > 0 else 0
        }


def main():
    """Test policy guardrails with sample recommendations."""
    from data_pipeline import DataPipeline
    from collaborative_filtering import CollaborativeRecommender

    # Load data
    pipeline = DataPipeline()
    books_df, students_df, checkouts_df, interactions_df = pipeline.run_pipeline()

    # Get test student
    test_student = students_df.iloc[0]
    student_id = test_student['student_id']
    student_grade = test_student['grade']

    # Get some recommendations to test
    collab_recommender = CollaborativeRecommender()
    collab_recommender.fit(pipeline.interaction_matrix)

    raw_recommendations = collab_recommender.recommend_for_user(
        student_id, books_df, n_recommendations=10
    )

    # Initialize policy guardrails
    policy = PolicyGuardrails()

    # Get student reading history
    student_history = checkouts_df[checkouts_df['student_id'] == student_id]['book_id'].tolist()

    print(f"🔒 Testing policy guardrails for {student_id} (Grade {student_grade})")
    print(f"   Student has read {len(student_history)} books")

    # Filter recommendations through policy
    filtered_recommendations = policy.filter_recommendations(
        raw_recommendations, student_grade, student_history, books_df
    )

    print(f"\n📋 Policy Results:")
    print(f"   Original recommendations: {len(raw_recommendations)}")
    print(f"   After policy filtering: {len(filtered_recommendations)}")

    # Show policy summary
    summary = policy.get_policy_summary(filtered_recommendations)
    print(f"\n📊 Policy Summary:")
    print(f"   Auto-approved: {summary['auto_approved']}")
    print(f"   Requires review: {summary['requires_librarian_review']}")
    print(f"   Review rate: {summary['review_rate']:.1%}")

    if summary['violation_counts']:
        print(f"   Violation breakdown:")
        for violation, count in summary['violation_counts'].items():
            print(f"     {violation}: {count}")

    # Show sample recommendations with policy info
    print(f"\n📚 Sample Filtered Recommendations:")
    for i, rec in enumerate(filtered_recommendations[:5], 1):
        status = "🟡 NEEDS REVIEW" if rec['requires_review'] else "✅ AUTO-APPROVED"
        print(f"   {i}. {rec['title']} - {status}")
        print(f"      Confidence: {rec['confidence']:.3f}")
        if rec['policy_explanation'] != "passes all policy checks":
            print(f"      Policy notes: {rec['policy_explanation']}")


if __name__ == "__main__":
    main()