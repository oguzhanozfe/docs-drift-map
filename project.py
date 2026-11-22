"""Map explicit action labels in a guide to an independently supplied UI inventory."""

import re
from difflib import SequenceMatcher

TITLE = "Docs Drift Map"
DESCRIPTION = "Check the actions named in a Markdown guide against the labels in your current interface."
PROMPT = "Explain the confirmed label changes with quoted evidence. Treat similar labels as suggestions, and ask for human confirmation when no alias proves a rename."

ACTION = re.compile(
    r"\b(click|tap|select|press|choose|open|enable|disable)\s+(?:the\s+)?"
    r"(?P<tag>\*\*|\x60|\"|“)(?P<name>[^\n*\"\x60”]+?)(?P<end>\*\*|\x60|\"|”)",
    re.I,
)


def key(label):
    return " ".join(label.casefold().split())


def analyze(data: dict) -> dict:
    if not isinstance(data, dict) or not isinstance(data.get("guide"), str):
        raise ValueError("Provide the Markdown guide as a string.")
    controls = data.get("controls")
    if not isinstance(controls, list) or not controls:
        raise ValueError("Provide a nonempty list of controls with labels.")
    names = {}
    aliases = {}
    for control in controls:
        if not isinstance(control, dict) or not isinstance(control.get("label"), str) or not control["label"].strip():
            raise ValueError("Each control needs a nonblank label.")
        label = control["label"].strip()
        if key(label) in names:
            raise ValueError("Current labels must be unique.")
        names[key(label)] = label
        former = control.get("formerly", [])
        if not isinstance(former, list) or any(not isinstance(x, str) or not x.strip() for x in former):
            raise ValueError("Former labels must be nonblank strings.")
        for alias in former:
            aliases.setdefault(key(alias), set()).add(label)
    rows = []
    section = "Introduction"
    fence = None
    for line_no, line in enumerate(data["guide"].splitlines(), 1):
        marker = re.match(r"^\s*(\x60{3,}|~{3,})", line)
        if marker:
            token = marker[1]
            if fence is None:
                fence = token
            elif token[0] == fence[0] and len(token) >= len(fence):
                fence = None
            continue
        if fence:
            continue
        heading = re.match(r"^\s*#{1,6}\s+(.+)", line)
        if heading:
            section = heading[1].strip()
        for hit in ACTION.finditer(line):
            if hit["end"] != {"“": "”"}.get(hit["tag"], hit["tag"]):
                continue
            observed = hit["name"].strip()
            norm = key(observed)
            candidate = ""
            if norm in names:
                status, candidate = "Current", names[norm]
            elif norm in aliases:
                matches = sorted(aliases[norm])
                status = "Renamed" if len(matches) == 1 else "Ambiguous alias"
                candidate = " / ".join(matches)
            else:
                status = "Unverified"
                score, closest = max((SequenceMatcher(None, norm, item).ratio(), item) for item in names)
                if score >= 0.62:
                    candidate = names[closest]
            rows.append({"Line": line_no, "Section": section, "Guide label": observed,
                         "Status": status, "Candidate": candidate})
    current = sum(r["Status"] == "Current" for r in rows)
    renamed = sum(r["Status"] == "Renamed" for r in rows)
    return {"summary": f"{len(rows)} action references checked. {renamed} have a recorded rename.",
            "metrics": {"References": len(rows), "Current": current, "Renamed": renamed,
                        "Need review": len(rows) - current - renamed}, "rows": rows}
