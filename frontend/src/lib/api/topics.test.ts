import { QueryClient } from "@tanstack/react-query";
import { describe, expect, it } from "vitest";

import { classesKey, enrolledClassesKey } from "@/modules/classes/api";
import { debriefsKey, sessionQuizKey, staffSummaryKey } from "@/modules/debrief/api";
import {
  classOverviewKey,
  gameInsightKey,
  myGameKey,
  playKey,
  startGamesKey,
  startingTaskKey,
  waitedForSeatsKey,
} from "@/modules/games/api";
import { meKey } from "@/modules/identity/api";
import { messageFormKey, myMessagesKey, sentMessagesKey } from "@/modules/messaging/api";
import { studentPageKey } from "@/modules/reports/api";
import { walkthroughKey } from "@/modules/replay/api";
import {
  allocationKey,
  classSessionKey,
  classSessionsKey,
  enrolledSessionsKey,
  lecturerHomeKey,
  seatChoiceKey,
} from "@/modules/sessions/api";

import { parseEvent, topicKeys } from "./topics";

/** Which of `keys` an event invalidates, through the query cache's own prefix match. */
function invalidated(event: Parameters<typeof topicKeys>[0], keys: readonly (readonly unknown[])[]) {
  const client = new QueryClient();
  for (const key of keys) client.setQueryData(key, 1);
  for (const queryKey of topicKeys(event)) void client.invalidateQueries({ queryKey, refetchType: "none" });
  return keys.filter((key) => client.getQueryState(key)?.isInvalidated);
}

const ALL = [
  meKey,
  enrolledSessionsKey,
  enrolledClassesKey,
  classesKey,
  lecturerHomeKey,
  seatChoiceKey("s1"),
  classSessionKey("s1"),
  classSessionKey("s2"),
  allocationKey("s1"),
  allocationKey("s2"),
  classSessionsKey("c1"),
  myGameKey("g1"),
  startingTaskKey("g1"),
  playKey("g1"),
  myGameKey("g2"),
  classOverviewKey("s1"),
  classOverviewKey("s2"),
  gameInsightKey("g1"),
  gameInsightKey("g2"),
  myMessagesKey,
  sentMessagesKey("s1"),
  sentMessagesKey("s2"),
  messageFormKey("s1", {}),
  messageFormKey("s1", { requirement: true }),
  studentPageKey("s1", "u1"),
  studentPageKey("s2", "u1"),
  startGamesKey("s1"),
  startGamesKey("s2"),
  waitedForSeatsKey("s1"),
  waitedForSeatsKey("s2"),
] as const;

describe("topicKeys", () => {
  it("maps user:<id> to Hjem, the enrolled lists, Klassene dine, the Lærerhjem, the seat choice, own games and Messages", () => {
    expect(invalidated({ topic: "user", id: "u1", version: null }, ALL)).toEqual([
      meKey,
      enrolledSessionsKey,
      enrolledClassesKey,
      classesKey,
      lecturerHomeKey,
      seatChoiceKey("s1"),
      // `classesKey` is ["classes"]: the Class detail and list pages read again too.
      myGameKey("g1"),
      startingTaskKey("g1"),
      playKey("g1"),
      myGameKey("g2"),
      myMessagesKey,
    ]);
  });

  it("reads a waiting Replay-gjennomgang again on user:<id>, when its line is stored (Story 10.7)", () => {
    expect(invalidated({ topic: "user", id: "u1", version: null }, [walkthroughKey("g1")])).toEqual([walkthroughKey("g1")]);
  });

  it("maps session:<id> to that Klasseøkt, its allocation, the Lærerhjem, the Class's session list, its Oversikt and «Meldinger»", () => {
    expect(invalidated({ topic: "session", id: "s1", version: null }, ALL)).toEqual([
      lecturerHomeKey,
      classSessionKey("s1"),
      allocationKey("s1"),
      classSessionsKey("c1"),
      classOverviewKey("s1"),
      sentMessagesKey("s1"),
      // The Oversikt's Lenke to those who have not met the requirement (Story 13.6), not any other
      // recipient's form.
      messageFormKey("s1", { requirement: true }),
      // The Studentsides of the Class session (Story 8.9).
      studentPageKey("s1", "u1"),
      // Its «Start spill» page (Story 8.10).
      startGamesKey("s1"),
      // Its «Sett inn KI-spillere» page (Story 8.12).
      waitedForSeatsKey("s1"),
    ]);
  });

  it("maps session:<id> to its Debrief quiz block and its Students' Debrief summaries (Story 9.10)", () => {
    const keys = [sessionQuizKey("s1"), sessionQuizKey("s2"), staffSummaryKey("s1", "u1"), staffSummaryKey("s2", "u1")];
    expect(invalidated({ topic: "session", id: "s1", version: null }, keys)).toEqual([
      sessionQuizKey("s1"),
      staffSummaryKey("s1", "u1"),
    ]);
  });

  it("maps game:<id> to that game and what hangs under it, the play envelope too, Hjem and its Spillinnsikt", () => {
    expect(invalidated({ topic: "game", id: "g1", version: 4 }, ALL)).toEqual([
      enrolledSessionsKey,
      myGameKey("g1"),
      startingTaskKey("g1"),
      playKey("g1"),
      gameInsightKey("g1"),
    ]);
  });

  it("maps a Debrief to the Debrief queries (Story 9.2)", () => {
    expect(topicKeys({ topic: "debrief", id: "d1", version: null })).toEqual([debriefsKey]);
    expect(topicKeys({ topic: "user", id: "u1", version: null })).toContainEqual(debriefsKey);
  });

  it("maps an unknown topic to nothing", () => {
    expect(topicKeys({ topic: "replay", id: "r1", version: null })).toEqual([]);
  });
});

describe("parseEvent", () => {
  it("reads topic, id and version", () => {
    expect(parseEvent('{"topic":"game","id":"g1","version":3}')).toEqual({ topic: "game", id: "g1", version: 3 });
    expect(parseEvent('{"topic":"user","id":"u1","version":null}')).toEqual({ topic: "user", id: "u1", version: null });
  });

  it("refuses what is not an event", () => {
    for (const data of ["", "x", "null", "[]", '{"topic":1,"id":"a","version":null}', '{"topic":"user","version":null}', '{"topic":"user","id":"","version":null}', '{"topic":"game","id":"g","version":"3"}']) {
      expect(parseEvent(data)).toBeNull();
    }
  });
});
