"""PLACE: the place list and the locus patterns, graded as the guide grades
them. 1 for a state or a national forest, 2 for a ranger district, 3 for any
specific named place on the list or a locus (road number, elevation,
coordinates, unit number, map or figure reference)."""
from __future__ import annotations

import csv
import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from .text import PhraseMatcher, load_list

PLACES_CSV = Path(__file__).resolve().parents[2] / "seeds" / "entity_tagging" / "seed_places.csv"

_LEVEL_BY_KIND = {"forest": 1, "district": 2}

# A single-word name is an ambiguous English word bare ("Security", "Dry",
# "Lake"), so it is matched only beside a cue word for its kind.
_CUES: dict[str, tuple[str, ...]] = {
    "trail": ("trail", "trailhead"),
    "stream": ("creek", "stream", "river", "fork", "branch", "run", "brook"),
    "valley": ("valley", "canyon", "hollow", "draw", "gulch"),
    "summit": ("peak", "mountain", "mount", "butte", "knob", "hill", "summit", "dome"),
    "structure": ("cabin", "lookout", "station", "campground", "ranger station"),
    "spring": ("spring", "springs"),
    "lake": ("lake",),
    "area": ("roadless area", "inventoried roadless area", "wilderness", "area"),
    "reservoir": ("reservoir",),
    "ridge": ("ridge",),
    "flat": ("flat", "flats"),
    "gap": ("gap", "pass", "saddle"),
    "forest": ("national forest", "forest"),
    "district": ("ranger district", "district"),
    "basin": ("basin",),
    "bay": ("bay",),
    "island": ("island",),
    "range": ("range", "mountains"),
    "glacier": ("glacier",),
    "cliff": ("cliff", "cliffs"),
    "falls": ("falls", "waterfall"),
    "canal": ("canal",),
    "cape": ("cape", "point"),
    "swamp": ("swamp",),
    "rapids": ("rapids",),
    "bench": ("bench",),
    "bend": ("bend",),
    "slope": ("slope",),
    "woods": ("woods",),
    "arch": ("arch",),
    "plain": ("plain", "plains"),
    "crossing": ("crossing",),
    "crater": ("crater",),
    "arroyo": ("arroyo",),
    "beach": ("beach",),
    "bar": ("bar",),
    "channel": ("channel",),
    "gut": ("gut",),
    "pillar": ("pillar",),
    "lava": ("lava flow", "lava"),
    "isthmus": ("isthmus",),
    "sea": ("sea",),
}

_NAME_OK = re.compile(r"^[A-Za-z][A-Za-z0-9 .'\-]*$")

LOCUS: list[tuple[str, re.Pattern[str]]] = [
    ("road_number", re.compile(
        r"\b(?:forest\s+(?:service\s+)?road|fs\s*road|nfsr|fsr|road)\s*#?\s*\d{2,5}\b",
        re.IGNORECASE)),
    ("elevation", re.compile(
        r"\b\d{1,2},?\d{3}\s*(?:-\s*)?(?:feet|foot|ft\b\.?|')", re.IGNORECASE)),
    ("coordinates", re.compile(
        r"\b\d{1,3}(?:\.\d+)?\s*(?:°|degrees)\s*\d{1,2}\s*'"
        r"|-?\d{2,3}\.\d{4,}\s*,\s*-?\d{2,3}\.\d{4,}", re.IGNORECASE)),
    ("unit_number", re.compile(r"\bunits?\s+\d+(?:\s*[-–]\s*\d+)?\b", re.IGNORECASE)),
    ("map_figure", re.compile(r"\b(?:map|figure|fig\.)\s*\d+\b", re.IGNORECASE)),
]


def _usable(name: str) -> bool:
    return len(name) >= 3 and bool(_NAME_OK.match(name)) and any(c.isalpha() for c in name)


@dataclass(frozen=True)
class PlaceHit:
    level: int
    match: str
    start: int
    end: int
    rule: str


class Places:
    def __init__(self, csv_path: Path = PLACES_CSV) -> None:
        levels: dict[str, int] = {}
        with csv_path.open(newline="", encoding="utf-8") as fh:
            for row in csv.DictReader(fh):
                name = (row.get("name") or "").strip()
                kind = (row.get("kind") or "").strip().lower()
                if not _usable(name):
                    continue
                level = _LEVEL_BY_KIND.get(kind, 3)
                low = name.lower()
                if " " in low:
                    pats = [low]
                else:
                    pats = [f"{low} {cue}" for cue in _CUES.get(kind, (kind,))]
                for p in pats:
                    levels[p] = max(levels.get(p, 0), level)
        for state in load_list("states.txt"):
            levels[state] = max(levels.get(state, 0), 1)
        self._levels = levels
        self._matcher = PhraseMatcher(levels.keys())

    def find(self, text: str) -> list[PlaceHit]:
        out: list[PlaceHit] = []
        for m in self._matcher.find(text):
            # A listed name is a proper noun: it counts only written with a
            # capital. The list holds names that are also ordinary phrases
            # ("Wide Open", "The Face", "Can Do"), and lower-cased they are
            # the phrase, not the place.
            if not text[m.start].isupper():
                continue
            lv = self._levels[m.phrase]
            out.append(PlaceHit(lv, text[m.start:m.end], m.start, m.end, f"PLACE.list.{lv}"))
        for name, rx in LOCUS:
            for m in rx.finditer(text):
                out.append(PlaceHit(3, m.group(0), m.start(), m.end(), f"PLACE.locus.{name}"))
        return out


@lru_cache(maxsize=1)
def places() -> Places:
    return Places()
