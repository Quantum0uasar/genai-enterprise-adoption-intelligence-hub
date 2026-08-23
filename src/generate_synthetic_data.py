"""
GenAI Enterprise Adoption Intelligence Hub
Synthetic data generator for the fictional "Northstar Financial Group" and its
internal GenAI assistant, "Northstar Assist."

IMPORTANT — SYNTHETIC DATA ONLY:
All organizations, employees, usage events, feedback, and metrics produced by
this script are entirely fictional and randomly generated. Nothing in this
file reads from, references, or is derived from any real company's data
(including RBC, TD, or any other financial institution). Do not treat any
output of this script as real, validated, or production data.

Run with:
    python src/generate_synthetic_data.py

Deterministic: a fixed random seed (SEED = 42) guarantees the same output on
every run, which is required for reproducibility of the rest of this project
(SQL, Power BI, Excel, and the written memo all assume these exact files).
"""

import os
import random
from datetime import datetime, timedelta

import numpy as np
import pandas as pd

# ---------------------------------------------------------------------------
# Reproducibility
# ---------------------------------------------------------------------------
SEED = 42
random.seed(SEED)
np.random.seed(SEED)
RNG = np.random.default_rng(SEED)

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW_DIR = os.path.join(PROJECT_ROOT, "data", "raw")

# ---------------------------------------------------------------------------
# Scale / scenario constants
# ---------------------------------------------------------------------------
N_USERS = 6000
N_WEEKS = 24
ROLLOUT_START = datetime(2026, 1, 5)  # Monday = Week 1, Day 1 of rollout
ROLLOUT_END = ROLLOUT_START + timedelta(weeks=N_WEEKS) - timedelta(days=1)

BUSINESS_UNITS = [
    "Retail Banking",
    "Commercial Banking",
    "Capital Markets",
    "Wealth Management",
    "Operations",
    "Technology",
    "Risk and Compliance",
    "Corporate Functions",
]

BU_WEIGHTS = {
    "Retail Banking": 0.28,
    "Operations": 0.18,
    "Technology": 0.12,
    "Commercial Banking": 0.12,
    "Capital Markets": 0.08,
    "Wealth Management": 0.08,
    "Risk and Compliance": 0.08,
    "Corporate Functions": 0.06,
}

ROLES = [
    "Analyst",
    "Associate",
    "Manager",
    "Director",
    "Operations Specialist",
    "Developer",
    "Risk Analyst",
    "Relationship Manager",
]

# Role mix within each business unit (weights sum to 1.0 per BU)
BU_ROLE_MIX = {
    "Retail Banking": {"Relationship Manager": 0.40, "Associate": 0.30, "Analyst": 0.15, "Manager": 0.10, "Director": 0.05},
    "Commercial Banking": {"Relationship Manager": 0.35, "Analyst": 0.25, "Associate": 0.20, "Manager": 0.15, "Director": 0.05},
    "Capital Markets": {"Analyst": 0.40, "Associate": 0.25, "Manager": 0.15, "Director": 0.10, "Developer": 0.10},
    "Wealth Management": {"Relationship Manager": 0.45, "Associate": 0.25, "Analyst": 0.15, "Manager": 0.10, "Director": 0.05},
    "Operations": {"Operations Specialist": 0.55, "Associate": 0.20, "Manager": 0.15, "Analyst": 0.05, "Director": 0.05},
    "Technology": {"Developer": 0.50, "Analyst": 0.20, "Manager": 0.15, "Director": 0.10, "Associate": 0.05},
    "Risk and Compliance": {"Risk Analyst": 0.50, "Analyst": 0.20, "Manager": 0.15, "Associate": 0.10, "Director": 0.05},
    "Corporate Functions": {"Associate": 0.30, "Analyst": 0.25, "Manager": 0.20, "Director": 0.15, "Operations Specialist": 0.10},
}

REGIONS = ["Canada - East", "Canada - West", "US - Northeast", "US - Midwest", "Europe", "APAC"]
REGION_WEIGHTS = [0.30, 0.20, 0.20, 0.10, 0.12, 0.08]

MANAGER_LEVEL_BY_ROLE = {
    "Analyst": "Individual Contributor",
    "Associate": "Individual Contributor",
    "Developer": "Individual Contributor",
    "Operations Specialist": "Individual Contributor",
    "Risk Analyst": "Individual Contributor",
    "Relationship Manager": "Individual Contributor",
    "Manager": "People Manager",
    "Director": "Senior Leader",
}

TRAINING_FORMATS = ["Live Virtual", "Self-Paced eLearning", "In-Person Workshop", "Manager-Led Briefing"]
TRAINING_FORMAT_WEIGHTS = [0.35, 0.40, 0.15, 0.10]

# Rollout wave windows: 6 waves x 4 weeks each across the 24-week rollout
N_WAVES = 6
WEEKS_PER_WAVE = N_WEEKS // N_WAVES

# Probability a BU's users are assigned to each wave (1..6); shapes the
# "who goes first" narrative described in the project brief.
BU_WAVE_WEIGHTS = {
    "Technology": [0.45, 0.30, 0.12, 0.08, 0.03, 0.02],
    "Capital Markets": [0.35, 0.30, 0.15, 0.10, 0.06, 0.04],
    "Retail Banking": [0.15, 0.17, 0.18, 0.18, 0.16, 0.16],
    "Operations": [0.14, 0.16, 0.18, 0.18, 0.17, 0.17],
    "Commercial Banking": [0.10, 0.18, 0.24, 0.22, 0.16, 0.10],
    "Wealth Management": [0.10, 0.16, 0.24, 0.22, 0.18, 0.10],
    "Corporate Functions": [0.08, 0.14, 0.22, 0.24, 0.20, 0.12],
    "Risk and Compliance": [0.03, 0.05, 0.12, 0.20, 0.30, 0.30],
}

