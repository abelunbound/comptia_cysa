"""Hardcoded fallback questions.

Used automatically by data_loader.load_questions() whenever the CSV file is
missing, empty, or malformed, so the app never crashes and always has at
least one question available to serve.

Each record matches the CSV schema exactly:
Domain, Sub-Section, Subtopic, Question, Option A, Option B, Option C,
Option D, Correct Answer, Explanation
"""

FALLBACK_QUESTIONS = [
    {
        "Domain": "Security Operations",
        "Sub-Section": "1.1",
        "Subtopic": "Logging Concepts",
        "Question": (
            "A security analyst is reviewing the logging configuration and "
            "notices that events from different servers show timestamps "
            "with a 5-minute discrepancy. Which logging concept is most "
            "critically misconfigured?"
        ),
        "Option A": "Ingestion",
        "Option B": "Configuration",
        "Option C": "Integrity",
        "Option D": "Time Synchronization",
        "Correct Answer": "D",
        "Explanation": (
            "Time synchronization ensures all logs use a consistent time "
            "source (like NTP). Without it, correlating events across "
            "different systems during an incident investigation becomes "
            "extremely difficult or impossible."
        ),
    },
    {
        "Domain": "Security Operations",
        "Sub-Section": "1.1",
        "Subtopic": "Logging Concepts",
        "Question": (
            "An organization is designing a new logging strategy and "
            "needs to ensure that once a log entry is written, it cannot "
            "be altered or deleted by an attacker. What is the primary "
            "security objective being addressed?"
        ),
        "Option A": "Integrity",
        "Option B": "Retention",
        "Option C": "Availability",
        "Option D": "Confidentiality",
        "Correct Answer": "A",
        "Explanation": (
            "Log integrity ensures that log data has not been tampered "
            "with. Techniques like write-once media or cryptographic "
            "hashing can be used to protect the integrity of log data, "
            "which is crucial for forensic investigations and compliance."
        ),
    },
]
