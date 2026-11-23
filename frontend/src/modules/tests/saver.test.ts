import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { api, ApiRequestError, createApiClient } from "@/lib/api/client";

import { saveMyTestAnswer } from "./api";
import { type Draft, type Entry, initial, LONG_ANSWER_PAUSE_MS, RETRY_MS, type Stored } from "./autosave";
import { AnswerSaver, fitsKeepalive, KEEPALIVE_MAX_BYTES } from "./saver";

const AT = "2026-11-22T20:14:00Z";

/** A save the test answers by hand: `calls` holds each request and its keepalive flag. */
function harness(entry: Entry = initial(null, null).entry) {
  const calls: { draft: Draft; keepalive: boolean; answer: (saved: Stored) => void; fail: (error: unknown) => void }[] = [];
  const hooks = {
    save: vi.fn(
      (draft: Draft, { keepalive }: { keepalive: boolean }) =>
        new Promise<Stored>((answer, fail) => calls.push({ draft, keepalive, answer, fail })),
    ),
    keep: vi.fn(),
    show: vi.fn(),
    stored: vi.fn(),
    refused: vi.fn(),
    failed: vi.fn(),
  };
  const saver = new AnswerSaver(entry, hooks);
  /** Answer the latest open save as stored at its revision. */
  const store = async (index = calls.length - 1) => {
    const call = calls[index]!;
    call.answer({ value: call.draft.value, revision: call.draft.revision, saved_at: AT });
    await flushPromises();
  };
  return { saver, hooks, calls, store };
}

/** Let the settled save's handlers run. */
const flushPromises = async () => {
  for (let i = 0; i < 5; i++) await Promise.resolve();
};

