import { describe, expect, it } from "vitest";

import { nb } from "@/copy/nb";

import { holderName, isChoosing } from "./allocation";
import type { Allocation, EnrolledSession, SeatChoice, SeatChoiceGame, SeatChoiceSeat } from "./api";
import { methodBody } from "./choices";
import { canTake, freeCount, homeLine, ownLine, seatText, takeLabel, whenLine } from "./seat-choice";

const seat = (over: Partial<SeatChoiceSeat> = {}): SeatChoiceSeat => ({
  role: "wholesaler",
  holder: "free",
  name: null,
  mine: false,
  ...over,
});

describe("«Velg spill og sete» in words (Story 5.17, UX-DR62)", () => {
  it("names every Seat state in text", () => {
    expect(seatText(seat())).toBe("Grossist, ledig");
    expect(seatText(seat({ holder: "student", name: "Ida Hansen" }))).toBe("Grossist, Ida Hansen");
    expect(seatText(seat({ holder: "student", name: "Ida Hansen", mine: true }))).toBe("Grossist, ditt sete");
    expect(seatText(seat({ holder: "student" }))).toBe("Grossist, Ikke lenger i Klassen");
    expect(seatText(seat({ holder: "ai" }))).toBe("Grossist, KI-spiller");
  });

  it("offers only a free Seat while the choice is open", () => {
    expect(canTake({ open: true }, seat())).toBe(true);
    expect(canTake({ open: false }, seat())).toBe(false);
    expect(canTake({ open: true }, seat({ holder: "student", name: "Ida" }))).toBe(false);
  });

  it("counts the free Seats and labels the primary button", () => {
    const game: SeatChoiceGame = {
      number: 17,
      seats: [seat({ role: "factory" }), seat({ role: "distributor", holder: "student", name: "A" })],
    };
    expect(freeCount(game)).toBe(1);
    expect(nb.sessions.seatChoice.freeCount(0)).toBe("Fullt");
    expect(nb.sessions.seatChoice.freeCount(2)).toBe("2 ledige");
    expect(takeLabel(17, "wholesaler")).toBe("Ta setet Grossist i Spill 17");
  });

  it("says the own Seat, drawn or chosen, and until when", () => {
    expect(ownLine({ my_seat: null, drawn: false })).toBe(nb.sessions.seatChoice.none);
    const mine = { game_number: 17, role: "wholesaler" } as const;
    expect(ownLine({ my_seat: mine, drawn: false })).toBe("Ditt sete: Grossist i Spill 17.");
    expect(ownLine({ my_seat: mine, drawn: true })).toBe("Du fikk et sete ved trekning: Grossist i Spill 17.");
    const open: Pick<SeatChoice, "open" | "start_at"> = { open: true, start_at: "2026-11-24T09:00:00Z" };
    expect(whenLine(open)).toBe(
      "Velg før startdatoen ti. 24. nov. kl. 10:00. Du kan bytte til et annet ledig sete fram til da.",
    );
    expect(whenLine({ open: true, start_at: null })).toBe(nb.sessions.seatChoice.beforeNoDate);
    expect(whenLine({ open: false, start_at: null })).toBe(nb.sessions.seatChoice.closed);
  });

  it("gives Hjem the Lenke while open and the drawn Seat after the lock", () => {
    const base = { seat_choice_open: false, drawn_seat: null } as unknown as EnrolledSession;
    expect(homeLine(base)).toBeNull();
    expect(homeLine({ ...base, seat_choice_open: true })).toEqual({ kind: "open" });
    expect(homeLine({ ...base, drawn_seat: { game_number: 3, role: "retailer" } })).toEqual({
      kind: "drawn",
      text: "Du fikk et sete ved trekning: Detaljist i Spill 3.",
    });
  });
});

describe("the Klasseøkt with Student choice (Story 5.17)", () => {
  it("sends only a change to Student choice", () => {
    expect(methodBody("student_choice", { allocation_method: "random" })).toEqual({
      allocation_method: "student_choice",
    });
    expect(methodBody("student_choice", { allocation_method: "student_choice" })).toEqual({});
    expect(methodBody("random", { allocation_method: "random" })).toEqual({});
  });

  it("names an empty Seat «Ledig» while the Students choose, «KI-spiller» otherwise", () => {
    const empty = { role: "retailer", user_id: null, name: null } as const;
    expect(holderName(empty, true)).toBe(nb.sessions.allocation.freeSeat);
    expect(holderName(empty)).toBe(nb.sessions.allocation.aiPlayer);
    const choosing = { method: "student_choice", opened: false } as Allocation;
    expect(isChoosing(choosing)).toBe(true);
    expect(isChoosing({ ...choosing, opened: true })).toBe(false);
    expect(isChoosing({ ...choosing, method: "random" })).toBe(false);
    expect(isChoosing(undefined)).toBe(false);
  });
});
