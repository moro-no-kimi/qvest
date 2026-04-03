# Qvest — Role & Data Hierarchy

A reference document for how users, data entities, and relationships are structured in the system.

---

## User Roles

The system has four role-scoped surfaces. Role assignment derives from **Microsoft Entra ID** security groups — not from any local user management system. All users authenticate via `@fcstu.org` accounts through ClassLink SSO (`launchpad.classlink.com/fcs`).

```
District Leader (district_admin)
│
└─── School
      │
      ├─── Principal (principal)
      │
      ├─── Librarian (librarian)
      │
      └─── Student (student)
```

| Role | Entra ID Claim | Entry Point | Surface |
|---|---|---|---|
| Student | `student` group | ClassLink tile | Recommendation page |
| Librarian | `librarian` group | ClassLink tile | Review workspace |
| Principal | `principal` group | ClassLink tile | School oversight dashboard |
| District Leader | `district_admin` group (explicit assignment required) | ClassLink tile | District analytics dashboard |

---

## Core Entities

### Student
- Identified by Fulton lunch number (`ID#@fcstu.org`)
- Belongs to one **School**, one **Homeroom**, one **Grade** (6–8)
- Has a **checkout history** in Destiny (source of truth for borrowing behavior)
- Receives one or more **Recommendations** per nightly batch

Key fields: `id`, `name`, `grade`, `homeroom`, `school`, `checkout_count`

---

### Book
- Catalog record sourced from **Destiny Library Manager** export
- Scoped to a **grade band** and subject to district suitability constraints
- Availability (copies available / total copies) is live from Destiny

Key fields: `id`, `title`, `author`, `genre`, `grade_band`, `available`, `copies_available`, `total_copies`

---

### Recommendation
- Generated nightly by the hybrid engine (collaborative filtering + content similarity)
- Links one **Student** → one **Book**, ranked by `position`
- Carries a `confidence` score (0–1) and `signals` array explaining its provenance
- LLM adds a plain-English `explanation` and `because_you_liked` title list
- Progresses through a **status lifecycle** managed by librarians

Key fields: `id`, `student_id`, `book_id`, `position`, `confidence`, `explanation`, `because_you_liked`, `signals`, `status`

#### Recommendation Status Lifecycle

```
[nightly batch] → pending
                     │
        ┌────────────┼────────────┬────────────┐
        ▼            ▼            ▼            ▼
   auto-published  approved     pinned     suppressed
   (no librarian  (librarian   (librarian  (librarian
    action taken)  approved)    featured)   removed)
```

- **auto-published**: shown to student without explicit librarian review (default if no action within threshold)
- **approved**: librarian explicitly approved
- **pinned**: librarian featured at top of student list
- **suppressed**: hidden from student; not shown

#### Recommendation Signals

| Signal | Meaning |
|---|---|
| `collaborative` | Borrowed by students with similar reading patterns |
| `content` | Matches genre/theme of books the student has read |
| `popularity` | Trending among grade/school peers |
| `series` | Next book in a series the student has started |

---

### Librarian Action
- Records every explicit decision a librarian makes on a **Recommendation**
- Immutable audit trail (append-only)
- Links to both the **Recommendation** and the **Student**

Key fields: `id`, `recommendation_id`, `student_id`, `librarian_name`, `action`, `note`, `created_at`

#### Action Types

| Action | Effect on Recommendation Status |
|---|---|
| `approved` | → `approved` |
| `pinned` | → `pinned` |
| `suppressed` | → `suppressed` |
| `replaced` | Suppresses current; a new recommendation takes its slot |

---

### School Metrics
- Aggregate rollup per school, updated on each nightly batch
- Used by Principal and District Leader dashboards
- No student PII; school-level aggregates only

Key fields: `school`, `lift_percent`, `current_checkouts`, `pre_baseline_checkouts`, `students_reached`, `total_students`, `approval_rate`, `override_rate`

