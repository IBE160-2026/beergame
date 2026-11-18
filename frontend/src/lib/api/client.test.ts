import { describe, expect, it } from "vitest";

import { ApiRequestError, createApiClient, CSRF_HEADER, CSRF_VALUE, toApiError } from "./client";

function recordingFetch(status = 200, body: unknown = { user: null }) {
  const seen: Request[] = [];
  const fetch = async (input: Request) => {
    seen.push(input);
    return new Response(status === 204 ? null : JSON.stringify(body), {
      status,
      headers: { "content-type": "application/json" },
    });
  };
  return { seen, fetch: fetch as unknown as typeof globalThis.fetch };
}

describe("the generated API client", () => {
  it("sends the CSRF header on every mutation and the session cookie on every request", async () => {
    const { seen, fetch } = recordingFetch(204);
    const client = createApiClient({ baseUrl: "http://t", fetch });
    await client.POST("/api/auth/logout");
    await client.POST("/api/auth/login", { body: { email: "a@b.no", password: "x" } });
    expect(seen.map((r) => r.headers.get(CSRF_HEADER))).toEqual([CSRF_VALUE, CSRF_VALUE]);
    expect(seen.every((r) => r.credentials === "same-origin")).toBe(true);
    expect(seen[1]!.url).toBe("http://t/api/auth/login");
  });

  it("leaves reads without the CSRF header", async () => {
    const { seen, fetch } = recordingFetch();
    const client = createApiClient({ baseUrl: "http://t", fetch });
    await client.GET("/api/auth/me");
    expect(seen[0]!.method).toBe("GET");
    expect(seen[0]!.headers.get(CSRF_HEADER)).toBeNull();
  });
});

describe("toApiError", () => {
  it("reads the AD-19 code", () => {
    const error = toApiError(401, { error: { code: "invalid_credentials", message: "", fields: {} } });
    expect(error).toBeInstanceOf(ApiRequestError);
    expect(error.status).toBe(401);
    expect(error.code).toBe("invalid_credentials");
  });

  it.each([undefined, null, "text", {}, { error: {} }, { error: { code: 3 } }])(
    "falls back to unknown_error for %j",
    (body) => {
      expect(toApiError(500, body).code).toBe("unknown_error");
    },
  );
});
