import { describe, expect, it } from "vitest";

import type { MyMessage, SentMessage } from "./api";
import { againTo, arrivalText, recipientLine, senderName } from "./message-list";

const base: SentMessage = {
  id: "m1",
  kind: "class_session",
  game_id: null,
  game_number: null,
  student_id: null,
  student_name: null,
  sender_name: "Bård",
  sent_at: "2026-11-26T13:15:00Z",
  students: 4,
  text: "Hei",
};

const mine = (id: string, sender: string | null = "Bård"): MyMessage => ({
  id,
  class_id: "c1",
  class_name: "class-of-1994",
  sender_name: sender,
  sent_at: "2026-11-26T13:15:00Z",
  text: "Hei",
});

describe("recipientLine and againTo", () => {
  it("name each kind of recipient and the form to write to it again", () => {
    const student = { ...base, kind: "student" as const, student_id: "u1", student_name: "Noah" };
    const fromGame = { ...student, game_id: "g1", game_number: 2 };
    const game = { ...base, kind: "class_game" as const, game_id: "g1", game_number: 2 };
    const list = { ...base, kind: "list" as const, students: 12 };
    const notMet = { ...base, kind: "requirement_not_met" as const, students: 4 };
    expect([student, fromGame, game, base, list, notMet].map((item) => recipientLine(item, 1))).toEqual([
      "Til Noah",
      "Til Noah, Spill 2",
      "Til Spill 2",
      "Til alle i Klasseøkt 1",
      "Til 12 studenter",
      "Til 4 som ikke hadde oppfylt kravet",
    ]);
    expect([student, fromGame, game, base, list, notMet].map(againTo)).toEqual([
      { student: "u1" },
      { game: "g1", student: "u1" },
      { game: "g1" },
      {},
      null,
      { requirement: true },
    ]);
  });

  it("name a Student who left the Class without a way back to the form", () => {
    const gone = { ...base, kind: "student" as const, student_id: "u1", student_name: null };
    expect(recipientLine(gone, 1)).toBe("Til en tidligere student");
    expect(againTo(gone)).toBeNull();
  });
});

describe("senderName", () => {
  it("falls back to «Faglærer» when the sender's account is gone", () => {
    expect(senderName(mine("m1"))).toBe("Bård");
    expect(senderName(mine("m1", null))).toBe("Faglærer");
  });
});

describe("arrivalText", () => {
  it("says nothing on the first answer or when nothing is new", () => {
    expect(arrivalText(null, [mine("m1")])).toBeNull();
    expect(arrivalText(new Set(["m1"]), [mine("m1")])).toBeNull();
  });

  it("names the sender of one new Message, and counts several", () => {
    expect(arrivalText(new Set(["m1"]), [mine("m2", "Kari"), mine("m1")])).toBe("Ny melding fra Kari.");
    expect(arrivalText(new Set(), [mine("m3"), mine("m2")])).toBe("Nye meldinger: 2.");
    expect(arrivalText(new Set(), [mine("m3", null)])).toBe("Ny melding fra Faglærer.");
  });
});
