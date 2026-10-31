"""Cosmetic preferences stay separate from radio settings and RF coordination."""
import json

from .models import settings_path

PALETTES = {
    "Dark": dict(bg="#111820", panel="#18232f", field="#202e3c", ink="#f4f7fb",
                 muted="#b5c6d6", edge="#334659", accent="#00b9ef", selected="#064f6a"),
    "Light": dict(bg="#edf2f6", panel="#ffffff", field="#ffffff", ink="#111b28",
                  muted="#465b70", edge="#c6d3df", accent="#007da6", selected="#cceefa"),
}


def load_appearance():
    try:
        value = json.loads(settings_path().with_name("appearance.json").read_text(encoding="utf-8"))
        return value["theme"] if value["theme"] in ("Light", "Dark") else "Dark"
    except (OSError, ValueError, KeyError, TypeError):
        return "Dark"


def save_appearance(theme):
    if theme not in PALETTES:
        raise ValueError("Choose Light or Dark appearance")
    path = settings_path().with_name("appearance.json")
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps({"theme": theme}), encoding="utf-8")
    temporary.replace(path)
