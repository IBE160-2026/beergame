"""The random allocation of registered Students into Class games of four (Story 5.8, FR-20).

`allocate` is pure and deterministic: the same ids, in any order, with the same seed always give
the same Seats. It holds ids only (AD-14); names are resolved at read time.
"""

import random
import secrets
import uuid
from collections.abc import Iterable
from dataclasses import dataclass

from app.engine.settings import ROLES, Role

GROUP_SIZE = len(ROLES)
"""Four: one Seat per Role."""

SEED_LIMIT = 2**53
"""Seeds stay below 2^53, so they are exact in JSON numbers too."""


@dataclass(frozen=True)
class Seat:
    """One Student's place in the draft: the Class game's number (from 1) and the Role."""

    user_id: uuid.UUID
    game_number: int
    role: Role


def draw_seed() -> int:
    """A fresh seed drawn by the server."""
    return secrets.randbelow(SEED_LIMIT)


def allocate(student_ids: Iterable[uuid.UUID], seed: int) -> list[Seat]:
    """Every Student placed at random in groups of four, each with a random Role (FR-20).

    The ids are sorted first, so their order does not matter, then shuffled with `seed`. They
    fill games 1, 2, … four at a time, so when the count is not divisible by four exactly one
    group, the last, has one to three Students; its other Roles stay empty (an AI player at the
    lock). Each group takes its own shuffle of the four Roles."""
    rng = random.Random(seed)
    ids = sorted(set(student_ids))
    rng.shuffle(ids)
    seats: list[Seat] = []
    for start in range(0, len(ids), GROUP_SIZE):
        roles = list(ROLES)
        rng.shuffle(roles)
        game_number = start // GROUP_SIZE + 1
        for user_id, role in zip(ids[start : start + GROUP_SIZE], roles, strict=False):
            seats.append(Seat(user_id=user_id, game_number=game_number, role=role))
    return seats
