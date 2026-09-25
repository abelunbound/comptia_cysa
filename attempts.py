"""AuthZ-scoped exam attempt reads/writes. Score is server-side only.

Every query is filtered by user_id. Do not look up an attempt by id alone.
Do not accept client-supplied is_correct, score_*, or status=completed.
Correct answers and explanations are never included in in-progress payloads.
"""

from datetime import datetime

from auth import AttemptAnswer, ExamAttempt, Question, db

VALID_OPTIONS = frozenset({"A", "B", "C", "D"})
# Same green threshold as the results tiles / donut.
PASS_PERCENT = 70
CHART_ATTEMPT_SLOTS = 10
RESULTS_PAGE_SIZE = 5
BASELINE_START_MINUTES = 80
BASELINE_END_MINUTES = 50


def _as_int(value):
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _question_id_list(attempt):
    raw = attempt.question_ids or []
    return [int(qid) for qid in raw]


def get_in_progress_attempt(user_id):
    """Return the user's single in-progress attempt, or None."""
    return ExamAttempt.query.filter_by(
        user_id=user_id,
        status=ExamAttempt.STATUS_IN_PROGRESS,
    ).one_or_none()


def get_attempt_for_user(attempt_id, user_id):
    """Load an attempt only when it belongs to user_id (no IDOR via attempt id)."""
    aid = _as_int(attempt_id)
    if aid is None:
        return None
    return ExamAttempt.query.filter_by(id=aid, user_id=user_id).one_or_none()


def list_answers_for_user_attempt(attempt_id, user_id):
    """Answers for an attempt, only if that attempt belongs to user_id."""
    attempt = get_attempt_for_user(attempt_id, user_id)
    if not attempt:
        return []
    return AttemptAnswer.query.filter_by(attempt_id=attempt.id).all()


def abandon_attempt(user_id, attempt_id=None):
    """End the user's in-progress attempt. Never abandons another user's row.

    If attempt_id is omitted, abandons the current in-progress row for user_id.
    Does not write scores. Completing is a separate path.
    """
    if attempt_id is None:
        attempt = get_in_progress_attempt(user_id)
    else:
        attempt = get_attempt_for_user(attempt_id, user_id)
    if not attempt or attempt.status != ExamAttempt.STATUS_IN_PROGRESS:
        return None
    attempt.status = ExamAttempt.STATUS_ABANDONED
    attempt.completed_at = datetime.utcnow()
    db.session.commit()
    return attempt


def start_attempt(user_id, domain, subsection, question_ids, mode=None):
    """Create an in-progress attempt, or return the existing one (one per user).

    Does not abandon. Call abandon_attempt first after an explicit confirm.
    exam and practice are scored and listed the same; mode only changes Grade Now.
    """
    existing = get_in_progress_attempt(user_id)
    if existing:
        return existing

    ids = [_as_int(qid) for qid in question_ids]
    ids = [qid for qid in ids if qid is not None]
    if not ids:
        raise ValueError("start_attempt requires at least one question id")

    chosen_mode = (mode or ExamAttempt.MODE_EXAM).strip().lower()
    if chosen_mode not in (ExamAttempt.MODE_EXAM, ExamAttempt.MODE_PRACTICE):
        chosen_mode = ExamAttempt.MODE_EXAM

    attempt = ExamAttempt(
        user_id=user_id,
        status=ExamAttempt.STATUS_IN_PROGRESS,
        started_at=datetime.utcnow(),
        current_index=0,
        domain=domain or "",
        subsection=subsection or "",
        question_ids=ids,
        mode=chosen_mode,
    )
    db.session.add(attempt)
    db.session.commit()
    return attempt


def save_selected_option(user_id, attempt_id, question_id, selected_option):
    """Upsert the user's choice. Does not store correctness."""
    attempt = get_attempt_for_user(attempt_id, user_id)
    if not attempt or attempt.status != ExamAttempt.STATUS_IN_PROGRESS:
        return None

    qid = _as_int(question_id)
    letter = str(selected_option or "").strip().upper()
    if qid is None or qid not in _question_id_list(attempt) or letter not in VALID_OPTIONS:
        return None

    row = AttemptAnswer.query.filter_by(
        attempt_id=attempt.id, question_id=qid
    ).one_or_none()
    now = datetime.utcnow()
    if row:
        row.selected_option = letter
        row.answered_at = now
    else:
        db.session.add(
            AttemptAnswer(
                attempt_id=attempt.id,
                question_id=qid,
                selected_option=letter,
                answered_at=now,
            )
        )
    db.session.commit()
    return attempt


def set_resume_index(user_id, attempt_id, current_index):
    """Persist the resume cursor for an in-progress attempt owned by user_id."""
    attempt = get_attempt_for_user(attempt_id, user_id)
    if not attempt or attempt.status != ExamAttempt.STATUS_IN_PROGRESS:
        return None
    total = len(_question_id_list(attempt))
    if total == 0:
        return attempt
    attempt.current_index = max(0, min(int(current_index), total - 1))
    db.session.commit()
    return attempt


