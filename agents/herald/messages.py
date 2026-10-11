"""Alert wording in English and Tamil (#10), action first.

Fixed templates, not a model: safety messages must be predictable, cost nothing,
and never invent facts. Say "likely waterlogged" for predictions; only a Reading
(band `flooded`) lets us say the street is waterlogged now.
Replay messages are prefixed [REPLAY] so a demo is never mistaken for a warning.
"""

from dataclasses import dataclass

from nimbus_contracts.common import RiskBand

REPLAY_PREFIX = "[REPLAY] "


@dataclass(frozen=True)
class Message:
    title: dict[str, str]
    body: dict[str, str]


def _when(minutes_to_flood: int | None) -> tuple[str, str]:
    if minutes_to_flood is None:
        return "soon", "விரைவில்"
    if minutes_to_flood < 60:
        return "within the hour", "ஒரு மணி நேரத்திற்குள்"
    hours = round(minutes_to_flood / 60)
    return f"in about {hours} hour{'' if hours == 1 else 's'}", f"சுமார் {hours} மணி நேரத்தில்"


def _move(safer_street: str | None) -> tuple[str, str]:
    if safer_street:
        return f"to {safer_street}", f"{safer_street} பகுதிக்கு"
    return "to higher ground", "மேடான இடத்திற்கு"


def risk_alert(street: str, band: RiskBand, minutes_to_flood: int | None, safer_street: str | None) -> Message:
    move_en, move_ta = _move(safer_street)
    if band == RiskBand.FLOODED:
        body = {
            "en": f"Verified reports say your street is waterlogged now. Avoid it and move your two-wheeler {move_en}.",
            "ta": f"சரிபார்க்கப்பட்ட தகவல்களின்படி உங்கள் தெருவில் இப்போது தண்ணீர் தேங்கியுள்ளது. அந்த வழியைத் தவிர்த்து, உங்கள் இருசக்கர வாகனத்தை {move_ta} நகர்த்துங்கள்.",
        }
    elif band == RiskBand.LIKELY:
        when_en, when_ta = _when(minutes_to_flood)
        body = {
            "en": f"Your street is likely waterlogged {when_en}. Move your two-wheeler {move_en} now.",
            "ta": f"உங்கள் தெருவில் {when_ta} தண்ணீர் தேங்க வாய்ப்புள்ளது. உங்கள் இருசக்கர வாகனத்தை இப்போதே {move_ta} நகர்த்துங்கள்.",
        }
    else:  # watch
        body = {
            "en": f"Heavy rain may waterlog your street in the next few hours. Be ready to move your two-wheeler {move_en}.",
            "ta": f"கனமழையால் அடுத்த சில மணி நேரங்களில் உங்கள் தெருவில் தண்ணீர் தேங்கக்கூடும். உங்கள் இருசக்கர வாகனத்தை {move_ta} நகர்த்தத் தயாராக இருங்கள்.",
        }
    return Message(title={"en": f"Flood alert: {street}", "ta": f"வெள்ள எச்சரிக்கை: {street}"}, body=body)


def all_clear(street: str) -> Message:
    return Message(
        title={"en": f"All clear: {street}", "ta": f"எச்சரிக்கை நீக்கம்: {street}"},
        body={
            "en": "The waterlogging risk on your street has eased.",
            "ta": "உங்கள் தெருவில் தண்ணீர் தேங்கும் அபாயம் குறைந்துள்ளது.",
        },
    )


def for_run(message: Message, run_id: str) -> Message:
    """Prefix every text with [REPLAY] outside the live Run. Text already prefixed is left alone."""
    if run_id == "live":
        return message

    def prefix(texts: dict[str, str]) -> dict[str, str]:
        return {lang: t if t.startswith(REPLAY_PREFIX) else REPLAY_PREFIX + t for lang, t in texts.items()}

    return Message(title=prefix(message.title), body=prefix(message.body))