---

### Weekly Trends
- District-wide time series: one row per week
- Tracks recommendation pipeline health vs. student checkout behavior

Key fields: `week`, `recommendations_generated`, `recommendations_exposed`, `checkouts_per_student`, `baseline`

---

## Relationship Map

```
District
  └── School (19 middle schools in pilot)
        ├── Principal (1 per school) ──────────────── read-only view
        ├── Librarian (1–2 per school)
        │     └── LibrarianAction ──────────────────┐
        └── Student (n per school)                  │
              ├── checkout_history (in Destiny)      │
              └── Recommendation (1–5 per student)   │
                    ├── Book                         │
                    └── ◄── LibrarianAction ─────────┘
```

---

## Data Sources & Ownership

| Data | System of Record | How it enters Qvest |
|---|---|---|
| Student identity & roles | Microsoft Entra ID | JWT claims on login |
| Book catalog & availability | Destiny Library Manager | Nightly export / approved API |
| Checkout history | Destiny Library Manager | Nightly export |
| School roster | Destiny / Entra ID | Nightly export |
| Recommendations | Qvest engine | Generated nightly, stored in Supabase (pilot) / PostgreSQL (production) |
| Librarian actions | Qvest | Written at review time |
| School & district metrics | Qvest | Derived from checkouts + recommendation events |

---

## What Roles Can See

| Entity | Student | Librarian | Principal | District Leader |
|---|---|---|---|---|
| Own recommendations | ✅ (approved + pinned + auto-published) | ✅ (all statuses) | ❌ | ❌ |
| Other students' recommendations | ❌ | ✅ (all homerooms in their school) | ✅ read-only (their school) | ❌ |
| Librarian actions | ❌ | ✅ (own actions) | ✅ read-only (their school) | ❌ |
| School metrics | ❌ | ✅ (own school) | ✅ (own school) | ✅ (all pilot schools) |
| Weekly trends | ❌ | ❌ | ❌ | ✅ |
| Book catalog | ✅ (grade-band filtered) | ✅ | ❌ | ❌ |

---

## Decisions

| Question | Answer |
|---|---|
| Librarian homeroom scope | Librarians see **all recommendations across all homerooms** in their school, not scoped to a single homeroom |
| District leader cardinality | **Single central role** for MVP — one district dashboard, no per-region/cluster splits |
| Librarian → school assignment | Stored as **Entra ID group membership** — no local mapping table needed |
| Principal role | **Included in MVP** — read-only oversight surface scoped to their school; assigned via Entra ID group |


---

## Core Entities

### Student
- Identified by Fulton lunch number (`ID#@fcstu.org`)
- Belongs to one **School**, one **Homeroom**, one **Grade** (6–8)
- Has a **checkout history** in Destiny (source of truth for borrowing behavior)
- Receives one or more **Recommendations** per nightly batch

Key fields: `id`, `name`, `grade`, `homeroom`, `school`, `checkout_count`

---

### Book
- Catalog record sourced from **Destiny Library Manager** export
- Scoped to a **grade band** and subject to district suitability constraints
- Availability (copies available / total copies) is live from Destiny

Key fields: `id`, `title`, `author`, `genre`, `grade_band`, `available`, `copies_available`, `total_copies`

---

### Recommendation
- Generated nightly by the hybrid engine (collaborative filtering + content similarity)
- Links one **Student** → one **Book**, ranked by `position`
- Carries a `confidence` score (0–1) and `signals` array explaining its provenance
- LLM adds a plain-English `explanation` and `because_you_liked` title list
- Progresses through a **status lifecycle** managed by librarians

Key fields: `id`, `student_id`, `book_id`, `position`, `confidence`, `explanation`, `because_you_liked`, `signals`, `status`

#### Recommendation Status Lifecycle