MANAGER_CHAMPION_RATE = {
    "Technology": 0.35,
    "Capital Markets": 0.25,
    "Risk and Compliance": 0.20,
}
DEFAULT_CHAMPION_RATE = 0.15

TRAINING_COMPLETION_RATE = {
    "Technology": 0.85,
    "Capital Markets": 0.78,
    "Risk and Compliance": 0.80,  # compliance-mandated, so completion itself is high
    "Wealth Management": 0.72,
    "Commercial Banking": 0.70,
    "Corporate Functions": 0.68,
    "Retail Banking": 0.55,  # uneven attendance due to time constraints
    "Operations": 0.60,
}

INELIGIBLE_RATE = {
    "Risk and Compliance": 0.08,
}
DEFAULT_INELIGIBLE_RATE = 0.05

# ---------------------------------------------------------------------------
# Feature catalog
# ---------------------------------------------------------------------------
FEATURES = [
    # feature_name, feature_category, target_persona, release_week, core_feature_flag
    ("Chat and Research", "Research & Knowledge", "All Employees", 1, True),
    ("Knowledge Search", "Research & Knowledge", "All Employees", 1, True),
    ("Document Summarization", "Productivity", "All Employees", 1, True),
    ("Meeting Notes", "Productivity", "All Employees", 1, True),
    ("Prompt Library", "Enablement", "All Employees", 1, True),
    ("Drafting Assistant", "Productivity", "Client-Facing Roles & Managers", 3, True),
    ("Data Analysis", "Technical / Analytical", "Technical Roles (Analysts, Developers)", 5, False),
    ("Code Assistant", "Technical / Analytical", "Technical Roles (Developers)", 7, False),
]
FEATURE_NAMES = [f[0] for f in FEATURES]
FEATURE_RELEASE_WEEK = {f[0]: f[3] for f in FEATURES}

# Baseline feature popularity weight (before role/BU/behavioral tilts)
FEATURE_BASE_WEIGHT = {
    "Knowledge Search": 20,
    "Document Summarization": 18,
    "Chat and Research": 14,
    "Drafting Assistant": 12,
    "Meeting Notes": 10,
    "Prompt Library": 10,
    "Data Analysis": 9,
    "Code Assistant": 7,
}

# Multiplicative tilts by role
ROLE_FEATURE_TILT = {
    "Developer": {"Code Assistant": 5.0, "Data Analysis": 2.0, "Knowledge Search": 1.2},
    "Analyst": {"Data Analysis": 3.0, "Chat and Research": 1.5, "Knowledge Search": 1.3},
    "Risk Analyst": {"Knowledge Search": 1.5, "Document Summarization": 1.4, "Chat and Research": 1.2,
                      "Code Assistant": 0.2, "Data Analysis": 0.4},
    "Relationship Manager": {"Drafting Assistant": 2.0, "Meeting Notes": 1.5, "Chat and Research": 1.3,
                              "Code Assistant": 0.1, "Data Analysis": 0.2},
    "Manager": {"Meeting Notes": 1.8, "Drafting Assistant": 1.5, "Document Summarization": 1.3,
                "Code Assistant": 0.3, "Data Analysis": 0.5},
    "Director": {"Meeting Notes": 1.8, "Drafting Assistant": 1.5, "Document Summarization": 1.3,
                 "Code Assistant": 0.2, "Data Analysis": 0.4},
    "Operations Specialist": {"Knowledge Search": 1.6, "Document Summarization": 1.5, "Meeting Notes": 1.2,
                               "Code Assistant": 0.2, "Data Analysis": 0.3},
    "Associate": {"Chat and Research": 1.3, "Document Summarization": 1.2},
}

# Multiplicative tilts by business unit (compounds with role tilt)
BU_FEATURE_TILT = {
    "Technology": {"Code Assistant": 2.0, "Data Analysis": 1.5},
    "Capital Markets": {"Data Analysis": 1.8},
    "Risk and Compliance": {"Code Assistant": 0.3, "Data Analysis": 0.5, "Knowledge Search": 1.3},
}

FEATURE_PROMPT_CATEGORIES = {
    "Chat and Research": ["General Q&A", "Research"],
    "Knowledge Search": ["Research", "Policy/Compliance Lookup"],
    "Document Summarization": ["Summarization"],
    "Meeting Notes": ["Meeting Notes"],
    "Prompt Library": ["General Q&A", "Enablement"],
    "Drafting Assistant": ["Drafting", "Client Communication"],
    "Data Analysis": ["Data Analysis"],
    "Code Assistant": ["Code"],
}

FEATURE_MINUTES_SAVED_RANGE = {
    "Chat and Research": (5, 20),
    "Knowledge Search": (5, 15),
    "Document Summarization": (10, 30),
    "Meeting Notes": (10, 20),
    "Prompt Library": (5, 15),
    "Drafting Assistant": (15, 40),
    "Data Analysis": (20, 60),
    "Code Assistant": (20, 50),
}

EVENT_TYPES = [
    "app_opened", "prompt_submitted", "output_generated", "output_exported",
    "feature_completed", "help_opened", "error_encountered", "feedback_submitted",
]
EVENT_TYPE_WEIGHTS = [0.20, 0.32, 0.24, 0.08, 0.10, 0.03, 0.02, 0.01]
MEANINGFUL_EVENT_TYPES = {"prompt_submitted", "output_generated", "feature_completed", "output_exported"}

