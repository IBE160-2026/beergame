import { describe, expect, it } from "vitest";

import { nb } from "@/copy/nb";

import {
  changedReason,
  gameLabel,
  gameLine,
  gameState,
  holderName,
  invalidMoveReason,
  movedLine,
  nextGame,
  pickLabel,
  seatMark,
  targetLabel,
  ticks,
  withoutSeatLine,
} from "./allocation";
import type { Allocation, AllocationGame } from "./api";

const game: AllocationGame = {
  number: 17,
  seats: [
    { role: "factory", user_id: null, name: null },
    { role: "distributor", user_id: "c", name: null },
    { role: "wholesaler", user_id: "b", name: "Sara" },
    { role: "retailer", user_id: "a", name: "Ida" },
  ],
};

describe("the allocation preview (Story 5.8)", () => {
  it("reads a game's Seats from Detaljist to Fabrikk, naming empty and removed Seats", () => {
    expect(gameLine(game)).toBe(
      "Ida, Detaljist. Sara, Grossist. Ikke lenger i Klassen, Distributør. KI-spiller, Fabrikk.",
    );
    expect(holderName(game.seats[0])).toBe("KI-spiller");
  });

  it("says an opened Class game's state apart from its Seats (Story 5.12)", () => {
    const opened = { ...game, lifecycle: "not_started" as const };
    expect(gameLine(opened)).toBe(gameLine(game));
    expect(gameState(opened)).toBe("Ikke startet.");
    expect(gameState(game)).toBe("");
    expect(gameLabel(opened)).toBe(`Spill ${game.number}: ${gameLine(game)} Ikke startet.`);
    expect(gameLabel(game)).toBe(`Spill ${game.number}: ${gameLine(game)}`);
    expect(gameState({ ...game, lifecycle: "playing_out" })).toBe("Spilles ferdig.");
  });

  it("ticks the first, selected and last game once each", () => {
    expect(ticks(60, 17)).toEqual([1, 17, 60]);
    expect(ticks(60, 1)).toEqual([1, 60]);
    expect(ticks(1, 1)).toEqual([1]);
    expect(ticks(0, 1)).toEqual([]);
    // Narrow columns: a number too close to the selected one gives way.
    expect(ticks(100, 99, 3)).toEqual([1, 99]);
    expect(ticks(100, 2, 3)).toEqual([2, 100]);
    expect(ticks(100, 50, 3)).toEqual([1, 50, 100]);
  });

  it("moves the selection with the arrow keys, Home and End, inside the games", () => {
    expect(nextGame("ArrowRight", 3, 5)).toBe(4);
    expect(nextGame("ArrowRight", 5, 5)).toBe(5);
    expect(nextGame("ArrowLeft", 1, 5)).toBe(1);
    expect(nextGame("Home", 4, 5)).toBe(1);
    expect(nextGame("End", 2, 5)).toBe(5);
    expect(nextGame("Enter", 2, 5)).toBeNull();
  });
});

describe("confirming the allocation (Story 5.9)", () => {
  it("marks a removed Student apart from a seated one and an empty Seat (issue 106)", () => {
    expect(game.seats.map(seatMark)).toEqual(["empty", "removed", "student", "student"]);
  });

  it("says why a confirm committed nothing", () => {
    expect(changedReason({ draft: "students_removed" })).toBe(
      "En eller flere studenter er ikke lenger i Klassen. Plassene deres er nå tomme. Se over fordelingen og bekreft igjen.",
    );
    expect(changedReason({ draft: "changed" })).toBe(
      "Fordelingen er endret siden du åpnet den. Se over den nye og bekreft igjen.",
    );
    expect(changedReason(undefined)).toBe(changedReason({ draft: "changed" }));
  });

  it("names what a Class session lacks on the Lærerhjem", () => {
    const lacks = nb.sessions.home.lacks;
    expect(lacks("k", 2, ["dates", "allocation"])).toBe("k: Klasseøkt 2 mangler datoer og bekreftet fordeling");
    expect(lacks("k", 1, ["allocation"])).toBe("k: Klasseøkt 1 mangler bekreftet fordeling");
    expect(lacks("k", 1, ["dates"])).toBe("k: Klasseøkt 1 mangler datoer");
  });
});

describe("moving and swapping (Story 5.10)", () => {
  const ida = { game: 17, seat: game.seats[3] };
  const sara = { game: 4, seat: game.seats[2] };
  const free = { game: 4, seat: game.seats[0] };

  it("names the Student, the Role and the Klassespill on every button", () => {
    expect(pickLabel(ida)).toBe("Flytt eller bytt Ida, Detaljist i Spill 17");
    expect(targetLabel(ida, sara)).toBe("Bytt Ida (Detaljist, Spill 17) med Sara (Grossist, Spill 4)");
    expect(targetLabel(ida, free)).toBe("Flytt Ida (Detaljist, Spill 17) til ledig sete: Fabrikk i Spill 4");
  });

  it("says what changed, and why a move was refused", () => {
    expect(movedLine(ida, sara)).toBe("Ida og Sara har byttet plass.");
    expect(movedLine(ida, free)).toBe("Ida er flyttet til Fabrikk i Spill 4.");
    expect(invalidMoveReason({ from: "last_student" })).toBe(nb.sessions.allocation.moveLastStudent);
    expect(invalidMoveReason({ to: "same" })).toBe(nb.sessions.allocation.moveInvalid);
  });
});

describe("Students without a Seat after the lock (Story 5.13)", () => {
  const base: Allocation = {
    registered_count: 6,
    missing_count: 0,
    draft: null,
    confirmed: true,
    confirmed_at: null,
    opened: true,
    method: "random",
    without_seat: [],
  };

  it("names them in one line, and says nothing when every Student is seated", () => {
    expect(withoutSeatLine(base)).toBe("");
    expect(withoutSeatLine({ ...base, without_seat: [{ user_id: "a", name: "Ida Hansen" }] })).toBe(
      "1 registrert student har ikke sete: Ida Hansen.",
    );
    expect(
      withoutSeatLine({
        ...base,
        without_seat: [
          { user_id: "a", name: "Ida Hansen" },
          { user_id: "b", name: "Sara Berg" },
        ],
      }),
    ).toBe("2 registrerte studenter har ikke sete: Ida Hansen, Sara Berg.");
  });
});
