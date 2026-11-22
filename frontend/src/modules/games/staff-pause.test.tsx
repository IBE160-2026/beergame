import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import type { ReactNode } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import { nb } from "@/copy/nb";

import type { GameInsight } from "./api";
import { OverviewBand } from "./overview-band";
import { pauseText } from "./pause-view";
import { Spillstyring } from "./spillstyring";
import {
  agreedAt,
  agreedInputs,
  checkAgreed,
  confirmLabel,
  doneText,
  EMPTY_AGREED,
  insightPauseText,
  StaffPauseForm,
} from "./staff-pause";
import { rangeError } from "./time-proposal";

const copy = nb.spillstyring.pause;
const student = nb.homes.student.pause;

function html(node: ReactNode): string {
  return renderToStaticMarkup(<QueryClientProvider client={new QueryClient()}>{node}</QueryClientProvider>);
}

// Thursday 26 November 2026, 19:00 in Oslo (UTC+1).
const THURSDAY_19 = "2026-11-26T18:00:00.000Z";
const NOW = Date.parse("2026-11-23T13:10:00Z"); // Monday 14:10 in Oslo
const DEADLINE = "2026-12-08T13:00:00Z";
const AT_19 = { date: "2026-11-26", time: "19:00", noTime: false };

describe("the Lecturer's pause form", () => {
  it("names the time on the primary, or says there is none", () => {
    expect(confirmLabel("pause", AT_19)).toBe("Ta pause til to. 19:00");
    expect(confirmLabel("pause", { ...AT_19, noTime: true })).toBe("Ta pause uten avtalt tid");
    expect(confirmLabel("pause", EMPTY_AGREED)).toBe("Ta pause");
    expect(confirmLabel("change", AT_19)).toBe("Lagre avtalt tid to. 19:00");
    expect(confirmLabel("change", { ...AT_19, noTime: true })).toBe("Lagre uten avtalt tid");
    expect(agreedAt(AT_19)).toBe(THURSDAY_19);
    expect(agreedAt({ ...AT_19, noTime: true })).toBeNull();
  });

  it("is prefilled with the agreed time in force on «Endre avtalt tid»", () => {
    expect(agreedInputs(THURSDAY_19)).toEqual(AT_19);
    expect(agreedInputs(null)).toEqual(EMPTY_AGREED);
  });

  it("says a time outside now to the Spillfrist under the time field", () => {
    expect(checkAgreed(AT_19, NOW, DEADLINE)).toEqual({});
    const range = rangeError(DEADLINE);
    expect(checkAgreed({ ...AT_19, date: "2026-12-09" }, NOW, DEADLINE)).toEqual({ time: range });
    expect(checkAgreed({ ...AT_19, date: "2026-11-20" }, NOW, DEADLINE)).toEqual({ time: range });
    expect(checkAgreed(EMPTY_AGREED, NOW, DEADLINE)).toEqual({
      date: nb.games.timeProposal.errors.dateMissing,
      time: nb.games.timeProposal.errors.timeMissing,
    });
    expect(checkAgreed({ ...EMPTY_AGREED, noTime: true }, NOW, DEADLINE)).toEqual({});
    expect(checkAgreed({ ...AT_19, date: "2026-11-20" }, NOW, null)).toEqual({ time: copy.afterNow });
  });

  it("opens with Dato first, the two lines, the primary and «Avbryt»", () => {
    const form = html(
      <StaffPauseForm
        gameId="g1"
        sessionId="s1"
        mode="pause"
        playDeadline={DEADLINE}
        now={() => NOW}
        onCancel={() => {}}
        onDone={() => {}}
      />,
    );
    expect(form.indexOf(copy.title)).toBeLessThan(form.indexOf(copy.date));
    expect(form.indexOf('type="date"')).toBeLessThan(form.indexOf('type="time"'));
    for (const text of [copy.noTime, copy.noTakeover, copy.afterTime, copy.confirm, copy.cancel]) {
      expect(form).toContain(text);
    }
    expect(form.match(/data-staff-pause-confirm/g)).toHaveLength(1);
  });

  it("states the result and the paused line on Spillinnsikt", () => {
    expect(doneText(THURSDAY_19)).toBe("Pause til to. 19:00 er satt.");
    expect(doneText(null)).toBe(copy.doneNoTime);
    const pause = { paused_at: "2026-11-23T13:10:00Z", by: "Sara", mine: false, resume_at: null };
    expect(insightPauseText(pause)).toBe("Pause siden ma. 14:10, satt av Sara.");
    expect(insightPauseText({ ...pause, mine: true, resume_at: THURSDAY_19 })).toBe(
      "Pause siden ma. 14:10, satt av deg. Avtalt tid to. 19:00.",
    );
  });
});

