#!/usr/bin/env python3
"""
LLM-powered explanation generator for book recommendations.
Creates natural, student-friendly explanations.
"""

import pandas as pd
from typing import List, Dict, Optional
import random
import os
from dataclasses import dataclass


@dataclass
class ExplanationContext:
    """Context needed to generate a recommendation explanation."""
    recommended_book: Dict
    student_grade: int
    student_reading_history: List[Dict]
    recommendation_source: str
    similar_students_count: Optional[int] = None
    content_similarity_reason: Optional[str] = None


class LLMExplanationGenerator:
    """Generates natural language explanations for book recommendations."""

    def __init__(self, use_mock_llm: bool = True):
        """
        Initialize explanation generator.

        Args:
            use_mock_llm: If True, uses mock explanations for demo.
                         If False, uses real LLM API (requires API key).
        """
        self.use_mock_llm = use_mock_llm
        self.api_key = os.getenv('OPENAI_API_KEY') or os.getenv('ANTHROPIC_API_KEY')

        # Template explanations for different recommendation scenarios
        self.explanation_templates = {
            'collaborative': [
                "Students who enjoyed {similar_books} also loved this book.",
                "Other readers with similar tastes highly recommend this one.",
                "{similar_count} students who like books similar to yours also checked this out.",
                "Based on what students like you are reading, this could be your next favorite."
            ],
            'content_based': [
                "Since you enjoyed {previous_book}, you'll likely love this {similarity_reason}.",
                "This book has the same {common_elements} that made {previous_book} so engaging.",
                "If you liked the {genre} elements in {previous_book}, this is perfect for you.",
                "This book explores similar themes to {previous_book} in an exciting new way."
            ],
            'series': [
                "This is the next book in the {series_name} series - continue the adventure!",
                "Keep the story going with this next book in your favorite series.",
                "You've been following this series - here's what happens next!"
            ],
            'genre_match': [
                "Another great {genre} book for your collection.",
                "Perfect if you're in the mood for more {genre} adventures.",
                "This {genre} story has the same exciting elements you love."
            ],
            'popular': [
                "This book is really popular right now - see what everyone's talking about!",
                "Lots of students at your school are loving this one.",
                "This is trending among {grade}th graders - don't miss out!"
            ],
            'cold_start': [
                "This book is perfect for someone just getting started with {genre}.",
                "Many students your age discovered their love of reading with this book.",
                "This is a great book to explore - it's helped many students find their reading passion."
            ]
        }

    def _mock_llm_explanation(self, context: ExplanationContext) -> str:
        """Generate mock explanation using templates (for demo purposes)."""

        book = context.recommended_book
        source = context.recommendation_source
        grade = context.student_grade

        # Choose template based on recommendation source
        if source == 'collaborative' and context.similar_students_count:
            template = random.choice(self.explanation_templates['collaborative'])
            similar_books = self._get_popular_titles_for_grade(grade)[:2]
            return template.format(
                similar_books=', '.join([f'"{title}"' for title in similar_books]),
                similar_count=context.similar_students_count
            )

        elif source == 'content_based' and context.student_reading_history:
            template = random.choice(self.explanation_templates['content_based'])
            prev_book = context.student_reading_history[0] if context.student_reading_history else {'title': 'books you\'ve read'}

            similarity_reasons = {
                'same_genre': f"same {book.get('genre', 'adventure')} style",
                'same_author': "same author's writing style",
                'similar_themes': "similar themes and characters",
                'reading_level': "perfect reading level for you"
            }

            reason_key = random.choice(list(similarity_reasons.keys()))
            similarity_reason = similarity_reasons[reason_key]

            common_elements = {
                'Fantasy': 'magical worlds and adventures',
                'Science Fiction': 'futuristic settings and technology',
                'Mystery': 'puzzles and detective work',
                'Adventure': 'exciting journeys and challenges',
                'Realistic Fiction': 'relatable characters and situations'
            }.get(book.get('genre', 'Adventure'), 'engaging storytelling')

            return template.format(
                previous_book=prev_book.get('title', 'your recent reads'),
                similarity_reason=similarity_reason,
                common_elements=common_elements,
                genre=book.get('genre', 'adventure').lower()
            )

        elif book.get('is_series', False):
            template = random.choice(self.explanation_templates['series'])
            return template.format(
                series_name=book.get('series_name', 'this')
            )

        elif book.get('checkout_count', 0) > 5:  # Popular book
            template = random.choice(self.explanation_templates['popular'])
            return template.format(grade=grade)

        else:  # Default genre match
            template = random.choice(self.explanation_templates['genre_match'])
            return template.format(genre=book.get('genre', 'adventure').lower())

    def _get_popular_titles_for_grade(self, grade: int) -> List[str]:
        """Get sample popular titles for explanations."""
        popular_by_grade = {
            6: ["Wonder", "Hatchet", "The Giver", "Bridge to Terabithia"],
            7: ["The Outsiders", "Holes", "Percy Jackson", "Number the Stars"],
            8: ["The Hunger Games", "The Maze Runner", "Divergent", "The Fault in Our Stars"]
        }
        return popular_by_grade.get(grade, ["popular books", "great stories"])

    def _real_llm_explanation(self, context: ExplanationContext) -> str:
        """Generate explanation using real LLM API."""
        if not self.api_key:
            return self._mock_llm_explanation(context)

        # This would implement the actual LLM API call
        # For now, fall back to mock explanation
        print("⚠️  Real LLM not implemented yet, using mock explanation")
        return self._mock_llm_explanation(context)

        # Example OpenAI implementation:
        # import openai
        #
        # prompt = self._build_llm_prompt(context)
        # response = openai.Completion.create(
        #     engine="text-davinci-003",
        #     prompt=prompt,
        #     max_tokens=100,
        #     temperature=0.7
        # )
        # return response.choices[0].text.strip()

    def _build_llm_prompt(self, context: ExplanationContext) -> str:
        """Build prompt for LLM API call."""
        book = context.recommended_book
        grade = context.student_grade

        # Build reading history context
        history_summary = ""
        if context.student_reading_history:
            recent_titles = [book['title'] for book in context.student_reading_history[:3]]
            history_summary = f"Recently read: {', '.join(recent_titles)}"

        prompt = f"""Write a friendly, encouraging explanation for why this book is recommended to a {grade}th grade student.

Book being recommended: "{book['title']}" by {book['author']} (Genre: {book.get('genre', 'Unknown')})
{history_summary}
Recommendation source: {context.recommendation_source}

The explanation should be:
- One or two sentences maximum
- Written in a warm, librarian-like tone
- Appropriate for middle school students
- Specific about why this book matches their interests
- Encouraging without being pushy

Explanation:"""

        return prompt

    def generate_explanation(self, context: ExplanationContext) -> str:
        """Generate natural language explanation for a book recommendation."""

        if self.use_mock_llm:
            explanation = self._mock_llm_explanation(context)
        else:
            explanation = self._real_llm_explanation(context)

        # Clean up explanation
        explanation = explanation.strip()
        if not explanation.endswith('.'):
            explanation += '.'

        return explanation

    def generate_batch_explanations(self, recommendations: List[Dict],
                                   student_grade: int,
                                   student_reading_history: List[Dict]) -> List[Dict]:
        """Generate explanations for multiple recommendations."""

        enhanced_recommendations = []

        for rec in recommendations:
            # Build context
            context = ExplanationContext(
                recommended_book=rec,
                student_grade=student_grade,
                student_reading_history=student_reading_history,
                recommendation_source=rec.get('recommendation_type', 'hybrid'),
                similar_students_count=len(rec.get('similar_users_who_liked', [])),
                content_similarity_reason=rec.get('content_similarity_reason')
            )

            # Generate explanation
            explanation = self.generate_explanation(context)

            # Add explanation to recommendation
            enhanced_rec = rec.copy()
            enhanced_rec['explanation'] = explanation
            enhanced_rec['explanation_generated'] = True

            enhanced_recommendations.append(enhanced_rec)

        return enhanced_recommendations

    def get_explanation_stats(self, explanations: List[str]) -> Dict:
        """Get statistics about generated explanations."""
        if not explanations:
            return {"count": 0}

        avg_length = sum(len(exp.split()) for exp in explanations) / len(explanations)

        return {
            "count": len(explanations),
            "avg_word_length": round(avg_length, 1),
            "shortest": min(len(exp.split()) for exp in explanations),
            "longest": max(len(exp.split()) for exp in explanations)
        }