def complete_attempt(user_id, attempt_id):
    """Grade from DB answers vs question.correct_answer. Ignore client scores."""
    attempt = get_attempt_for_user(attempt_id, user_id)
    if not attempt or attempt.status != ExamAttempt.STATUS_IN_PROGRESS:
        return None

    question_ids = _question_id_list(attempt)
    questions = {
        q.id: q for q in Question.query.filter(Question.id.in_(question_ids)).all()
    } if question_ids else {}
    chosen = {
        row.question_id: str(row.selected_option).strip().upper()
        for row in AttemptAnswer.query.filter_by(attempt_id=attempt.id).all()
    }

    correct = 0
    for qid in question_ids:
        question = questions.get(qid)
        if not question:
            continue
        expected = str(question.correct_answer).strip().upper()
        if chosen.get(qid) == expected:
            correct += 1

    attempt.status = ExamAttempt.STATUS_COMPLETED
    attempt.completed_at = datetime.utcnow()
    attempt.score_correct = correct
    attempt.score_total = len(question_ids)
    db.session.commit()
    return attempt


def _answers_by_index(attempt):
    question_ids = _question_id_list(attempt)
    index_for = {qid: i for i, qid in enumerate(question_ids)}
    answers = {}
    for row in AttemptAnswer.query.filter_by(attempt_id=attempt.id).all():
        idx = index_for.get(row.question_id)
        if idx is not None:
            answers[str(idx)] = row.selected_option
    return answers


def _isoformat(value):
    if not value:
        return ""
    return value.isoformat(timespec="seconds")


def _question_map(question_ids):
    if not question_ids:
        return {}
    return {q.id: q for q in Question.query.filter(Question.id.in_(question_ids)).all()}


def public_exam_session(user_id, attempt=None):
    """In-progress session. Exam mode omits keys; practice includes them for Grade Now."""
    attempt = attempt or get_in_progress_attempt(user_id)
    if not attempt or attempt.user_id != user_id:
        return None
    if attempt.status != ExamAttempt.STATUS_IN_PROGRESS:
        return None

    question_ids = _question_id_list(attempt)
    by_id = _question_map(question_ids)
    is_practice = attempt.mode == ExamAttempt.MODE_PRACTICE
    questions = []
    for qid in question_ids:
        question = by_id.get(qid)
        if not question:
            continue
        row = {
            "id": question.id,
            "Domain": question.domain,
            "Sub-Section": question.sub_section,
            "Subtopic": question.subtopic,
            "Question": question.question,
            "Option A": question.option_a,
            "Option B": question.option_b,
            "Option C": question.option_c,
            "Option D": question.option_d,
        }
        if is_practice:
            row["Correct Answer"] = question.correct_answer
            row["Explanation"] = question.explanation
        questions.append(row)
    return {
        "attempt_id": attempt.id,
        "mode": attempt.mode or ExamAttempt.MODE_EXAM,
        "domain": attempt.domain,
        "subsection": attempt.subsection,
        "questions": questions,
        "answers": _answers_by_index(attempt),
        "current_index": attempt.current_index or 0,
        "started_at": _isoformat(attempt.started_at),
        "graded": {},
    }


def list_completed_summaries(user_id):
    """Completed attempts for results UI, oldest first. Scores from DB only."""
    rows = (
        ExamAttempt.query.filter_by(
            user_id=user_id, status=ExamAttempt.STATUS_COMPLETED
        )
        .order_by(ExamAttempt.completed_at.asc(), ExamAttempt.id.asc())
        .all()
    )
    summaries = []
    for attempt in rows:
        answers = _answers_by_index(attempt)
        summaries.append(
            {
                "id": attempt.id,
                "domain": attempt.domain,
                "subsection": attempt.subsection,
                "score": attempt.score_correct or 0,
                "total": attempt.score_total or 0,
                "answers": answers,
                "started_at": _isoformat(attempt.started_at),
                "submitted_at": _isoformat(attempt.completed_at),
            }
        )
    return summaries


def dashboard_metrics(user_id):
    """Highest / count / pass rate / average for this user's completed attempts."""
    rows = ExamAttempt.query.filter_by(
        user_id=user_id, status=ExamAttempt.STATUS_COMPLETED
    ).all()
    percents = []
    for attempt in rows:
        total = attempt.score_total or 0
        if total <= 0:
            continue
        percents.append(100.0 * (attempt.score_correct or 0) / total)
    if not percents:
        return {
            "highest_score": 0,
            "total_attempts": 0,
            "pass_rate": 0,
            "average_score": 0,
        }
    passed = sum(1 for percent in percents if percent >= PASS_PERCENT)
    return {
        "highest_score": round(max(percents)),
        "total_attempts": len(percents),
        "pass_rate": round(100.0 * passed / len(percents)),
        "average_score": round(sum(percents) / len(percents)),
    }