describe("the Students' line after a Lecturer's Pause", () => {
  it("names the Lecturer and only the Lecturer's agreed time", () => {
    const paused = { state: "paused" as const, name: null, mine: false, staff: true };
    expect(pauseText(paused)).toBe(student.pausedByLecturer);
    expect(pauseText({ ...paused, resume_at: THURSDAY_19 })).toBe("Pause til to. 19:00, satt av faglæreren.");
    // A Student's Pause with the Lecturer's agreed time reads as the Lecturer's.
    expect(pauseText({ ...paused, staff: false, name: "Sara", resume_at: THURSDAY_19 })).toBe(
      "Pause til to. 19:00, satt av faglæreren.",
    );
    expect(pauseText({ state: "ended", name: null, mine: false, staff: true })).toBe(student.endedByLecturer);
  });
});

function insight(over: Partial<GameInsight>): GameInsight {
  return {
    game_id: "g1",
    class_session_id: "s1",
    class_id: "c1",
    class_name: "Klasse",
    session_number: 1,
    game_number: 2,
    status: "running",
    version: 1,
    weeks_total: 20,
    demand: [],
    seats: [],
    roles: [],
    can_pause: true,
    can_adjust: false,
    can_start: false,
    can_mark_in_room: false,
    play_deadline: DEADLINE,
    ...over,
  };
}

describe("Spillstyring's Pause", () => {
  it("offers «Pause spillet» to a Lecturer under a label-sized title, and nothing to an Assistant", () => {
    const lecturer = html(<Spillstyring data={insight({})} />);
    expect(lecturer).toContain('class="text-label text-ink"');
    expect(lecturer).toContain(copy.open);
    expect(html(<Spillstyring data={insight({ can_pause: false })} />)).toBe("");
    // An Assistant lecturer keeps the per-Seat rows, and gets no Pause control.
    const seat = {
      role: "factory" as const,
      holder: "student" as const,
      name: "Jonas",
      user_id: "u-jonas",
      links: [],
      takeover: "this_week" as const,
      extra_time: false,
    };
    const assistant = html(<Spillstyring data={insight({ can_pause: false, seats: [seat] })} />);
    expect(assistant).toContain('data-takeover="factory"');
    expect(assistant).not.toContain("data-spillstyring-pause");
    expect(assistant).not.toContain(copy.open);
  });

  it("offers no «Pause spillet» in the Varselbånd without `canPause`", () => {
    const alert = {
      game_id: "g1",
      game_number: 2,
      role: "factory" as const,
      name: "Noah",
      user_id: "u-noah",
      since: "2026-11-23T12:00:00Z",
      takeover_due_at: "2026-11-24T12:00:00Z",
    };
    const now = Date.parse("2026-11-23T13:00:00Z");
    expect(html(<OverviewBand alert={alert} sessionId="s1" now={now} />)).not.toContain("data-band-pause");
    expect(html(<OverviewBand alert={alert} sessionId="s1" now={now} canPause />)).toContain("data-band-pause");
  });

  it("shows the paused line with «Endre avtalt tid» and «Avslutt pausen»", () => {
    const pause = { paused_at: "2026-11-23T13:10:00Z", by: "Sara", mine: false, resume_at: THURSDAY_19 };
    const paused = html(<Spillstyring data={insight({ status: "paused", pause })} />);
    expect(paused).toContain("Pause siden ma. 14:10, satt av Sara. Avtalt tid to. 19:00.");
    expect(paused).toContain(copy.change);
    expect(paused).toContain(copy.end);
    expect(paused).not.toContain(copy.open);
  });
});
