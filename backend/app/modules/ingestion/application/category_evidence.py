"""Read explicit source categories without guessing them from product names."""


def category_from_payload(payload: dict) -> str | None:
    value = payload.get("category")
    if isinstance(value, str) and value.strip() and len(value.strip()) <= 255:
        return value.strip()
    paths = payload.get("categories")
    if not isinstance(paths, list):
        return None
    parts = [
        tuple(part.strip() for part in path.strip("/").split("/") if part.strip())
        for path in paths if isinstance(path, str)
    ]
    parts = [path for path in parts if path]
    if not parts:
        return None
    deepest = max(parts, key=len)
    if any(deepest[:len(path)] != path for path in parts):
        return None
    return deepest[-1] if len(deepest[-1]) <= 255 else None
