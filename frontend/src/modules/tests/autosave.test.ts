import { describe, expect, it } from "vitest";

import { nb } from "@/copy/nb";
import { ApiRequestError } from "@/lib/api/client";

import {
  applyFailed,
  applyRefused,
  applySaved,
  choose,
  draftField,
  draftText,
  initial,
  LONG_ANSWER_MAX,
  merge,
  parseDraft,
  pasteIsCut,
  refusedForGood,
  statusLine,
} from "./autosave";

const copy = nb.tests.individual;
const AT = "2026-11-22T20:14:00Z"; // 21:14 in Oslo

describe("the autosave of an Individual test answer (Story 11.4, AD-10)", () => {
  it("starts from the stored answer, sends a newer draft and drops an older one", () => {
    const stored = { value: "a", revision: 2, saved_at: AT };
    const plain = initial(stored, null);
    expect(plain).toMatchObject({ send: false, drop: false, entry: { value: "a", revision: 2, stored: 2, status: "idle" } });
    expect(statusLine(plain.entry, "")).toBe("");

    const newer = initial(stored, draftText({ value: "c", revision: 3 }));
    expect(newer).toMatchObject({ send: true, drop: false, entry: { value: "c", revision: 3, stored: 2, storedValue: "a" } });

    expect(initial(stored, draftText({ value: "c", revision: 2 }))).toMatchObject({ send: false, drop: true, entry: { value: "a" } });
    expect(initial(null, "not json")).toMatchObject({ send: false, drop: true, entry: { value: null, revision: 0 } });
    expect(initial(null, draftText({ value: "b", revision: 1 })).entry).toMatchObject({ value: "b", revision: 1, stored: 0 });
  });

  it("tells when a paste into a long answer goes past the longest answer (Story 11.6)", () => {
    expect(pasteIsCut(0, 0, LONG_ANSWER_MAX)).toBe(false);
    expect(pasteIsCut(0, 0, LONG_ANSWER_MAX + 1)).toBe(true);
    expect(pasteIsCut(LONG_ANSWER_MAX, 10, 10)).toBe(false);
    expect(pasteIsCut(LONG_ANSWER_MAX - 5, 0, 6)).toBe(true);
  });

  it("raises the revision by one per change", () => {
    const { entry } = initial(null, null);
    const once = choose(entry, "a");
    const twice = choose(once, "b");
    expect([once.revision, twice.revision, twice.value, twice.status]).toEqual([1, 2, "b", "saving"]);
  });

  it("shows «Lagret 21:14» in Oslo time once stored, and sends again when a newer change waits", () => {
    const picked = choose(initial(null, null).entry, "a");
    const { entry: saved, done } = applySaved(picked, { value: "a", revision: 1, saved_at: AT });
    expect(done).toBe(true);
    expect(statusLine(saved, "")).toBe(copy.saved("21:14"));
    expect(statusLine(saved, "")).toBe("Lagret 21:14");

    const moved = choose(picked, "b"); // revision 2 picked while 1 was on its way
    const waiting = applySaved(moved, { value: "a", revision: 1, saved_at: AT });
    expect(waiting.done).toBe(false);
    expect(waiting.entry).toMatchObject({ value: "b", revision: 2, stored: 1, status: "saving" });
  });

  it("takes an answer stored from a higher revision on another device", () => {
    const picked = choose(initial({ value: "a", revision: 2, saved_at: AT }, null).entry, "b"); // revision 3
    const { entry, done } = applySaved(picked, { value: "c", revision: 4, saved_at: AT });
    expect(done).toBe(true);
    expect(entry).toMatchObject({ value: "c", revision: 4, stored: 4 });
  });

  it("keeps a failed save with the spine's line, and keeps the last line while it runs again", () => {
    const failed = applyFailed(choose(initial(null, null).entry, "a"));
    const line = statusLine(failed, "");
    expect(line).toBe("Ikke lagret. Svarene ligger på denne enheten, og vi prøver igjen.");
    expect(statusLine({ ...failed, status: "saving" }, line)).toBe(line);
    expect(failed.value).toBe("a");
  });

  it("a refusal for good shows the stored value again with why", () => {
    const picked = choose(initial({ value: "a", revision: 1, saved_at: AT }, null).entry, "b");
    const refused = applyRefused(picked, "attempt_submitted");
    expect(refused).toMatchObject({ value: "a", revision: 1, status: "refused" });
    expect(statusLine(refused, "")).toBe(copy.saveErrors.attempt_submitted);
    expect(statusLine(applyRefused(picked, "unknown_item"), "")).toBe(copy.saveRefused);
  });

  it("tells a refusal for good from a failure worth trying again", () => {
    expect(refusedForGood(new ApiRequestError(409, "attempt_submitted"))).toBe(true);
    expect(refusedForGood(new ApiRequestError(422, "invalid_answer"))).toBe(true);
    expect(refusedForGood(new ApiRequestError(403, "forbidden"))).toBe(true);
    expect(refusedForGood(new ApiRequestError(0, "network_error"))).toBe(false);
    expect(refusedForGood(new ApiRequestError(503, "unavailable"))).toBe(false);
    expect(refusedForGood(new ApiRequestError(401, "session_expired"))).toBe(false);
    expect(refusedForGood(new ApiRequestError(400, "bad_request"))).toBe(false);
    expect(refusedForGood(new ApiRequestError(404, "not_found"))).toBe(false);
    expect(refusedForGood(new ApiRequestError(429, "rate_limited"))).toBe(false);
    expect(refusedForGood(new Error("x"))).toBe(false);
  });

  it("a test read again replaces only a lower revision", () => {
    const picked = choose(initial({ value: "a", revision: 1, saved_at: AT }, null).entry, "b"); // 2
    expect(merge(picked, { value: "c", revision: 2, saved_at: AT })).toBe(picked);
    expect(merge(picked, null)).toBe(picked);
    expect(merge(picked, { value: "c", revision: 5, saved_at: AT })).toMatchObject({ value: "c", revision: 5, stored: 5 });
  });

  it("keeps drafts per Class session and item, and reads only well-formed ones", () => {
    expect(draftField("s1", "flervalg-1")).toBe("test:s1:flervalg-1");
    expect(parseDraft(draftText({ value: "a", revision: 4 }))).toEqual({ value: "a", revision: 4 });
    for (const bad of [
      null,
      "",
      "[]",
      '{"value":1.5,"revision":1}',
      '{"value":[1,"x"],"revision":1}',
      '{"value":{"a":1},"revision":1}',
      '{"revision":1}',
      '{"value":"a","revision":0}',
      '{"value":"a","revision":1.5}',
    ]) {
      expect(parseDraft(bad)).toBeNull();
    }
  });

  it("keeps a number and a table answer like a choice (Story 11.5)", () => {
    expect(parseDraft(draftText({ value: [8, null, -3], revision: 2 }))).toEqual({ value: [8, null, -3], revision: 2 });
    expect(parseDraft(draftText({ value: 16, revision: 1 }))).toEqual({ value: 16, revision: 1 });
    expect(parseDraft(draftText({ value: null, revision: 3 }))).toEqual({ value: null, revision: 3 });
    const table = initial({ value: [8, null], revision: 1, saved_at: AT }, draftText({ value: [8, 4], revision: 2 }));
    expect(table).toMatchObject({ send: true, entry: { value: [8, 4], storedValue: [8, null], revision: 2 } });
    const cleared = choose(initial({ value: 16, revision: 1, saved_at: AT }, null).entry, null);
    expect(cleared).toMatchObject({ value: null, revision: 2, status: "saving" });
    const { entry } = applySaved(cleared, { value: null, revision: 2, saved_at: AT });
    expect(entry).toMatchObject({ value: null, storedValue: null, stored: 2, status: "saved" });
  });
});

describe("a long answer's draft (Story 11.6)", () => {
  it("keeps the text exactly as typed, also emptied, and a session that ended keeps it", () => {
    const text = "  Forsinkelsen gjør at ordren kommer senere.\n\nDerfor …  ";
    expect(parseDraft(draftText({ value: text, revision: 7 }))).toEqual({ value: text, revision: 7 });
    expect(parseDraft(draftText({ value: "", revision: 8 }))).toEqual({ value: "", revision: 8 });
    // After a new login the draft is above the stored revision: shown and sent.
    const back = initial({ value: "Eldre", revision: 4, saved_at: AT }, draftText({ value: text, revision: 7 }));
    expect(back).toMatchObject({ send: true, entry: { value: text, revision: 7, stored: 4, status: "saving" } });
    // An ended session is not refused for good: the draft stays.
    expect(refusedForGood(new ApiRequestError(401, "session_expired"))).toBe(false);
  });
});
