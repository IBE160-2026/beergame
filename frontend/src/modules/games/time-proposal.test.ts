import { describe, expect, it } from "vitest";

import { nb } from "@/copy/nb";
import { ApiRequestError } from "@/lib/api/client";

import {
  checkProposal,
  proposalAt,
  proposalLines,
  refusedRange,
  shownProposal,
  type TimeProposal,
} from "./time-proposal";

const copy = nb.games.timeProposal;
const DEADLINE = "2026-12-08T13:00:00Z"; // ti. 8. des. kl. 14:00 in Oslo
const NOW = Date.parse("2026-11-25T09:00:00Z");
const RANGE = "Velg et tidspunkt mellom nå og Spillfristen, ti. 8. des. kl.\u00a014:00.";

const proposal = (over: Partial<TimeProposal> = {}): TimeProposal => ({
  id: "p1",
  at: "2026-11-26T13:15:00Z",
  proposed_by: { name: "Kari Nordmann", mine: false },
  accepted_by: [],
  can_accept: true,
  ...over,
});

describe("the proposal line (Story 6.19)", () => {
  it("names who proposed which time, in Europe/Oslo, and who accepted", () => {
    expect(proposalLines(proposal())).toEqual({
      proposed: "Kari Nordmann foreslår å spille to. 26. nov. kl.\u00a014:15.",
      accepted: copy.noneAccepted,
    });
    const accepted = proposal({
      proposed_by: { name: "Demo Student", mine: true },
      accepted_by: [
        { name: "Per Hansen", mine: false },
        { name: null, mine: false },
        { name: "Ola", mine: true },
      ],
    });
    expect(proposalLines(accepted)).toEqual({
      proposed: "Du foreslår å spille to. 26. nov. kl.\u00a014:15.",
      accepted: "Godtatt av Per Hansen, En Student og deg.",
    });
  });

  it("is gone once its time has passed on the server's clock", () => {
    expect(shownProposal(proposal(), NOW)).not.toBeNull();
    expect(shownProposal(proposal(), Date.parse("2026-11-26T13:15:00Z"))).toBeNull();
    expect(shownProposal(null, NOW)).toBeNull();
  });
});

describe("the proposal form (Story 6.19)", () => {
  it("asks for a date and a time, never read as empty in silence", () => {
    expect(checkProposal({ date: "", time: "" }, NOW, DEADLINE)).toEqual({
      date: copy.errors.dateMissing,
      time: copy.errors.timeMissing,
    });
    expect(checkProposal({ date: "", time: "14:15" }, NOW, DEADLINE, { date: true })).toEqual({
      date: copy.errors.dateMissing,
    });
  });

  it("takes a time after now and not after the Play deadline, and says the range otherwise", () => {
    expect(checkProposal({ date: "2026-11-26", time: "14:15" }, NOW, DEADLINE)).toEqual({});
    expect(checkProposal({ date: "2026-12-08", time: "14:00" }, NOW, DEADLINE)).toEqual({}); // the deadline itself
    expect(checkProposal({ date: "2026-12-08", time: "14:01" }, NOW, DEADLINE)).toEqual({ time: RANGE });
    expect(checkProposal({ date: "2026-11-25", time: "10:00" }, NOW, DEADLINE)).toEqual({ time: RANGE }); // now
  });

  it("sends the Oslo wall time as an instant, and maps the api's range refusal", () => {
    expect(proposalAt({ date: "2026-11-26", time: "14:15" })).toBe("2026-11-26T13:15:00.000Z");
    const refused = new ApiRequestError(422, "time_out_of_range");
    expect(refusedRange(refused, DEADLINE)).toEqual({ time: RANGE });
    expect(refusedRange(new Error("x"), DEADLINE)).toBeNull();
  });
});