describe("the save loop of one answer (Story 11.4, 11.6, AD-10)", () => {
  beforeEach(() => vi.useFakeTimers());
  afterEach(() => vi.useRealTimers());

  it("keeps a pick on the device, sends it at once and drops the draft once stored", async () => {
    const { saver, hooks, calls, store } = harness();
    saver.pick("a");
    expect(hooks.keep).toHaveBeenCalledWith({ value: "a", revision: 1 });
    expect(calls).toHaveLength(1);
    expect(calls[0]).toMatchObject({ draft: { value: "a", revision: 1 }, keepalive: false });
    await store();
    expect(hooks.stored).toHaveBeenCalledWith({ value: "a", revision: 1, saved_at: AT }, true);
    expect(saver.entry).toMatchObject({ status: "saved", stored: 1 });
  });

  it("runs one save at a time and sends the latest change after it", async () => {
    const { saver, calls, store, hooks } = harness();
    saver.pick("a");
    saver.pick("b");
    expect(calls).toHaveLength(1);
    await store(0);
    expect(hooks.stored).toHaveBeenLastCalledWith(expect.objectContaining({ revision: 1 }), false);
    expect(calls).toHaveLength(2);
    expect(calls[1]!.draft).toEqual({ value: "b", revision: 2 });
  });

  it("sends a long answer when typing pauses, and at once on flush", () => {
    const { saver, calls } = harness();
    saver.write("H");
    saver.write("He");
    expect(calls).toHaveLength(0);
    vi.advanceTimersByTime(LONG_ANSWER_PAUSE_MS);
    expect(calls).toHaveLength(1);
    expect(calls[0]!.draft).toEqual({ value: "He", revision: 2 });
    saver.write("Hei");
    saver.flush();
    // One save runs: the newer text waits for it.
    expect(calls).toHaveLength(1);
  });

  it("sends text typed during an in-flight save after the item leaves the page (the 11.6 fix)", async () => {
    const { saver, calls, store, hooks } = harness();
    saver.write("Hei");
    saver.flush();
    expect(calls).toHaveLength(1);
    // Typed while the first save runs, then the item leaves before the pause ends.
    saver.write("Hei du");
    saver.stop();
    expect(calls).toHaveLength(1);
    await store(0);
    expect(calls).toHaveLength(2);
    expect(calls[1]!.draft).toEqual({ value: "Hei du", revision: 2 });
    // The item has left: nothing more is shown.
    hooks.show.mockClear();
    await store(1);
    expect(hooks.show).not.toHaveBeenCalled();
    expect(hooks.stored).toHaveBeenLastCalledWith(expect.objectContaining({ revision: 2 }), true);
  });

  it("sends with keepalive while the page is hidden, so closing the tab does not cancel the save", () => {
    const { saver, calls } = harness();
    saver.write("Svar");
    saver.hidden = true;
    saver.flush();
    expect(calls).toHaveLength(1);
    expect(calls[0]).toMatchObject({ draft: { value: "Svar", revision: 1 }, keepalive: true });
  });

  it("sends a body over the keepalive limit as a plain request; the draft stays on the device", () => {
    const { saver, calls, hooks } = harness();
    const long = "æ".repeat(20_000) + "ø".repeat(10_000); // 2 bytes each in UTF-8
    expect(fitsKeepalive({ value: long, revision: 1 })).toBe(false);
    expect(fitsKeepalive({ value: "æ".repeat(20_000), revision: 1 })).toBe(true);
    expect(KEEPALIVE_MAX_BYTES).toBeLessThan(64 * 1024);
    saver.write(long);
    saver.hidden = true;
    saver.flush();
    expect(calls[0]).toMatchObject({ keepalive: false });
    expect(hooks.keep).toHaveBeenCalledWith({ value: long, revision: 1 });
  });

  it("tries a failed save again after RETRY_MS, and at once when back online", async () => {
    const { saver, calls, hooks } = harness();
    saver.pick("a");
    calls[0]!.fail(new ApiRequestError(0, "network_error"));
    await flushPromises();
    expect(saver.entry.status).toBe("failed");
    expect(hooks.failed).toHaveBeenCalled();
    vi.advanceTimersByTime(RETRY_MS);
    expect(calls).toHaveLength(2);
    calls[1]!.fail(new ApiRequestError(0, "network_error"));
    await flushPromises();
    saver.online();
    expect(calls).toHaveLength(3);
  });

  it("drops the change and says why when the api refuses it for good", async () => {
    const { saver, calls, hooks } = harness();
    saver.pick("a");
    calls[0]!.fail(new ApiRequestError(409, "attempt_submitted"));
    await flushPromises();
    expect(hooks.refused).toHaveBeenCalled();
    expect(saver.entry).toMatchObject({ status: "refused", value: null, revision: 0 });
    vi.advanceTimersByTime(RETRY_MS);
    expect(calls).toHaveLength(1);
  });

  it("plans no retry after the item has left the page", async () => {
    const { saver, calls } = harness();
    saver.pick("a");
    saver.stop();
    calls[0]!.fail(new ApiRequestError(0, "network_error"));
    await flushPromises();
    vi.advanceTimersByTime(RETRY_MS * 2);
    expect(calls).toHaveLength(1);
  });

  it("passes keepalive on to the browser's fetch", async () => {
    const seen: Request[] = [];
    // openapi-fetch hands its options to `new Request`, which the client's fetch receives.
    const client = createApiClient({
      baseUrl: "http://olspillet.test",
      fetch: async (input: RequestInfo | URL) => {
        seen.push(input as Request);
        return Response.json({ value: "a", revision: 1, saved_at: AT });
      },
    });
    const put = vi.spyOn(api, "PUT").mockImplementation(client.PUT);
    try {
      await saveMyTestAnswer("s", "i", { value: "a", revision: 1 }, { keepalive: true });
      await saveMyTestAnswer("s", "i", { value: "a", revision: 1 });
      expect(seen.map((request) => request.keepalive)).toEqual([true, false]);
    } finally {
      put.mockRestore();
    }
  });

  it("takes a stored answer from a higher revision (another device)", () => {
    const { saver, hooks } = harness(initial({ value: "a", revision: 2, saved_at: AT }, null).entry);
    saver.received({ value: "b", revision: 1, saved_at: AT });
    expect(hooks.show).not.toHaveBeenCalled();
    saver.received({ value: "c", revision: 3, saved_at: AT });
    expect(saver.entry).toMatchObject({ value: "c", revision: 3, stored: 3 });
  });
});
