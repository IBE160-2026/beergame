import { describe, expect, it } from "vitest";

import { messagePath } from "@/modules/identity/homes";

import type { MessageForm } from "./api";
import { canSend, keyFor, messageTitle, recipientFrom, sendErrors } from "./message-form";

const SESSION = "0190b8a4-1a2b-7c3d-8e4f-123456789abc";
const GAME = "0190b8a4-1a2b-7c3d-8e4f-aaaaaaaaaaaa";
const STUDENT = "0190b8a4-1a2b-7c3d-8e4f-bbbbbbbbbbbb";

function form(overrides: Partial<MessageForm> = {}): MessageForm {
  return {
    kind: "class_session",
    class_session_id: SESSION,
    class_id: SESSION,
    class_name: "class-of-2027",
    session_number: 2,
    game_id: null,
    game_number: null,
    student_name: null,
    students: 4,
    sent_before: 3,
    max_length: 2000,
    ...overrides,
  };
}

describe("the Meldingsskjema's recipient (Story 7.9)", () => {
  it("reads the recipient from the page's query and refuses an id that is not one", () => {
    expect(recipientFrom(new URLSearchParams(""))).toEqual({});
    expect(recipientFrom(new URLSearchParams(`spill=${GAME.toUpperCase()}`))).toEqual({ game: GAME });
    expect(recipientFrom(new URLSearchParams(`spill=${GAME}&student=${STUDENT}`))).toEqual({ game: GAME, student: STUDENT });
    expect(recipientFrom(new URLSearchParams("student=noah"))).toBeNull();
  });

  it("builds the page's path for each recipient, and reads it back", () => {
    expect(messagePath(SESSION)).toBe(`/klasseokter/${SESSION}/melding`);
    expect(messagePath(SESSION, { game: GAME })).toBe(`/klasseokter/${SESSION}/melding?spill=${GAME}`);
    const path = messagePath(SESSION, { game: GAME, student: STUDENT });
    expect(recipientFrom(new URL(path, "http://x").searchParams)).toEqual({ game: GAME, student: STUDENT });
  });

  it("titles the form with the recipient", () => {
    expect(messageTitle(form({ kind: "student", student_name: "Noah", game_id: GAME, game_number: 2 }))).toBe(
      "Melding til Noah, Spill 2",
    );
    expect(messageTitle(form({ kind: "student", student_name: "Noah" }))).toBe("Melding til Noah");
    expect(messageTitle(form({ kind: "class_game", game_id: GAME, game_number: 7 }))).toBe("Melding til Spill 7");
    expect(messageTitle(form())).toBe("Melding til alle i Klasseøkt 2");
  });
});

describe("«Send Melding» (Story 7.9)", () => {
  it("acts only with text, someone to send to and no send under way", () => {
    expect(canSend("", form(), false)).toBe(false);
    expect(canSend(" \n ", form(), false)).toBe(false);
    expect(canSend("Hei", form(), false)).toBe(true);
    expect(canSend("Hei", form(), true)).toBe(false);
    expect(canSend("Hei", form({ students: 0 }), false)).toBe(false);
  });

  it("keeps the key while the text is the same, and makes a new one once it changed", () => {
    let n = 0;
    const make = () => `key-${++n}`;
    const first = keyFor(null, "Hei", make);
    expect(first).toEqual({ key: "key-1", text: "Hei" });
    expect(keyFor(first, "Hei", make)).toBe(first);
    expect(keyFor(first, "Hei igjen", make)).toEqual({ key: "key-2", text: "Hei igjen" });
  });

  it("words the length refusal with the limit", () => {
    expect(sendErrors(form()).message_too_long).toBe("Meldingen er for lang. Høyst 2 000 tegn.");
  });
});
