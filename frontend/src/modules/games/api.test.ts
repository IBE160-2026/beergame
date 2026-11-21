import { describe, expect, it } from "vitest";

import { ApiRequestError, createApiClient } from "@/lib/api/client";

import { type ClassOverview, readOverview } from "./api";

const OVERVIEW = {
  items: [],
  next_cursor: null,
  counts: { waiting: 0, running: 1, not_started: 0, finished: 0, paused: 0 },
  server_now: "2026-11-21T13:02:15Z",
  before_start: false,
  start_at: "2026-11-20T08:00:00Z",
  next_change_at: null,
  ai: { seats: 0, games: 0 },
  cost: null,
  funnel: [{ stage: "registered", count: 0 }],
  alert: null,
  can_pause: false,
  class_id: "c1",
  class_name: "klasse",
  session_number: 1,
} satisfies ClassOverview;

/** A client whose server answers `status` (with the overview and an ETag on 200) and records each
 * request's `If-None-Match`. */
function server(status: number) {
  const sent: (string | null)[] = [];
  const fetch = async (input: Request) => {
    sent.push(input.headers.get("If-None-Match"));
    if (status === 304) return new Response(null, { status: 304, headers: { ETag: '"a"' } });
    const body = status === 200 ? OVERVIEW : { code: "server_error", message: "x" };
    return new Response(JSON.stringify(body), {
      status,
      headers: { "content-type": "application/json", ETag: '"a"' },
    });
  };
  return { sent, client: createApiClient({ baseUrl: "http://t", fetch: fetch as unknown as typeof globalThis.fetch }) };
}

describe("readOverview (Story 7.5, AD-25)", () => {
  it("keeps the ETag of an answer and sends none on the first read", async () => {
    const { sent, client } = server(200);
    const answer = await readOverview("s1", undefined, client);
    expect(sent).toEqual([null]);
    expect(answer.etag).toBe('"a"');
    expect(answer.overview.counts.running).toBe(1);
  });

  it("revalidates with the ETag, and a 304 gives back the same answer object", async () => {
    const previous = { overview: OVERVIEW, etag: '"a"', receivedAt: 1 };
    const { sent, client } = server(304);
    const answer = await readOverview("s1", previous, client);
    expect(sent).toEqual(['"a"']);
    expect(answer).toBe(previous);
  });

  it("fails as an api error when the read fails, so the page keeps what it shows", async () => {
    const { client } = server(500);
    await expect(readOverview("s1", { overview: OVERVIEW, etag: '"a"', receivedAt: 1 }, client)).rejects.toBeInstanceOf(
      ApiRequestError,
    );
  });
});
