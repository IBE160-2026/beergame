import { nb } from "@/copy/nb";
import { ApiRequestError } from "@/lib/api/client";
import { fromOsloInput, osloDateText } from "@/modules/sessions/dates";

import type { MyGame } from "./api";

const copy = nb.games.timeProposal;

/** The game's open proposal of a time to play (Story 6.19), as the api answers it. */
export type TimeProposal = NonNullable<MyGame["time_proposal"]>;
type Person = TimeProposal["proposed_by"];

/** The form as typed: a date «2026-11-26» and a time «14:15», in Europe/Oslo. Nothing else. */
export type ProposalInputs = { date: string; time: string };
export type ProposalField = keyof ProposalInputs;
export type ProposalErrors = Partial<Record<ProposalField, string>>;
export const EMPTY_PROPOSAL: ProposalInputs = { date: "", time: "" };

/** The proposal while its time lies ahead on the server's clock (`now`, ms); null once it has
 * passed, so an open page drops it at once (the api leaves it out on the next read). */
export function shownProposal(proposal: TimeProposal | null | undefined, now: number): TimeProposal | null {
  return proposal && Date.parse(proposal.at) > now ? proposal : null;
}

function nameOf(person: Person): string {
  return person.mine ? copy.you : (person.name ?? copy.someone);
}

/** «Kari Nordmann foreslår å spille to. 26. nov. kl. 14:15.» and «Godtatt av Per Hansen og deg.»,
 * or «Ingen har godtatt ennå.». */
export function proposalLines(proposal: TimeProposal): {
  proposed: string;
  accepted: string;
} {
  const when = osloDateText(proposal.at);
  const proposed = proposal.proposed_by.mine
    ? copy.proposedMine(when)
    : copy.proposed(proposal.proposed_by.name ?? copy.someone, when);
  const names = proposal.accepted_by.map(nameOf);
  return {
    proposed,
    accepted: names.length > 0 ? copy.acceptedBy(nb.sessions.chain.list(names)) : copy.noneAccepted,
  };
}

/** The range error: «Velg et tidspunkt mellom nå og Spillfristen, ti. 8. des. kl. 14:00.» */
export function rangeError(playDeadline: string): string {
  return copy.errors.range(osloDateText(playDeadline));
}

/**
 * What the form says before anything is sent: an empty or half-typed field its own reason, and a
 * time not after `now` (the server's clock, ms) or after the Play deadline the range error under
 * the time field. The api judges the same rule again (`time_out_of_range`).
 */
export function checkProposal(
  inputs: ProposalInputs,
  now: number,
  playDeadline: string,
  halfTyped: Partial<Record<ProposalField, boolean>> = {},
): ProposalErrors {
  const errors: ProposalErrors = {};
  if (halfTyped.date || !inputs.date) errors.date = copy.errors.dateMissing;
  if (halfTyped.time || !inputs.time) errors.time = copy.errors.timeMissing;
  if (errors.date || errors.time) return errors;
  const at = fromOsloInput(`${inputs.date}T${inputs.time}`);
  if (at === null) return { date: copy.errors.dateMissing };
  const ms = Date.parse(at);
  if (!(ms > now) || ms > Date.parse(playDeadline)) errors.time = rangeError(playDeadline);
  return errors;
}

/** The instant the api takes; only called once `checkProposal` found nothing. */
export function proposalAt(inputs: ProposalInputs): string {
  return fromOsloInput(`${inputs.date}T${inputs.time}`) ?? "";
}

/** The api's refusal as the field reason (`time_out_of_range`), or null for another failure. */
export function refusedRange(error: unknown, playDeadline: string): ProposalErrors | null {
  return error instanceof ApiRequestError && error.code === "time_out_of_range"
    ? { time: rangeError(playDeadline) }
    : null;
}
