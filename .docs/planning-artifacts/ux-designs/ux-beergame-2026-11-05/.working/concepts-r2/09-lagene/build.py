"""Bygger konsept 09 Lagene. Alle tall i grafer og lister leses fra ../_shared/fixture.json."""
import sys

from lib import *
from pages_student import page_01, page_04, page_05, page_06
from pages_laerer import page_02, page_03, page_08
from pages_fag import page_07, page_09, page_10

assert_balanse()

PAGES = {
    "01": page_01, "02": page_02, "03": page_03, "04": page_04, "05": page_05,
    "06": page_06, "07": page_07, "08": page_08, "09": page_09, "10": page_10,
}

only = sys.argv[1:] or list(PAGES)
for key in only:
    PAGES[key]()
    print("bygget", key)