def main():
    """Test explanation generation with sample recommendations."""
    from data_pipeline import DataPipeline
    from hybrid_recommender import HybridRecommender

    # Load data
    pipeline = DataPipeline()
    books_df, students_df, checkouts_df, interactions_df = pipeline.run_pipeline()

    # Get sample recommendations
    recommender = HybridRecommender()
    recommender.fit(books_df, students_df, pipeline.interaction_matrix)

    # Test with a student
    test_student = students_df.iloc[0]
    student_id = test_student['student_id']

    recommendations = recommender.recommend_for_user(student_id, n_recommendations=5)

    # Get student reading history
    student_checkouts = checkouts_df[checkouts_df['student_id'] == student_id]['book_id'].tolist()
    reading_history = []
    for book_id in student_checkouts[:3]:
        book_info = books_df[books_df['book_id'] == book_id]
        if len(book_info) > 0:
            reading_history.append({
                'title': book_info.iloc[0]['title'],
                'author': book_info.iloc[0]['author'],
                'genre': book_info.iloc[0]['genre']
            })

    print(f"🤖 Testing LLM explanation generator for {student_id}")
    print(f"   Grade: {test_student['grade']}, Reading history: {len(reading_history)} books")

    # Initialize explanation generator
    explainer = LLMExplanationGenerator(use_mock_llm=True)

    # Generate explanations
    enhanced_recommendations = explainer.generate_batch_explanations(
        recommendations,
        test_student['grade'],
        reading_history
    )

    print(f"\n📚 Recommendations with LLM explanations:")

    explanations = []
    for i, rec in enumerate(enhanced_recommendations, 1):
        explanations.append(rec['explanation'])
        print(f"\n   {i}. {rec['title']} by {rec['author']}")
        print(f"      Genre: {rec['genre']}")
        print(f"      💬 \"{rec['explanation']}\"")

    # Show explanation stats
    stats = explainer.get_explanation_stats(explanations)
    print(f"\n📊 Explanation Statistics:")
    print(f"   Generated: {stats['count']}")
    print(f"   Average length: {stats['avg_word_length']} words")
    print(f"   Range: {stats['shortest']}-{stats['longest']} words")


if __name__ == "__main__":
    main()