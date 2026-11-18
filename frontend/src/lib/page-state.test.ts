import { describe, expect, it } from "vitest";

import { ApiRequestError, isSessionExpired } from "./api/client";
import { LOADING_TEXT_AFTER_MS, PAGE_ERROR_AFTER_MS, pagePhase } from "./page-state";

describe("pagePhase", () => {
  it("shows the Skjelett with no text first, «Laster …» after a while, then the page error", () => {
    expect(pagePhase({ pending: true, failed: false, waited: "short" })).toBe("loading");
    expect(pagePhase({ pending: true, failed: false, waited: "long" })).toBe("slow");
    expect(pagePhase({ pending: true, failed: false, waited: "too-long" })).toBe("failed");
  });

  it("shows the page once its data is there, and the page error when the request failed", () => {
    expect(pagePhase({ pending: false, failed: false, waited: "too-long" })).toBe("ready");
    expect(pagePhase({ pending: false, failed: true, waited: "short" })).toBe("failed");
  });

  it("waits 1 s for «Laster …» and 10 s for the page error", () => {
    expect(LOADING_TEXT_AFTER_MS).toBe(1_000);
    expect(PAGE_ERROR_AFTER_MS).toBe(10_000);
  });
});

describe("isSessionExpired", () => {
  it("is true only for the API's session_expired", () => {
    expect(isSessionExpired(new ApiRequestError(401, "session_expired"))).toBe(true);
    expect(isSessionExpired(new ApiRequestError(401, "not_authenticated"))).toBe(false);
    expect(isSessionExpired(new Error("session_expired"))).toBe(false);
  });
});
