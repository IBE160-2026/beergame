import { describe, expect, it } from "vitest";

import { nb } from "@/copy/nb";

import { ApiRequestError } from "./client";
import { actionErrorMessage, request } from "./mutation";

const response = (status: number) => new Response(null, { status });

describe("request", () => {
  it("returns the data of a 2xx answer", async () => {
    await expect(request(async () => ({ data: { ok: 1 }, response: response(200) }))).resolves.toEqual({ ok: 1 });
  });

  it("throws the AD-19 code of a refused answer", async () => {
    const call = async () => ({ error: { error: { code: "forbidden" } }, response: response(403) });
    await expect(request(call)).rejects.toMatchObject({ status: 403, code: "forbidden" });
  });

  it("turns a request that never completed into network_error", async () => {
    const call = async (): Promise<{ response: Response }> => {
      throw new TypeError("Failed to fetch");
    };
    await expect(request(call)).rejects.toMatchObject({ status: 0, code: "network_error" });
  });

  it("lets any other error through as itself, so a bug is not reported as a lost connection", async () => {
    const call = async (): Promise<{ response: Response }> => {
      throw new SyntaxError("Unexpected token");
    };
    await expect(request(call)).rejects.toBeInstanceOf(SyntaxError);
  });
});

describe("actionErrorMessage", () => {
  it("maps unknown and unnamed codes to «Det ble ikke lagret. Prøv igjen.»", () => {
    expect(nb.system.actionFailed).toBe("Det ble ikke lagret. Prøv igjen.");
    expect(actionErrorMessage(new ApiRequestError(500, "unknown_error"))).toBe(nb.system.actionFailed);
    expect(actionErrorMessage(new ApiRequestError(0, "network_error"))).toBe(nb.system.actionFailed);
    expect(actionErrorMessage(new Error("boom"))).toBe(nb.system.actionFailed);
  });

  it("uses an action's own line for the codes it names, and its own fallback", () => {
    const messages = { rate_limited: "For mange forsøk." };
    expect(actionErrorMessage(new ApiRequestError(429, "rate_limited"), messages)).toBe("For mange forsøk.");
    expect(actionErrorMessage(new ApiRequestError(500, "x"), messages, "Utloggingen gikk ikke.")).toBe(
      "Utloggingen gikk ikke.",
    );
    // An inherited property name is not a code an action named.
    expect(actionErrorMessage(new ApiRequestError(500, "toString"), messages)).toBe(nb.system.actionFailed);
  });
});
