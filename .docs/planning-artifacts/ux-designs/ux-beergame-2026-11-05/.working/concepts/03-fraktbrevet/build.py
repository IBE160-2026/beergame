"""Bygger de 9 SVG-filene for konsept 03 Fraktbrev. Kjoer: uv run python build.py [navn ...]"""
import sys
from c03lib import *  # noqa: F403
import pages_game
import pages_laerer
import pages_annet

ALL = {
    "01": pages_annet.landing, "02": pages_laerer.klasse, "03": pages_laerer.okt, "04": pages_annet.hjem,
    "05": pages_game.spill, "06": pages_game.storyboard, "07": pages_game.debrief,
    "08": pages_laerer.oversikt, "09": pages_annet.alle,
}

if __name__ == "__main__":
    want = sys.argv[1:] or list(ALL)
    for key in want:
        ALL[key]()
        print("bygd", key)
