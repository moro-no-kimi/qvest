from __future__ import annotations

from dataclasses import dataclass

import pandas as pd


@dataclass(frozen=True)
class DemoData:
    schools: pd.DataFrame
    students: pd.DataFrame
    catalog: pd.DataFrame
    checkouts: pd.DataFrame


def create_demo_data() -> DemoData:
    schools = pd.DataFrame(
        [
            {"school_id": "SCH-01", "school_name": "Bear Creek MS"},
            {"school_id": "SCH-02", "school_name": "Holcomb Bridge MS"},
            {"school_id": "SCH-03", "school_name": "Sandtown MS"},
            {"school_id": "SCH-04", "school_name": "Northwestern MS"},
        ]
    )

    students = pd.DataFrame(
        [
            {"student_id": "STU-001", "student_name": "Avery Brooks", "school_id": "SCH-01", "grade": 7, "homeroom": "7A", "history_segment": "dense"},
            {"student_id": "STU-002", "student_name": "Miles Carter", "school_id": "SCH-01", "grade": 7, "homeroom": "7A", "history_segment": "dense"},
            {"student_id": "STU-003", "student_name": "Maya Patel", "school_id": "SCH-01", "grade": 7, "homeroom": "7B", "history_segment": "dense"},
            {"student_id": "STU-004", "student_name": "Jonah Kim", "school_id": "SCH-01", "grade": 6, "homeroom": "6A", "history_segment": "sparse"},
            {"student_id": "STU-005", "student_name": "Nia Johnson", "school_id": "SCH-02", "grade": 8, "homeroom": "8A", "history_segment": "dense"},
            {"student_id": "STU-006", "student_name": "Sofia Martinez", "school_id": "SCH-02", "grade": 8, "homeroom": "8A", "history_segment": "dense"},
            {"student_id": "STU-007", "student_name": "Elijah Scott", "school_id": "SCH-02", "grade": 7, "homeroom": "7C", "history_segment": "moderate"},
            {"student_id": "STU-008", "student_name": "Ruby Nguyen", "school_id": "SCH-02", "grade": 6, "homeroom": "6B", "history_segment": "sparse"},
            {"student_id": "STU-009", "student_name": "Zoe Allen", "school_id": "SCH-03", "grade": 7, "homeroom": "7D", "history_segment": "dense"},
            {"student_id": "STU-010", "student_name": "Jackson Price", "school_id": "SCH-03", "grade": 7, "homeroom": "7D", "history_segment": "dense"},
            {"student_id": "STU-011", "student_name": "Camila Green", "school_id": "SCH-03", "grade": 6, "homeroom": "6C", "history_segment": "moderate"},
            {"student_id": "STU-012", "student_name": "Liam Thompson", "school_id": "SCH-04", "grade": 8, "homeroom": "8C", "history_segment": "dense"},
            {"student_id": "STU-013", "student_name": "Emma Walker", "school_id": "SCH-04", "grade": 8, "homeroom": "8C", "history_segment": "dense"},
            {"student_id": "STU-014", "student_name": "Noah Robinson", "school_id": "SCH-04", "grade": 7, "homeroom": "7E", "history_segment": "moderate"},
            {"student_id": "STU-015", "student_name": "Harper Lewis", "school_id": "SCH-04", "grade": 6, "homeroom": "6D", "history_segment": "sparse"},
        ]
    )

    catalog = pd.DataFrame(
        [
            {"book_id": "BK-001", "title": "The Giver", "author": "Lois Lowry", "genre": "Dystopian", "series": "The Giver Quartet", "grade_min": 6, "grade_max": 8, "district_suitable": True, "availability": "Available now", "description": "A reflective dystopian novel about memory, choice, and a tightly controlled community."},
            {"book_id": "BK-002", "title": "Among the Hidden", "author": "Margaret Peterson Haddix", "genre": "Dystopian", "series": "Shadow Children", "grade_min": 6, "grade_max": 8, "district_suitable": True, "availability": "2 copies at your school", "description": "A suspenseful dystopian story about a hidden third child learning to resist unfair rules."},
            {"book_id": "BK-003", "title": "Scythe", "author": "Neal Shusterman", "genre": "Dystopian", "series": "Arc of a Scythe", "grade_min": 7, "grade_max": 8, "district_suitable": True, "availability": "Available across district", "description": "Teens train inside a future society where mortality has been conquered and moral choices still matter."},
            {"book_id": "BK-004", "title": "The Hunger Games", "author": "Suzanne Collins", "genre": "Dystopian", "series": "The Hunger Games", "grade_min": 7, "grade_max": 8, "district_suitable": True, "availability": "1 copy on hold", "description": "A fast-paced survival story about courage, spectacle, and resisting an unjust system."},
            {"book_id": "BK-005", "title": "Amari and the Night Brothers", "author": "B. B. Alston", "genre": "Fantasy", "series": "Supernatural Investigations", "grade_min": 6, "grade_max": 8, "district_suitable": True, "availability": "Available now", "description": "A magical mystery about a determined girl uncovering a hidden world and finding where she belongs."},
            {"book_id": "BK-006", "title": "Tristan Strong Punches a Hole in the Sky", "author": "Kwame Mbalia", "genre": "Fantasy", "series": "Tristan Strong", "grade_min": 6, "grade_max": 8, "district_suitable": True, "availability": "Available now", "description": "A mythic adventure with folklore, humor, and a hero learning to carry grief and courage together."},
            {"book_id": "BK-007", "title": "Front Desk", "author": "Kelly Yang", "genre": "Realistic Fiction", "series": "Front Desk", "grade_min": 6, "grade_max": 8, "district_suitable": True, "availability": "3 copies at your school", "description": "A heartfelt story about family, persistence, and standing up for other people."},
            {"book_id": "BK-008", "title": "New Kid", "author": "Jerry Craft", "genre": "Graphic Novel", "series": "New Kid", "grade_min": 6, "grade_max": 8, "district_suitable": True, "availability": "Available now", "description": "A graphic novel about friendship, fitting in, and navigating a new school environment."},
            {"book_id": "BK-009", "title": "Ghost", "author": "Jason Reynolds", "genre": "Sports", "series": "Track", "grade_min": 6, "grade_max": 8, "district_suitable": True, "availability": "Available now", "description": "A fast, character-driven sports novel about speed, second chances, and building trust."},
            {"book_id": "BK-010", "title": "The Crossover", "author": "Kwame Alexander", "genre": "Sports", "series": "The Crossover", "grade_min": 6, "grade_max": 8, "district_suitable": True, "availability": "Available now", "description": "A basketball novel in verse about family, pressure, and the rhythm of growing up."},
            {"book_id": "BK-011", "title": "One of Us Is Lying", "author": "Karen M. McManus", "genre": "Mystery", "series": "One of Us Is Lying", "grade_min": 7, "grade_max": 8, "district_suitable": True, "availability": "Available across district", "description": "A twisty mystery where students untangle secrets after a classmate dies during detention."},
            {"book_id": "BK-012", "title": "The Parker Inheritance", "author": "Varian Johnson", "genre": "Mystery", "series": "Standalone", "grade_min": 6, "grade_max": 8, "district_suitable": True, "availability": "Available now", "description": "A thoughtful mystery about puzzles, history, and two kids following clues hidden inside their town."},
            {"book_id": "BK-013", "title": "Hidden Figures Young Readers Edition", "author": "Margot Lee Shetterly", "genre": "Nonfiction", "series": "Standalone", "grade_min": 6, "grade_max": 8, "district_suitable": True, "availability": "Available now", "description": "The inspiring true story of Black women mathematicians whose work shaped the space race."},
            {"book_id": "BK-014", "title": "The Wild Robot", "author": "Peter Brown", "genre": "Science Fiction", "series": "The Wild Robot", "grade_min": 6, "grade_max": 7, "district_suitable": True, "availability": "Available now", "description": "A gentle science-fiction adventure about a robot learning community, kindness, and survival."},
            {"book_id": "BK-015", "title": "Percy Jackson and the Lightning Thief", "author": "Rick Riordan", "genre": "Fantasy", "series": "Percy Jackson", "grade_min": 6, "grade_max": 7, "district_suitable": True, "availability": "2 copies at your school", "description": "A myth-heavy adventure with humor, friendship, and a hero discovering hidden strengths."},
            {"book_id": "BK-016", "title": "Refugee", "author": "Alan Gratz", "genre": "Historical Fiction", "series": "Standalone", "grade_min": 6, "grade_max": 8, "district_suitable": True, "availability": "Available now", "description": "Three stories of young people forced to flee danger, linked by courage and survival."},
            {"book_id": "BK-017", "title": "Brown Girl Dreaming", "author": "Jacqueline Woodson", "genre": "Memoir", "series": "Standalone", "grade_min": 6, "grade_max": 8, "district_suitable": True, "availability": "Available now", "description": "A memoir in verse about voice, family, and finding language to describe the world."},
            {"book_id": "BK-018", "title": "A Good Girl's Guide to Murder", "author": "Holly Jackson", "genre": "Mystery", "series": "A Good Girl's Guide to Murder", "grade_min": 9, "grade_max": 12, "district_suitable": False, "availability": "Not displayed to middle school students", "description": "A mature mystery title included only to demonstrate policy guardrails during the demo."},
        ]
    )

    checkout_rows = [
        ("STU-001", "BK-001", "2025-08-18"),
        ("STU-001", "BK-002", "2025-08-29"),
        ("STU-001", "BK-003", "2025-09-11"),
        ("STU-001", "BK-016", "2025-09-25"),
        ("STU-002", "BK-001", "2025-08-20"),
        ("STU-002", "BK-002", "2025-09-02"),
        ("STU-002", "BK-003", "2025-09-18"),
        ("STU-002", "BK-018", "2025-10-03"),
        ("STU-003", "BK-001", "2025-08-22"),
        ("STU-003", "BK-002", "2025-09-05"),
        ("STU-004", "BK-014", "2025-09-09"),
        ("STU-005", "BK-011", "2025-08-16"),
        ("STU-005", "BK-012", "2025-08-31"),
        ("STU-005", "BK-018", "2025-09-17"),
        ("STU-006", "BK-011", "2025-08-19"),
        ("STU-006", "BK-012", "2025-09-03"),
        ("STU-006", "BK-013", "2025-09-19"),
        ("STU-007", "BK-009", "2025-09-01"),
        ("STU-007", "BK-010", "2025-09-15"),
        ("STU-008", "BK-008", "2025-09-12"),
        ("STU-009", "BK-005", "2025-08-18"),
        ("STU-009", "BK-006", "2025-08-30"),
        ("STU-009", "BK-015", "2025-09-14"),
        ("STU-010", "BK-005", "2025-08-22"),
        ("STU-010", "BK-006", "2025-09-07"),
        ("STU-010", "BK-015", "2025-09-23"),
        ("STU-011", "BK-007", "2025-09-03"),
        ("STU-011", "BK-017", "2025-09-20"),
        ("STU-012", "BK-011", "2025-08-15"),
        ("STU-012", "BK-012", "2025-08-28"),
        ("STU-012", "BK-013", "2025-09-10"),
        ("STU-012", "BK-016", "2025-09-24"),
        ("STU-013", "BK-001", "2025-08-17"),
        ("STU-013", "BK-003", "2025-09-01"),
        ("STU-013", "BK-004", "2025-09-16"),
        ("STU-014", "BK-007", "2025-09-05"),
        ("STU-014", "BK-008", "2025-09-22"),
        ("STU-015", "BK-013", "2025-09-08"),
    ]
    checkouts = pd.DataFrame(checkout_rows, columns=["student_id", "book_id", "checkout_date"])
    checkouts["checkout_date"] = pd.to_datetime(checkouts["checkout_date"])

    return DemoData(
        schools=schools,
        students=students.merge(schools, on="school_id", how="left"),
        catalog=catalog,
        checkouts=checkouts,
    )