PLATFORMS = ["Web", "Desktop App", "Teams Plugin", "Outlook Plugin", "Mobile"]
PLATFORM_WEIGHTS = [0.55, 0.20, 0.15, 0.07, 0.03]
PLATFORM_SOURCE_SYSTEM = {
    "Web": "Northstar Assist Web",
    "Desktop App": "Northstar Assist Desktop",
    "Teams Plugin": "Teams Integration",
    "Outlook Plugin": "Outlook Integration",
    "Mobile": "Northstar Assist Mobile",
}

BARRIER_CATEGORIES = [
    "No time to learn",
    "Unsure what use cases are allowed",
    "Low output quality",
    "Hard to find the right feature",
    "Privacy or compliance concern",
    "Lack of relevant training",
    "Tool performance issue",
    "No barrier reported",
]
BARRIER_BASE_WEIGHT = {
    "No time to learn": 15,
    "Unsure what use cases are allowed": 10,
    "Low output quality": 10,
    "Hard to find the right feature": 8,
    "Privacy or compliance concern": 8,
    "Lack of relevant training": 10,
    "Tool performance issue": 7,
    "No barrier reported": 32,
}

FACILITATORS = ["J. Alvarez", "M. Chen", "S. Okafor", "R. Singh", "T. Nguyen", "L. Bianchi"]
TRAINING_TOPICS = [
    "Northstar Assist Fundamentals",
    "Prompt Writing Basics",
    "Responsible AI & Approved Use Cases",
    "Advanced Data Analysis Features",
    "Code Assistant Deep Dive",
]

