"""Simple rule-based legal factor computation."""
from app.agents.base import BaseAgent
from app.math.formulas import compute_f_legal, compute_s_legal_liquidity


class LegalAgent(BaseAgent):
    name = "legal"

    async def run(self, ctx: dict) -> dict:
        inp = ctx["input"]
        ownership = inp.get("ownership")
        title_clear = inp.get("title_clear")

        f_legal = compute_f_legal(ownership, title_clear)
        s_legal = compute_s_legal_liquidity(ownership, title_clear)

        status = "clear"
        if title_clear is False:
            status = "disputed"
        elif title_clear is None:
            status = "unknown"

        warnings = []
        if ownership == "leasehold":
            warnings.append({"flag": "leasehold_property", "severity": "low",
                           "explanation": "Leasehold properties have reduced marketability"})
        if title_clear is False:
            warnings.append({"flag": "title_disputed", "severity": "high",
                           "explanation": "Disputed title severely impacts value and liquidity"})
        if title_clear is None and ownership is None:
            warnings.append({"flag": "legal_info_missing", "severity": "low",
                           "explanation": "No ownership or title information provided"})

        return {
            "f_legal": f_legal,
            "s_legal": s_legal,
            "ownership": ownership or "unknown",
            "title_status": status,
            "legal_multiplier": f_legal,
            "warnings": warnings,
        }
