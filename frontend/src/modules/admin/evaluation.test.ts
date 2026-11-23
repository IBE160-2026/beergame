import { describe, expect, it } from "vitest";

import { nb } from "@/copy/nb";
import { ApiRequestError } from "@/lib/api/client";

import {
  agreementErrors,
  formatDay,
  keyError,
  outcomeText,
  runRefusal,
  sessionLabel,
  shortFingerprint,
  todayInOslo,
} from "./evaluation";

const copy = nb.admin.evaluation;
const KEY = "k".repeat(32);

describe("«Pseudonymisert eksport» (Story 15.4)", () => {
  it("names a Class session and a calendar day without a time zone shift", () => {
    expect(sessionLabel({ class_name: "class-of-1994", number: 2 })).toBe("class-of-1994 · Klasseøkt 2");
    expect(formatDay("2027-05-17")).toBe(`17. ${nb.admin.users.invitations.months[4]} 2027`);
    expect(todayInOslo(new Date("2026-11-22T23:30:00Z"))).toBe("2026-11-23");
  });

  it("checks the agreement as the api does", () => {
    const today = "2026-11-22";
    expect(agreementErrors({ agreedBy: " Prorektor ", agreedOn: today, controller: "Høgskolen" }, today)).toEqual({});
    expect(agreementErrors({ agreedBy: "  ", agreedOn: "", controller: "x".repeat(201) }, today)).toEqual({
      agreedBy: copy.agreementForm.required,
      agreedOn: copy.agreementForm.required,
      controller: copy.agreementForm.tooLong,
    });
    expect(agreementErrors({ agreedBy: "a", agreedOn: "2026-11-23", controller: "b" }, today)).toEqual({
      agreedOn: copy.agreementForm.inFuture,
    });
  });

  it("checks the key's length without its outer whitespace", () => {
    expect(keyError(`  ${KEY}  `)).toBeUndefined();
    expect(keyError(`  ${KEY.slice(1)}  `)).toBe(copy.run.keyTooShort);
    expect(keyError("x".repeat(513))).toBe(copy.run.keyTooLong);
  });

  it("words each refusal of a run", () => {
    expect(runRefusal(new ApiRequestError(409, "pseudonym_key_changed"))).toBe(copy.run.keyChanged);
    expect(runRefusal(new ApiRequestError(403, "no_agreement", { class_session_ids: [] }))).toBe(copy.run.noAgreement);
    expect(runRefusal(new ApiRequestError(422, "invalid_request", { key: "too_short" }))).toBe(copy.run.keyTooShort);
    expect(runRefusal(new ApiRequestError(0, "network_error"))).toBe(copy.run.failed);
  });

  it("shortens a fingerprint and words an outcome", () => {
    expect(shortFingerprint("0123456789abcdef".repeat(4))).toBe("0123 4567 89ab cdef");
    expect(outcomeText("exported")).toBe(copy.exports.outcomes.exported);
    expect(outcomeText("something_new")).toBe("something_new");
  });
});
