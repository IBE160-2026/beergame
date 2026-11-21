import { QueryClient } from "@tanstack/react-query";
import { describe, expect, it } from "vitest";

import { classesKey, enrolledClassesKey } from "@/modules/classes/api";
import { classOverviewKey, gameInsightKey, myGameKey, playKey, startingTaskKey } from "@/modules/games/api";
import { meKey } from "@/modules/identity/api";
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
] as const;

describe("topicKeys", () => {
  it("maps user:<id> to Hjem, the enrolled lists, Klassene dine, the Lærerhjem, the seat choice and own games", () => {
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
    ]);
  });

  it("maps session:<id> to that Klasseøkt, its allocation, the Lærerhjem, the Class's session list and its Oversikt", () => {
    expect(invalidated({ topic: "session", id: "s1", version: null }, ALL)).toEqual([
      lecturerHomeKey,
      classSessionKey("s1"),
      allocationKey("s1"),
      classSessionsKey("c1"),
      classOverviewKey("s1"),
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

  it("maps an unknown topic to nothing", () => {
    expect(topicKeys({ topic: "debrief", id: "d1", version: null })).toEqual([]);
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