def _display_date(value):
    if not value:
        return ""
    return f"{value.strftime('%b')} {value.day}, {value.year}"


def dashboard_results_rows(user_id):
    """Completed attempts for the dashboard table. Newest first. This user only.

    Attempts is the 1-based count of completed tries at that subsection.
    Score is computed from stored score_correct / score_total.
    """
    rows = (
        ExamAttempt.query.filter_by(
            user_id=user_id, status=ExamAttempt.STATUS_COMPLETED
        )
        .order_by(ExamAttempt.completed_at.asc(), ExamAttempt.id.asc())
        .all()
    )
    seen = {}
    out = []
    for attempt in rows:
        key = (attempt.domain or "", attempt.subsection or "")
        seen[key] = seen.get(key, 0) + 1
        total = attempt.score_total or 0
        percent = 0
        if total:
            percent = round(100.0 * (attempt.score_correct or 0) / total)
        out.append(
            {
                "subsection": attempt.subsection or "—",
                "score": f"{percent}%",
                "attempts": seen[key],
                "date": _display_date(attempt.completed_at),
            }
        )
    out.reverse()
    return out


def dashboard_results_page(user_id, page=1, page_size=RESULTS_PAGE_SIZE):
    """One page of dashboard rows. Page 1 is the 5 most recent."""
    all_rows = dashboard_results_rows(user_id)
    total = len(all_rows)
    pages = max(1, (total + page_size - 1) // page_size) if total else 1
    try:
        page = int(page)
    except (TypeError, ValueError):
        page = 1
    page = max(1, min(page, pages))
    start = (page - 1) * page_size
    return {
        "rows": all_rows[start : start + page_size],
        "page": page,
        "pages": pages,
        "total": total,
    }


def latest_exam_percent(user_id):
    """Most recently submitted exam score as 0–100. None if none completed."""
    attempt = (
        ExamAttempt.query.filter_by(
            user_id=user_id, status=ExamAttempt.STATUS_COMPLETED
        )
        .order_by(ExamAttempt.completed_at.desc(), ExamAttempt.id.desc())
        .first()
    )
    if not attempt or not attempt.score_total:
        return None
    return round(100.0 * (attempt.score_correct or 0) / attempt.score_total)


def time_target_baseline(slots=CHART_ATTEMPT_SLOTS):
    """Fixed 80→50 minute target across the chart's attempt slots."""
    if slots <= 1:
        return [float(BASELINE_END_MINUTES)]
    step = (BASELINE_END_MINUTES - BASELINE_START_MINUTES) / (slots - 1)
    return [round(BASELINE_START_MINUTES + step * index, 1) for index in range(slots)]


def _duration_minutes(attempt):
    started = attempt.started_at
    finished = attempt.completed_at
    if not started or not finished:
        return None
    seconds = (finished - started).total_seconds()
    if seconds < 0:
        return 0.0
    return round(seconds / 60.0, 1)


def recent_attempt_durations(user_id, limit=CHART_ATTEMPT_SLOTS):
    """Start→Submit minutes for this user's last completed attempts, oldest first."""
    rows = (
        ExamAttempt.query.filter_by(
            user_id=user_id, status=ExamAttempt.STATUS_COMPLETED
        )
        .order_by(ExamAttempt.completed_at.desc(), ExamAttempt.id.desc())
        .limit(limit)
        .all()
    )
    rows.reverse()
    minutes = []
    for attempt in rows:
        duration = _duration_minutes(attempt)
        if duration is not None:
            minutes.append(duration)
    return minutes


def review_payload(user_id, attempt_id):
    """Completed attempt for review HTML. None if missing, in-progress, or not owned."""
    attempt = get_attempt_for_user(attempt_id, user_id)
    if not attempt or attempt.status != ExamAttempt.STATUS_COMPLETED:
        return None

    question_ids = _question_id_list(attempt)
    by_id = _question_map(question_ids)
    questions = []
    for qid in question_ids:
        question = by_id.get(qid)
        if not question:
            continue
        questions.append(
            {
                "id": question.id,
                "Domain": question.domain,
                "Sub-Section": question.sub_section,
                "Subtopic": question.subtopic,
                "Question": question.question,
                "Option A": question.option_a,
                "Option B": question.option_b,
                "Option C": question.option_c,
                "Option D": question.option_d,
                "Correct Answer": question.correct_answer,
                "Explanation": question.explanation,
            }
        )
    return {
        "id": attempt.id,
        "domain": attempt.domain,
        "subsection": attempt.subsection,
        "questions": questions,
        "answers": _answers_by_index(attempt),
        "score": attempt.score_correct or 0,
        "total": attempt.score_total or 0,
        "started_at": _isoformat(attempt.started_at),
        "submitted_at": _isoformat(attempt.completed_at),
    }
