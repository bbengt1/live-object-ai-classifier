"""
Feedback Analysis Service - Story P4-5.4

Analyzes user feedback corrections to identify patterns and generate
prompt improvement suggestions for the AI service.

Features:
- Pattern extraction from correction texts
- Categorization of feedback (object, action, detail, context)
- Minimum sample threshold enforcement (10 samples)
- Per-camera insights generation
- Confidence scoring for suggestions
"""

import logging
import re
from collections import Counter
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import func, and_

from app.models.event_feedback import EventFeedback
from app.models.camera import Camera

logger = logging.getLogger(__name__)

# Minimum feedback samples required before generating suggestions
MIN_SAMPLES_FOR_SUGGESTIONS = 10

# Accuracy threshold below which camera-specific suggestions are generated
LOW_ACCURACY_THRESHOLD = 70.0


class CorrectionCategory(str, Enum):
    """Categories for classifying user corrections."""
    OBJECT_MISID = "object_misidentification"  # Wrong object identified
    ACTION_WRONG = "action_wrong"  # Incorrect action description
    MISSING_DETAIL = "missing_detail"  # Important detail omitted
    CONTEXT_ERROR = "context_error"  # Wrong context/location/time
    GENERAL = "general"  # Other corrections


@dataclass
class PromptSuggestion:
    """A suggested improvement to the AI description prompt."""
    id: str
    category: CorrectionCategory
    suggestion_text: str
    example_corrections: List[str]
    confidence: float  # 0.0 to 1.0
    impact_score: float  # 0.0 to 1.0 based on frequency
    camera_id: Optional[str] = None  # If camera-specific


@dataclass
class CameraInsight:
    """Per-camera analysis results."""
    camera_id: str
    camera_name: str
    accuracy_rate: float
    sample_count: int
    top_categories: List[CorrectionCategory]
    suggestions: List[PromptSuggestion] = field(default_factory=list)


@dataclass
class PromptInsightsResult:
    """Complete result of feedback analysis."""
    suggestions: List[PromptSuggestion]
    camera_insights: Dict[str, CameraInsight]
    sample_count: int
    confidence: float
    min_samples_met: bool


# Keyword patterns for categorizing corrections
CATEGORY_PATTERNS = {
    CorrectionCategory.OBJECT_MISID: [
        r"(it was|that's|that is|this is) (a |an |the )?(\w+),? not (a |an |the )?(\w+)",
        r"(not (a |an |the )?|wasn't (a |an |the )?|isn't (a |an |the )?)(\w+)",
        r"(actually|really) (a |an |the )?(\w+)",
        r"(mis)?identified as",
        r"(wrong|incorrect) (object|animal|vehicle|person|thing)",
        r"(cat|dog|person|car|truck|package|animal|bird)",
    ],
    CorrectionCategory.ACTION_WRONG: [
        r"(was|were) (leaving|arriving|entering|exiting|standing|sitting|walking|running)",
        r"(not |wasn't |weren't )(leaving|arriving|entering|exiting|standing|sitting|walking|running)",
        r"(didn't|did not) (leave|arrive|enter|exit|stand|sit|walk|run|move|come|go)",
        r"(wrong|incorrect) (action|movement|direction)",
        r"(going|coming|moving) (toward|away|left|right)",
    ],
    CorrectionCategory.MISSING_DETAIL: [
        r"(didn't mention|missed|omitted|forgot|left out)",
        r"(should have|should've) (mentioned|noted|included|said)",
        r"(also|there was also|and also)",
        r"(more than one|multiple|several|two|three)",
        r"(package|delivery|carrying|holding|had)",
    ],
    CorrectionCategory.CONTEXT_ERROR: [
        r"(this is|that's|that is) (my|our|the) (regular|usual|daily)",
        r"(mailman|mail carrier|delivery|neighbor|family|friend)",
        r"(every|always|usually|normally) (day|week|morning|afternoon)",
        r"(wrong|incorrect) (time|location|place|camera)",
        r"(known|familiar|recognized) (person|visitor|vehicle)",
    ],
}


