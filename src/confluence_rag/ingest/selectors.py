from __future__ import annotations


def build_cql(
    *,
    spaces: list[str] | None = None,
    labels: list[str] | None = None,
    ancestors: list[str] | None = None,
    include_archived: bool = False,
) -> str:
    parts: list[str] = ["type=page"]

    spaces = [s.strip() for s in (spaces or []) if s.strip()]
    labels = [l.strip() for l in (labels or []) if l.strip()]
    ancestors = [a.strip() for a in (ancestors or []) if a.strip()]

    if spaces:
        if len(spaces) == 1:
            parts.append(f'space="{spaces[0]}"')
        else:
            parts.append('space in ({})'.format(",".join(f'"{s}"' for s in spaces)))

    if labels:
        if len(labels) == 1:
            parts.append(f'label="{labels[0]}"')
        else:
            parts.append('label in ({})'.format(",".join(f'"{l}"' for l in labels)))

    if ancestors:
        if len(ancestors) == 1:
            parts.append(f"ancestor={ancestors[0]}")
        else:
            parts.append("(" + " or ".join(f"ancestor={a}" for a in ancestors) + ")")

    if not include_archived:
        parts.append('status="current"')

    return " and ".join(parts)

