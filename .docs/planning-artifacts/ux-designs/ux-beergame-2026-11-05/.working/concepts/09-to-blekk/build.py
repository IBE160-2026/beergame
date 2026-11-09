"""Bygger alle SVG-er for konsept 09 To blekk. Kjør: uv run python build.py"""
import sys

from core import *  # noqa: F403
from pages_game import page_05, page_06, page_07, page_04
from pages_ops import page_01, page_02, page_03, page_08, page_09

PAGES = {"01": page_01, "02": page_02, "03": page_03, "04": page_04, "05": page_05,
         "06": page_06, "07": page_07, "08": page_08, "09": page_09}

only = sys.argv[1:] or list(PAGES)
for key in only:
    PAGES[key]()
    print("bygget", key)