```
[nightly batch] → pending
                     │
        ┌────────────┼────────────┬────────────┐
        ▼            ▼            ▼            ▼
   auto-published  approved     pinned     suppressed
   (no librarian  (librarian   (librarian  (librarian
    action taken)  approved)    featured)   removed)
```

- **auto-published**: shown to student without explicit librarian review (default if no action within threshold)
- **approved**: librarian explicitly approved
- **pinned**: librarian featured at top of student list
- **suppressed**: hidden from student; not shown

#### Recommendation Signals

| Signal | Meaning |
|---|---|
| `collaborative` | Borrowed by students with similar reading patterns |
| `content` | Matches genre/theme of books the student has read |
| `popularity` | Trending among grade/school peers |
| `series` | Next book in a series the student has started |

---

### Librarian Action
- Records every explicit decision a librarian makes on a **Recommendation**
- Immutable audit trail (append-only)
- Links to both the **Recommendation** and the **Student**

Key fields: `id`, `recommendation_id`, `student_id`, `librarian_name`, `action`, `note`, `created_at`

#### Action Types

| Action | Effect on Recommendation Status |
|---|---|
| `approved` | → `approved` |
| `pinned` | → `pinned` |
| `suppressed` | → `suppressed` |
| `replaced` | Suppresses current; a new recommendation takes its slot |

---

### School Metrics
- Aggregate rollup per school, updated on each nightly batch
- Used by District Leader dashboard
- No student PII; school-level aggregates only

Key fields: `school`, `lift_percent`, `current_checkouts`, `pre_baseline_checkouts`, `students_reached`, `total_students`, `approval_rate`, `override_rate`

---

### Weekly Trends
- District-wide time series: one row per week
- Tracks recommendation pipeline health vs. student checkout behavior

Key fields: `week`, `recommendations_generated`, `recommendations_exposed`, `checkouts_per_student`, `baseline`

---

## Relationship Map

```
District
  └── School (19 middle schools in pilot)
        ├── Librarian (1–2 per school)
        │     └── LibrarianAction ──────────────────┐
        └── Student (n per school)                  │
              ├── checkout_history (in Destiny)      │
              └── Recommendation (1–5 per student)   │
                    ├── Book                         │
                    └── ◄── LibrarianAction ─────────┘
```

---

## Data Sources & Ownership

| Data | System of Record | How it enters Qvest |
|---|---|---|
| Student identity & roles | Microsoft Entra ID | JWT claims on login |
| Book catalog & availability | Destiny Library Manager | Nightly export / approved API |
| Checkout history | Destiny Library Manager | Nightly export |
| School roster | Destiny / Entra ID | Nightly export |
| Recommendations | Qvest engine | Generated nightly, stored in Supabase (pilot) / PostgreSQL (production) |
| Librarian actions | Qvest | Written at review time |
| School & district metrics | Qvest | Derived from checkouts + recommendation events |

---

## What Roles Can See

| Entity | Student | Librarian | District Leader |
|---|---|---|---|
| Own recommendations | ✅ (approved + pinned + auto-published) | ✅ (all statuses) | ❌ |
| Other students' recommendations | ❌ | ✅ (all homerooms in their school) | ❌ |
| Librarian actions | ❌ | ✅ (own actions) | ❌ |
| School metrics | ❌ | ✅ (own school) | ✅ (all pilot schools) |
| Weekly trends | ❌ | ❌ | ✅ |
| Book catalog | ✅ (grade-band filtered) | ✅ | ❌ |

---

## Decisions

| Question | Answer |
|---|---|
| Librarian homeroom scope | Librarians see **all recommendations across all homerooms** in their school, not scoped to a single homeroom |
| District leader cardinality | **Single central role** for MVP — one district dashboard, no per-region/cluster splits |
| Librarian → school assignment | Stored as **Entra ID group membership** — no local mapping table needed |
| Principal role | **Included in MVP** — read-only oversight surface scoped to their school; assigned via Entra ID group |