FEEDBACK_TEMPLATES = {
    "No time to learn": [
        "I know Northstar Assist could help but I haven't had time to sit down and learn it properly.",
        "Between meetings and deadlines I haven't found the time to explore {feature}.",
    ],
    "Unsure what use cases are allowed": [
        "I'm not always clear on what I'm allowed to use {feature} for in client-facing work.",
        "Guidance on approved use cases for Northstar Assist could be clearer.",
    ],
    "Low output quality": [
        "The output from {feature} needed a lot of editing before it was usable.",
        "{feature} sometimes gives generic answers that don't fit our context.",
    ],
    "Hard to find the right feature": [
        "It took me a while to figure out that {feature} was the right tool for what I needed.",
        "The menu of features isn't very intuitive; I didn't know {feature} existed until a colleague mentioned it.",
    ],
    "Privacy or compliance concern": [
        "I'm cautious about what data I put into {feature} given compliance requirements.",
        "I'd like clearer confirmation that {feature} is approved for use with client information.",
    ],
    "Lack of relevant training": [
        "The training I received didn't cover how {feature} applies to my day-to-day role.",
        "More role-specific training on {feature} would help me use it with confidence.",
    ],
    "Tool performance issue": [
        "{feature} was slow to respond a few times this week.",
        "I ran into an error using {feature} and had to restart my session.",
    ],
    "No barrier reported": [
        "{feature} has been a great time-saver for my day-to-day work.",
        "No issues to report — {feature} works well for what I need.",
        "Really happy with Northstar Assist overall, especially {feature}.",
    ],
}

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def week_number_of(date):
    """1-indexed week number within the rollout, clipped to [1, N_WEEKS]."""
    offset_days = (date - ROLLOUT_START).days
    wk = (offset_days // 7) + 1
    return int(min(max(wk, 1), N_WEEKS))


def week_start_of(date):
    wk = week_number_of(date)
    return ROLLOUT_START + timedelta(weeks=wk - 1)


def weighted_choice(options, weights):
    weights = np.array(weights, dtype=float)
    weights = weights / weights.sum()
    idx = RNG.choice(len(options), p=weights)
    return options[idx]


def sample_role(bu):
    mix = BU_ROLE_MIX[bu]
    roles = list(mix.keys())
    weights = list(mix.values())
    return weighted_choice(roles, weights)


def sample_wave(bu):
    weights = BU_WAVE_WEIGHTS[bu]
    return int(RNG.choice(np.arange(1, N_WAVES + 1), p=weights))


def random_date_in_range(start, end):
    delta_days = (end - start).days
    if delta_days <= 0:
        return start
    return start + timedelta(days=int(RNG.integers(0, delta_days + 1)))


def random_business_time(date):
    """Attach a randomized, business-hours-weighted time of day to a date."""
    if RNG.random() < 0.85:
        hour = int(RNG.integers(8, 18))
    else:
        hour = int(RNG.integers(18, 23))
    minute = int(RNG.integers(0, 60))
    second = int(RNG.integers(0, 60))
    return date.replace(hour=hour, minute=minute, second=second)


def fmt_ts(dt):
    return dt.strftime("%Y-%m-%d %H:%M:%S")


def fmt_date(dt):
    return dt.strftime("%Y-%m-%d")


# ---------------------------------------------------------------------------
# 1. Calendar dimension
# ---------------------------------------------------------------------------

def generate_calendar():
    rows = []
    d = ROLLOUT_START
    while d <= ROLLOUT_END:
        wk_num = week_number_of(d)
        wk_start = week_start_of(d)
        rows.append({
            "date": fmt_date(d),
            "week_start_date": fmt_date(wk_start),
            "week_number": wk_num,
            "month": d.month,
            "month_name": d.strftime("%B"),
            "quarter": (d.month - 1) // 3 + 1,
            "year": d.year,
        })
        d += timedelta(days=1)
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# 2. Feature catalog dimension
# ---------------------------------------------------------------------------

def generate_feature_catalog():
    rows = []
    for i, (name, category, persona, release_week, core_flag) in enumerate(FEATURES, start=1):
        release_date = ROLLOUT_START + timedelta(weeks=release_week - 1)
        rows.append({
            "feature_id": f"F{i:02d}",
            "feature_name": name,
            "feature_category": category,
            "target_persona": persona,
            "release_date": fmt_date(release_date),
            "core_feature_flag": core_flag,
        })
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# 3. Users dimension
# ---------------------------------------------------------------------------

def generate_users():
    bu_list = list(BU_WEIGHTS.keys())
    bu_choices = RNG.choice(bu_list, size=N_USERS, p=list(BU_WEIGHTS.values()))

    records = []
    for i in range(N_USERS):
        user_id = f"U{i + 1:05d}"
        bu = bu_choices[i]
        role = sample_role(bu)
        region = weighted_choice(REGIONS, REGION_WEIGHTS)
        manager_level = MANAGER_LEVEL_BY_ROLE[role]

        hire_date = ROLLOUT_START - timedelta(days=int(RNG.integers(30, 3650)))

        wave = sample_wave(bu)
        wave_week_start = (wave - 1) * WEEKS_PER_WAVE + 1
        wave_start_date = ROLLOUT_START + timedelta(weeks=wave_week_start - 1)
        wave_end_date = wave_start_date + timedelta(weeks=WEEKS_PER_WAVE) - timedelta(days=1)

        ineligible_rate = INELIGIBLE_RATE.get(bu, DEFAULT_INELIGIBLE_RATE)
        eligible = RNG.random() >= ineligible_rate

        assigned_access_date = random_date_in_range(wave_start_date, wave_end_date)
        if not eligible:
            # Ineligible users: about half still show an access date in the raw
            # log (a real-world data lag / entitlement error), half are blank.
            if RNG.random() < 0.5:
                assigned_access_date_str = fmt_date(assigned_access_date)
            else:
                assigned_access_date_str = ""
        else:
            assigned_access_date_str = fmt_date(assigned_access_date)

        training_assigned_date = assigned_access_date - timedelta(days=int(RNG.integers(0, 8)))

        champion_rate = MANAGER_CHAMPION_RATE.get(bu, DEFAULT_CHAMPION_RATE)
        manager_champion = RNG.random() < champion_rate
        # Small share of blanks to simulate an HR data-feed gap.
        champion_blank = RNG.random() < 0.01

        completion_rate = TRAINING_COMPLETION_RATE[bu]
        completed_training = RNG.random() < completion_rate
        if completed_training:
            training_completed_date = training_assigned_date + timedelta(days=int(RNG.integers(3, 22)))
            training_completed_date_str = fmt_date(training_completed_date)
        else:
            training_completed_date_str = ""

        training_format = weighted_choice(TRAINING_FORMATS, TRAINING_FORMAT_WEIGHTS)

        records.append({
            "user_id": user_id,
            "business_unit": bu,
            "role": role,
            "region": region,
            "manager_level": manager_level,
            "hire_date": fmt_date(hire_date),
            "assigned_access_date": assigned_access_date_str,
            "rollout_wave": wave,
            "training_assigned_date": fmt_date(training_assigned_date),
            "training_completed_date": training_completed_date_str,
            "training_format": training_format,
            "manager_champion_flag": "" if champion_blank else bool(manager_champion),
            "eligible_for_access_flag": bool(eligible),
        })

    df = pd.DataFrame(records)

    # --- Deliberate data-quality issues -----------------------------------
    # 1) A handful of exact-duplicate user rows (simulates a duplicate HR feed load).
    n_dupe_users = 8
    dupe_idx = RNG.choice(df.index, size=n_dupe_users, replace=False)
    df = pd.concat([df, df.loc[dupe_idx]], ignore_index=True)

    # 2) Inconsistent business_unit label variants on a small subset of rows.
    label_variants = {
        "Retail Banking": ["retail banking", "Retail  Banking", "RETAIL BANKING"],
        "Risk and Compliance": ["Risk & Compliance", "risk and compliance"],
        "Technology": ["technology ", "TECH"],
    }
    n_label_issues = 40
    label_idx = RNG.choice(df.index, size=n_label_issues, replace=False)
    for idx in label_idx:
        bu = df.at[idx, "business_unit"]
        if bu in label_variants:
            df.at[idx, "business_unit"] = random.choice(label_variants[bu])

    return df


# ---------------------------------------------------------------------------
# Activity-level model (drives usage_events volume/shape per user)
# ---------------------------------------------------------------------------

BU_ACTIVITY_BASE = {
    "Technology": {"none": 0.05, "light": 0.15, "moderate": 0.35, "power": 0.45},
    "Capital Markets": {"none": 0.08, "light": 0.20, "moderate": 0.40, "power": 0.32},
    "Wealth Management": {"none": 0.12, "light": 0.25, "moderate": 0.40, "power": 0.23},
    "Commercial Banking": {"none": 0.15, "light": 0.28, "moderate": 0.38, "power": 0.19},
    "Corporate Functions": {"none": 0.15, "light": 0.30, "moderate": 0.40, "power": 0.15},
    "Retail Banking": {"none": 0.22, "light": 0.33, "moderate": 0.32, "power": 0.13},
    "Operations": {"none": 0.20, "light": 0.35, "moderate": 0.33, "power": 0.12},
    "Risk and Compliance": {"none": 0.25, "light": 0.30, "moderate": 0.30, "power": 0.15},
}

ACTIVITY_LEVELS = ["none", "light", "moderate", "power"]
ACTIVITY_EVENT_RANGE = {"none": (0, 0), "light": (3, 14), "moderate": (15, 50), "power": (45, 160)}
ACTIVITY_DECAY_LAMBDA = {"light": 0.60, "moderate": 0.12, "power": 0.03}
ACTIVITY_CHURN_PROB = {"light": 0.0, "moderate": 0.30, "power": 0.12}
ACTIVITY_CHURN_CUTOFF_RANGE = {"moderate": (2, 10), "power": (8, 20)}


def assign_activity_level(bu, role, manager_champion, training_completed):
    weights = dict(BU_ACTIVITY_BASE[bu])

    def bump(level, factor):
        weights[level] = weights[level] * factor

    if manager_champion:
        bump("none", 0.6); bump("light", 0.9); bump("moderate", 1.3); bump("power", 1.6)
    if training_completed:
        bump("none", 0.7); bump("light", 0.95); bump("moderate", 1.2); bump("power", 1.3)
    if role in ("Developer", "Analyst") and bu in ("Technology", "Capital Markets"):
        bump("moderate", 1.15); bump("power", 1.4)
    if bu == "Risk and Compliance" and training_completed:
        # Reflects "higher adoption after training and approved-use-case
        # communications" for this business unit specifically.
        bump("none", 0.5); bump("moderate", 1.3); bump("power", 1.5)

    total = sum(weights.values())
    probs = [weights[lvl] / total for lvl in ACTIVITY_LEVELS]
    return weighted_choice(ACTIVITY_LEVELS, probs)


def feature_weights_for(role, bu, boost_prompt_library):
    weights = dict(FEATURE_BASE_WEIGHT)
    for feat, mult in ROLE_FEATURE_TILT.get(role, {}).items():
        weights[feat] = weights.get(feat, 1.0) * mult
    for feat, mult in BU_FEATURE_TILT.get(bu, {}).items():
        weights[feat] = weights.get(feat, 1.0) * mult
    if boost_prompt_library:
        # Designed correlation: Prompt Library usage is deliberately made more
        # common among moderate/power users to support the project's
        # exploration of "does Prompt Library use associate with retention?"
        # This is a built-in data assumption, not an observed causal effect.
        weights["Prompt Library"] = weights.get("Prompt Library", 1.0) * 1.6
    return weights


# ---------------------------------------------------------------------------
# 4. Usage events fact
# ---------------------------------------------------------------------------

def generate_usage_events(users_df):
    events = []
    event_seq = 1

    users_df = users_df.drop_duplicates(subset="user_id", keep="first")

    for _, u in users_df.iterrows():
        user_id = u["user_id"]
        bu_raw = u["business_unit"]
        bu = bu_raw.strip().title() if bu_raw.strip().title() in BUSINESS_UNITS else bu_raw
        # normalize a couple of known odd variants back to canonical for modeling logic only
        bu_norm = {
            "Tech": "Technology", "TECH": "Technology",
            "Risk & Compliance": "Risk and Compliance",
        }.get(bu_raw.strip(), bu_raw.strip())
        if bu_norm not in BUSINESS_UNITS:
            bu_norm = bu_raw.strip().title() if bu_raw.strip().title() in BUSINESS_UNITS else "Retail Banking"

        role = u["role"]
        access_date_str = u["assigned_access_date"]
        if not access_date_str or pd.isna(access_date_str):
            continue  # no access assigned -> no usage log

        access_date = datetime.strptime(access_date_str, "%Y-%m-%d")
        access_week = week_number_of(access_date)

        manager_champion = u["manager_champion_flag"] is True
        training_completed = bool(access_date_str) and bool(u["training_completed_date"]) and not pd.isna(u["training_completed_date"]) and u["training_completed_date"] != ""

        level = assign_activity_level(bu_norm, role, manager_champion, training_completed)

        # access_granted event always logged
        access_dt = random_business_time(access_date)
        events.append(_make_event(event_seq, user_id, access_dt, "access_granted", access_week))
        event_seq += 1

        if level == "none":
            if RNG.random() < 0.30:
                open_date = min(access_date + timedelta(days=int(RNG.integers(0, 5))), ROLLOUT_END)
                open_dt = random_business_time(open_date)
                events.append(_make_event(event_seq, user_id, open_dt, "app_opened", week_number_of(open_dt)))
                event_seq += 1
            continue

        lo, hi = ACTIVITY_EVENT_RANGE[level]
        total_events = int(RNG.integers(lo, hi + 1))
        if total_events == 0:
            continue

        weeks_available = list(range(access_week, N_WEEKS + 1))
        weeks_since = np.array([w - access_week for w in weeks_available])

        lam = ACTIVITY_DECAY_LAMBDA[level]
        base_w = np.exp(-lam * weeks_since)

        churn_prob = ACTIVITY_CHURN_PROB.get(level, 0.0)
        if churn_prob > 0 and RNG.random() < churn_prob:
            lo_c, hi_c = ACTIVITY_CHURN_CUTOFF_RANGE[level]
            cutoff = int(RNG.integers(lo_c, hi_c + 1))
            base_w = np.where(weeks_since > cutoff, base_w * 0.02, base_w)

        probs = base_w / base_w.sum()
        chosen_weeks = RNG.choice(weeks_available, size=total_events, p=probs)

        boost_prompt_library = level in ("moderate", "power")
        feat_weights = feature_weights_for(role, bu_norm, boost_prompt_library)

        for wk in sorted(chosen_weeks):
            wk_start = ROLLOUT_START + timedelta(weeks=int(wk) - 1)
            day_offset = int(RNG.integers(0, 7))
            candidate_date = wk_start + timedelta(days=day_offset)
            if candidate_date < access_date:
                candidate_date = access_date
            if candidate_date > ROLLOUT_END:
                candidate_date = ROLLOUT_END

            available_feats = [f for f in FEATURE_NAMES if FEATURE_RELEASE_WEEK[f] <= wk]
            if not available_feats:
                available_feats = ["Chat and Research"]
            w = np.array([feat_weights.get(f, 1.0) for f in available_feats], dtype=float)
            w = w / w.sum()
            feature_name = available_feats[RNG.choice(len(available_feats), p=w)]

            event_type = weighted_choice(EVENT_TYPES, EVENT_TYPE_WEIGHTS)
            ts = random_business_time(candidate_date)
            events.append(_make_event(event_seq, user_id, ts, event_type, wk, feature_name=feature_name))
            event_seq += 1

    df = pd.DataFrame(events)
    df = _inject_event_quality_issues(df, users_df)
    return df


def _make_event(seq, user_id, dt, event_type, week_num, feature_name=None):
    if feature_name is None:
        feature_name = "Chat and Research" if event_type == "access_granted" else weighted_choice(
            FEATURE_NAMES, [FEATURE_BASE_WEIGHT[f] for f in FEATURE_NAMES]
        )

    is_error = event_type == "error_encountered"
    successful = False if is_error else (RNG.random() < 0.93)
    output_exported_flag = event_type == "output_exported" or (
        event_type == "feature_completed" and RNG.random() < 0.05
    )

    minutes_saved = np.nan
    if event_type in ("output_generated", "output_exported", "feature_completed") and successful:
        lo, hi = FEATURE_MINUTES_SAVED_RANGE.get(feature_name, (5, 20))
        minutes_saved = round(float(RNG.uniform(lo, hi)), 1)

    duration_ranges = {
        "app_opened": (5, 30), "prompt_submitted": (20, 240), "output_generated": (20, 240),
        "output_exported": (10, 90), "feature_completed": (60, 600), "help_opened": (10, 90),
        "error_encountered": (5, 60), "feedback_submitted": (30, 180),
    }
    dlo, dhi = duration_ranges.get(event_type, (10, 120))
    duration = int(RNG.integers(dlo, dhi + 1))

    platform = weighted_choice(PLATFORMS, PLATFORM_WEIGHTS)
    source_system = PLATFORM_SOURCE_SYSTEM[platform]
    prompt_category = random.choice(FEATURE_PROMPT_CATEGORIES.get(feature_name, ["General Q&A"]))

    session_id = f"S-{user_id}-{dt.strftime('%Y%m%d')}"

    return {
        "event_id": f"EVT{seq:07d}",
        "user_id": user_id,
        "event_timestamp": fmt_ts(dt),
        "session_id": session_id,
        "feature_name": feature_name,
        "event_type": event_type,
        "prompt_category": prompt_category,
        "output_exported_flag": bool(output_exported_flag),
        "successful_completion_flag": bool(successful),
        "estimated_minutes_saved": minutes_saved,
        "session_duration_seconds": duration,
        "error_flag": bool(is_error),
        "platform": platform,
        "source_system": source_system,
    }


def _inject_event_quality_issues(df, users_df):
    n = len(df)
    access_lookup = dict(zip(users_df["user_id"], users_df["assigned_access_date"]))

    # 1) Exact duplicate events (same event_id and all fields) - simulates a
    #    retry/at-least-once delivery issue in the event pipeline.
    n_dupe = max(1, int(n * 0.004))
    dupe_idx = RNG.choice(df.index, size=n_dupe, replace=False)
    df = pd.concat([df, df.loc[dupe_idx]], ignore_index=True)

    # 2) Malformed / invalid timestamps
    n_invalid_ts = max(1, int(n * 0.001))
    bad_ts_idx = RNG.choice(df.index, size=n_invalid_ts, replace=False)
    bad_values = ["2026-13-45 99:99:99", "", "not_a_date", "00/00/0000"]
    for i, idx in enumerate(bad_ts_idx):
        df.at[idx, "event_timestamp"] = bad_values[i % len(bad_values)]

    # 3) Events timestamped before the user's assigned_access_date (violates
    #    the business rule that usage can only occur after access is granted).
    n_pre_access = max(1, int(n * 0.002))
    pre_idx = RNG.choice(df.index, size=n_pre_access, replace=False)
    for idx in pre_idx:
        uid = df.at[idx, "user_id"]
        acc = access_lookup.get(uid, "")
        if acc and not pd.isna(acc) and acc != "":
            try:
                acc_dt = datetime.strptime(acc, "%Y-%m-%d")
                bad_dt = acc_dt - timedelta(days=int(RNG.integers(1, 15)))
                df.at[idx, "event_timestamp"] = fmt_ts(random_business_time(bad_dt))
            except ValueError:
                continue

    # 4) Negative session_duration_seconds
    n_neg_dur = max(1, int(n * 0.003))
    neg_dur_idx = RNG.choice(df.index, size=n_neg_dur, replace=False)
    df.loc[neg_dur_idx, "session_duration_seconds"] = -df.loc[neg_dur_idx, "session_duration_seconds"]

    # 5) Negative estimated_minutes_saved (only where a value exists)
    has_minutes = df.index[df["estimated_minutes_saved"].notna()]
    n_neg_min = min(len(has_minutes), max(1, int(n * 0.003)))
    if n_neg_min > 0:
        neg_min_idx = RNG.choice(has_minutes, size=n_neg_min, replace=False)
        df.loc[neg_min_idx, "estimated_minutes_saved"] = -df.loc[neg_min_idx, "estimated_minutes_saved"]

    # 6) Missing feature_name
    n_missing_feat = max(1, int(n * 0.002))
    miss_feat_idx = RNG.choice(df.index, size=n_missing_feat, replace=False)
    df.loc[miss_feat_idx, "feature_name"] = ""

    # 7) Inconsistent feature label variants (for the cleaning pipeline to normalize)
    variant_map = {
        "Document Summarization": ["Doc Summarization", "document summarization"],
        "Chat and Research": ["Chat & Research", "chat and research"],
        "Knowledge Search": ["knowledge search "],
    }
    for canonical, variants in variant_map.items():
        rows = df.index[df["feature_name"] == canonical]
        n_variant = min(len(rows), max(1, int(len(rows) * 0.02)))
        if n_variant > 0:
            variant_idx = RNG.choice(rows, size=n_variant, replace=False)
            for idx in variant_idx:
                df.at[idx, "feature_name"] = random.choice(variants)

    return df.reset_index(drop=True)


# ---------------------------------------------------------------------------
# 5. Feedback fact
# ---------------------------------------------------------------------------

GIVE_FEEDBACK_PROB = {"none": 0.30, "light": 0.65, "moderate": 0.88, "power": 0.85}
N_ENTRIES_WEIGHTS = [0.45, 0.35, 0.20]  # 1, 2, 3 entries


def _rating_for(bu, week_num):
    base_mean = {
        "Technology": 4.2, "Capital Markets": 4.0, "Wealth Management": 3.8,
        "Commercial Banking": 3.7, "Corporate Functions": 3.7,
        "Retail Banking": 3.4, "Operations": 3.3, "Risk and Compliance": 3.2,
    }.get(bu, 3.5)
    if bu == "Risk and Compliance":
        base_mean += 0.6 * (week_num / N_WEEKS)  # improves as training/comms roll out
    val = RNG.normal(base_mean, 0.9)
    return int(min(max(round(val), 1), 5))


def _barrier_for(bu, rating):
    weights = dict(BARRIER_BASE_WEIGHT)

    def bump(cat, factor):
        weights[cat] = weights[cat] * factor

    if bu == "Risk and Compliance":
        bump("Privacy or compliance concern", 3.0)
        bump("Unsure what use cases are allowed", 2.5)
        bump("No barrier reported", 0.5)
    if bu in ("Retail Banking", "Operations"):
        bump("No time to learn", 2.0)
        bump("Lack of relevant training", 1.8)
        bump("No barrier reported", 0.7)
    if bu in ("Technology", "Capital Markets"):
        bump("No barrier reported", 1.5)
        bump("Low output quality", 0.7)

    if rating >= 4:
        bump("No barrier reported", 3.0)
        for cat in BARRIER_CATEGORIES:
            if cat != "No barrier reported":
                bump(cat, 0.5)
    elif rating == 3:
        pass
    else:
        bump("No barrier reported", 0.1)
        bump("Low output quality", 2.0)
        bump("Tool performance issue", 1.8)

    cats = list(weights.keys())
    w = np.array([weights[c] for c in cats], dtype=float)
    w = w / w.sum()
    return cats[RNG.choice(len(cats), p=w)]


def generate_feedback(users_df, usage_events_df):
    # Approximate each user's activity level via their meaningful-event count
    # in the (already generated) usage_events table, to keep feedback volume
    # correlated with observed engagement rather than resimulating it.
    meaningful = usage_events_df[usage_events_df["event_type"].isin(MEANINGFUL_EVENT_TYPES)]
    counts = meaningful.groupby("user_id").size()

    def level_from_count(c):
        if c == 0:
            return "none"
        if c <= 12:
            return "light"
        if c <= 45:
            return "moderate"
        return "power"

    rows = []
    fid = 1
    for _, u in users_df.drop_duplicates(subset="user_id").iterrows():
        user_id = u["user_id"]
        access_date_str = u["assigned_access_date"]
        if not access_date_str or pd.isna(access_date_str) or access_date_str == "":
            continue
        access_date = datetime.strptime(access_date_str, "%Y-%m-%d")

        bu_raw = u["business_unit"].strip()
        bu = {"retail banking": "Retail Banking", "Retail  Banking": "Retail Banking",
              "RETAIL BANKING": "Retail Banking", "Risk & Compliance": "Risk and Compliance",
              "risk and compliance": "Risk and Compliance", "technology ": "Technology",
              "TECH": "Technology"}.get(bu_raw, bu_raw)
        if bu not in BUSINESS_UNITS:
            bu = "Retail Banking"

        level = level_from_count(counts.get(user_id, 0))
        if RNG.random() >= GIVE_FEEDBACK_PROB[level]:
            continue

        n_entries = int(RNG.choice([1, 2, 3], p=N_ENTRIES_WEIGHTS))
        for _ in range(n_entries):
            fb_date = random_date_in_range(access_date, ROLLOUT_END)
            week_num = week_number_of(fb_date)
            rating = _rating_for(bu, week_num)
            barrier = _barrier_for(bu, rating)

            if rating <= 2:
                sentiment = "Negative"
            elif rating == 3:
                sentiment = "Neutral"
            else:
                sentiment = "Positive"
            if RNG.random() < 0.05:
                sentiment = random.choice(["Negative", "Neutral", "Positive"])

            if rating >= 4:
                would_recommend = RNG.random() < 0.90
            elif rating == 3:
                would_recommend = RNG.random() < 0.45
            else:
                would_recommend = RNG.random() < 0.12

            has_feature = RNG.random() >= 0.20
            feature_name = random.choice(FEATURE_NAMES) if has_feature else ""

            template_feature = feature_name if feature_name else "Northstar Assist"
            template = random.choice(FEEDBACK_TEMPLATES[barrier]).format(feature=template_feature)
            if RNG.random() < 0.08:
                template = ""  # some users skip the free-text box

            rows.append({
                "feedback_id": f"FB{fid:06d}",
                "user_id": user_id,
                "feedback_timestamp": fmt_ts(random_business_time(fb_date)),
                "rating_1_to_5": rating,
                "sentiment_label": sentiment,
                "barrier_category": barrier,
                "free_text_feedback": template,
                "feature_name": feature_name,
                "would_recommend_flag": bool(would_recommend),
            })
            fid += 1

    df = pd.DataFrame(rows)
    df = _inject_feedback_quality_issues(df)
    return df


def _inject_feedback_quality_issues(df):
    n = len(df)

    n_dupe = max(1, int(n * 0.001))
    dupe_idx = RNG.choice(df.index, size=n_dupe, replace=False)
    df = pd.concat([df, df.loc[dupe_idx]], ignore_index=True)

    n_invalid_rating = max(1, int(n * 0.002))
    bad_idx = RNG.choice(df.index, size=n_invalid_rating, replace=False)
    for idx in bad_idx:
        df.at[idx, "rating_1_to_5"] = random.choice([0, 6, -1])

    return df.reset_index(drop=True)


# ---------------------------------------------------------------------------
# 6. Training sessions fact
# ---------------------------------------------------------------------------

def generate_training_sessions():
    rows = []
    sid = 1
    for bu in BUSINESS_UNITS:
        n_sessions = int(RNG.integers(6, 11))
        for _ in range(n_sessions):
            wk = int(RNG.integers(1, N_WEEKS - 1))
            session_date = ROLLOUT_START + timedelta(weeks=wk - 1, days=int(RNG.integers(0, 5)))
            fmt = weighted_choice(TRAINING_FORMATS, TRAINING_FORMAT_WEIGHTS)

            base_registered = int(RNG.integers(20, 120))
            attendance_rate = {
                "Retail Banking": 0.65, "Operations": 0.68, "Risk and Compliance": 0.80,
                "Technology": 0.88, "Capital Markets": 0.82,
            }.get(bu, 0.75)
            attended = int(base_registered * min(1.0, attendance_rate + RNG.normal(0, 0.08)))
            attended = max(0, min(attended, base_registered))
            completion = int(attended * min(1.0, 0.85 + RNG.normal(0, 0.07)))
            completion = max(0, min(completion, attended))

            rows.append({
                "training_session_id": f"TR{sid:04d}",
                "session_date": fmt_date(session_date),
                "business_unit": bu,
                "training_format": fmt,
                "registered_count": base_registered,
                "attended_count": attended,
                "completion_count": completion,
                "facilitator": random.choice(FACILITATORS),
                "session_topic": random.choice(TRAINING_TOPICS),
            })
            sid += 1
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# Main orchestration
# ---------------------------------------------------------------------------

def main():
    os.makedirs(RAW_DIR, exist_ok=True)

    print("Generating calendar.csv ...")
    calendar_df = generate_calendar()

    print("Generating feature_catalog.csv ...")
    feature_catalog_df = generate_feature_catalog()

    print("Generating users.csv ...")
    users_df = generate_users()

    print("Generating usage_events.csv (this may take a few seconds) ...")
    usage_events_df = generate_usage_events(users_df)

    print("Generating feedback.csv ...")
    feedback_df = generate_feedback(users_df, usage_events_df)

    print("Generating training_sessions.csv ...")
    training_sessions_df = generate_training_sessions()

    outputs = {
        "users.csv": users_df,
        "usage_events.csv": usage_events_df,
        "feedback.csv": feedback_df,
        "training_sessions.csv": training_sessions_df,
        "feature_catalog.csv": feature_catalog_df,
        "calendar.csv": calendar_df,
    }

    for filename, df in outputs.items():
        path = os.path.join(RAW_DIR, filename)
        df.to_csv(path, index=False)
        print(f"  wrote {filename}: {len(df):,} rows -> {path}")

    print("\n=== Generation summary (synthetic data only) ===")
    print(f"Users: {len(users_df):,} (target 6,000 + intentional duplicates)")
    print(f"Usage events: {len(usage_events_df):,} (target range 120,000-250,000)")
    print(f"Feedback records: {len(feedback_df):,} (target range 5,000-12,000)")
    print(f"Training sessions: {len(training_sessions_df):,}")
    print(f"Feature catalog rows: {len(feature_catalog_df):,}")
    print(f"Calendar days: {len(calendar_df):,}")

    assert 120_000 <= len(usage_events_df) <= 260_000, "usage_events.csv row count is out of the expected range"
    assert 5_000 <= len(feedback_df) <= 12_500, "feedback.csv row count is out of the expected range"

    print("\nAll target row-count ranges satisfied. Reminder: ALL data above is")
    print("synthetic and fictional (Northstar Financial Group / Northstar Assist).")
    print("It does not represent RBC, TD, or any real financial institution.")


if __name__ == "__main__":
    main()
