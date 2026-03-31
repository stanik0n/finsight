"""
Analyst commentary — Phase 2.

Takes the user's question and the SQL results, makes a second Groq call,
and returns a 2-3 sentence plain-English interpretation of the data.

Falls back to an empty string on any error so the main query path never breaks.
"""

import json
import os

from groq import Groq

GROQ_MODEL = 'llama-3.3-70b-versatile'

_COMMENTARY_SYSTEM = (
    "You are a concise financial analyst. "
    "Given a user's question and the raw query results as JSON, "
    "write 2-3 sentences interpreting what the data shows. "
    "Be specific: name tickers, cite numbers, highlight anything notable. "
    "Do not restate the question. Do not describe the SQL. Just analyse the results."
)


def generate_commentary(question: str, results: list[dict]) -> str:
    """Return a plain-English analyst comment for the given results.

    Returns an empty string if the API key is missing or the call fails.
    """
    groq_key = os.environ.get('GROQ_API_KEY', '')
    if not groq_key or not results:
        return ''

    # Truncate to first 20 rows to keep token count low
    sample = results[:20]
    user_msg = f"Question: {question}\n\nResults (JSON):\n{json.dumps(sample, default=str)}"

    try:
        client = Groq(api_key=groq_key)
        completion = client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[
                {'role': 'system', 'content': _COMMENTARY_SYSTEM},
                {'role': 'user',   'content': user_msg},
            ],
            temperature=0.3,
            max_tokens=200,
        )
        return completion.choices[0].message.content.strip()
    except Exception:
        return ''