class FeedbackAnalysisService:
    """Service for analyzing feedback and generating prompt suggestions."""

    def __init__(self, db: Session):
        self.db = db

    def analyze_correction_patterns(
        self,
        camera_id: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> PromptInsightsResult:
        """
        Analyze feedback corrections to identify patterns and generate suggestions.

        Args:
            camera_id: Optional filter for specific camera
            start_date: Optional start date filter
            end_date: Optional end date filter

        Returns:
            PromptInsightsResult with suggestions and camera insights
        """
        # Build query for feedback with corrections
        query = self.db.query(EventFeedback).filter(
            EventFeedback.correction.isnot(None),
            EventFeedback.correction != ''
        )

        if camera_id:
            query = query.filter(EventFeedback.camera_id == camera_id)

        corrections = query.all()
        sample_count = len(corrections)

        logger.info(f"Analyzing {sample_count} feedback corrections for prompt insights")

        # Check minimum samples threshold
        if sample_count < MIN_SAMPLES_FOR_SUGGESTIONS:
            logger.info(
                f"Insufficient samples ({sample_count}/{MIN_SAMPLES_FOR_SUGGESTIONS}) "
                "for generating suggestions"
            )
            return PromptInsightsResult(
                suggestions=[],
                camera_insights={},
                sample_count=sample_count,
                confidence=0.0,
                min_samples_met=False
            )

        # Categorize all corrections
        categorized = self._categorize_corrections(corrections)

        # Generate suggestions from patterns
        suggestions = self._generate_suggestions(categorized, sample_count)

        # Generate per-camera insights
        camera_insights = self._generate_camera_insights(corrections)

        # Calculate overall confidence based on sample size and consistency
        confidence = self._calculate_confidence(sample_count, categorized)

        return PromptInsightsResult(
            suggestions=suggestions,
            camera_insights=camera_insights,
            sample_count=sample_count,
            confidence=confidence,
            min_samples_met=True
        )

    def categorize_feedback(self, correction_text: str) -> CorrectionCategory:
        """
        Classify a single correction into a category.

        Args:
            correction_text: The user's correction text

        Returns:
            CorrectionCategory enum value
        """
        if not correction_text:
            return CorrectionCategory.GENERAL

        text_lower = correction_text.lower().strip()

        # Check each category's patterns
        for category, patterns in CATEGORY_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, text_lower, re.IGNORECASE):
                    return category

        return CorrectionCategory.GENERAL

    def _categorize_corrections(
        self, corrections: List[EventFeedback]
    ) -> Dict[CorrectionCategory, List[str]]:
        """Group corrections by category."""
        categorized: Dict[CorrectionCategory, List[str]] = {
            cat: [] for cat in CorrectionCategory
        }

        for feedback in corrections:
            category = self.categorize_feedback(feedback.correction)
            categorized[category].append(feedback.correction)

        return categorized

    def _generate_suggestions(
        self,
        categorized: Dict[CorrectionCategory, List[str]],
        total_count: int
    ) -> List[PromptSuggestion]:
        """Generate prompt improvement suggestions from categorized corrections."""
        suggestions = []
        suggestion_id = 0

        for category, correction_texts in categorized.items():
            if not correction_texts or category == CorrectionCategory.GENERAL:
                continue

            count = len(correction_texts)
            frequency = count / total_count

            # Only suggest if category has significant representation (>5%)
            if frequency < 0.05:
                continue

            suggestion = self._create_suggestion_for_category(
                category=category,
                corrections=correction_texts,
                frequency=frequency,
                suggestion_id=f"sug_{suggestion_id}"
            )

            if suggestion:
                suggestions.append(suggestion)
                suggestion_id += 1

        # Sort by impact score (most impactful first)
        suggestions.sort(key=lambda s: s.impact_score, reverse=True)

        return suggestions

    def _create_suggestion_for_category(
        self,
        category: CorrectionCategory,
        corrections: List[str],
        frequency: float,
        suggestion_id: str
    ) -> Optional[PromptSuggestion]:
        """Create a specific suggestion based on category and corrections."""
        # Extract common themes from corrections
        examples = corrections[:5]  # Top 5 examples

        suggestion_templates = {
            CorrectionCategory.OBJECT_MISID: (
                "Add instruction: 'Be precise when identifying objects. "
                "Distinguish between similar items like cats vs dogs, "
                "packages vs bags. If uncertain, describe physical characteristics.'"
            ),
            CorrectionCategory.ACTION_WRONG: (
                "Add instruction: 'Focus on the direction of movement. "
                "Clearly state if subjects are arriving/leaving, entering/exiting. "
                "Describe the complete action sequence from start to end.'"
            ),
            CorrectionCategory.MISSING_DETAIL: (
                "Add instruction: 'Include ALL visible details: "
                "items being carried, number of people/vehicles, "
                "what they are holding or interacting with. Don't omit secondary elements.'"
            ),
            CorrectionCategory.CONTEXT_ERROR: (
                "Add instruction: 'Avoid assumptions about identity or context. "
                "Describe what is visible without inferring relationships. "
                "Use neutral language like \"a person\" rather than assuming roles.'"
            ),
        }

        suggestion_text = suggestion_templates.get(category)
        if not suggestion_text:
            return None

        # Calculate confidence based on consistency of corrections
        confidence = min(0.95, 0.5 + (frequency * 0.5))

        return PromptSuggestion(
            id=suggestion_id,
            category=category,
            suggestion_text=suggestion_text,
            example_corrections=examples,
            confidence=confidence,
            impact_score=frequency
        )

    def _generate_camera_insights(
        self, corrections: List[EventFeedback]
    ) -> Dict[str, CameraInsight]:
        """Generate per-camera analysis insights."""
        insights = {}

        # Group corrections by camera
        by_camera: Dict[str, List[EventFeedback]] = {}
        for feedback in corrections:
            cam_id = feedback.camera_id
            if cam_id:
                if cam_id not in by_camera:
                    by_camera[cam_id] = []
                by_camera[cam_id].append(feedback)

        # For each camera with corrections, generate insights
        for camera_id, camera_corrections in by_camera.items():
            # Get camera details
            camera = self.db.query(Camera).filter(Camera.id == camera_id).first()
            camera_name = camera.name if camera else f"Camera {camera_id[:8]}"

            # Calculate accuracy for this camera (from all feedback, not just corrections)
            total_feedback = self.db.query(EventFeedback).filter(
                EventFeedback.camera_id == camera_id
            ).count()

            helpful_count = self.db.query(EventFeedback).filter(
                EventFeedback.camera_id == camera_id,
                EventFeedback.rating == 'helpful'
            ).count()

            accuracy_rate = (helpful_count / total_feedback * 100) if total_feedback > 0 else 0.0

            # Categorize this camera's corrections
            categories = [
                self.categorize_feedback(f.correction) for f in camera_corrections
            ]
            category_counts = Counter(categories)
            top_categories = [
                cat for cat, _ in category_counts.most_common(3)
                if cat != CorrectionCategory.GENERAL
            ]

            # Generate camera-specific suggestions if accuracy is low
            camera_suggestions = []
            if accuracy_rate < LOW_ACCURACY_THRESHOLD and len(camera_corrections) >= 5:
                categorized = self._categorize_corrections(camera_corrections)
                camera_suggestions = self._generate_suggestions(
                    categorized, len(camera_corrections)
                )
                # Mark as camera-specific
                for sug in camera_suggestions:
                    sug.camera_id = camera_id

            insights[camera_id] = CameraInsight(
                camera_id=camera_id,
                camera_name=camera_name,
                accuracy_rate=round(accuracy_rate, 1),
                sample_count=len(camera_corrections),
                top_categories=top_categories,
                suggestions=camera_suggestions
            )

        return insights

    def _calculate_confidence(
        self,
        sample_count: int,
        categorized: Dict[CorrectionCategory, List[str]]
    ) -> float:
        """
        Calculate overall confidence in the analysis.

        Based on:
        - Sample size (more = higher confidence)
        - Distribution across categories (less spread = higher confidence)
        """
        # Base confidence from sample size (caps at 0.7 with 50+ samples)
        size_factor = min(0.7, sample_count / 50)

        # Distribution factor (are corrections concentrated or spread?)
        total = sum(len(v) for v in categorized.values())
        if total == 0:
            return 0.0

        # Calculate entropy-like measure
        max_category_ratio = max(len(v) / total for v in categorized.values())
        distribution_factor = max_category_ratio * 0.3

        confidence = min(0.95, size_factor + distribution_factor)
        return round(confidence, 2)


def get_feedback_analysis_service(db: Session) -> FeedbackAnalysisService:
    """Factory function for FeedbackAnalysisService."""
    return FeedbackAnalysisService(db)
