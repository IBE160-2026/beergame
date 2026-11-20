import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { clearAllDrafts, clearDraft, clearDrafts, loadDraft, saveDraft } from "./drafts";

/** A `localStorage` stand-in with the Web Storage methods the module uses. */
function memoryStorage(): Storage {
  const items = new Map<string, string>();
  return {
    get length() {
      return items.size;
    },
    key: (i: number) => [...items.keys()][i] ?? null,
    getItem: (key: string) => items.get(key) ?? null,
    setItem: (key: string, value: string) => void items.set(key, String(value)),
    removeItem: (key: string) => void items.delete(key),
    clear: () => items.clear(),
  };
}

describe("drafts", () => {
  let store: Storage;
  beforeEach(() => {
    store = memoryStorage();
    vi.stubGlobal("window", { localStorage: store });
  });
  afterEach(() => vi.unstubAllGlobals());

  it("keeps a draft per User and field and gives it back", () => {
    saveDraft("u1", "order:g1:11", "24");
    saveDraft("u2", "order:g1:11", "7");
    expect(loadDraft("u1", "order:g1:11")).toBe("24");
    expect(loadDraft("u2", "order:g1:11")).toBe("7");
    expect(loadDraft("u1", "order:g1:12")).toBeNull();
    expect(store.getItem("olspillet:draft:u1:order:g1:11")).toBe("24");
  });

  it("an empty value and clearDraft remove the draft", () => {
    saveDraft("u1", "f", "24");
    saveDraft("u1", "f", "");
    expect(loadDraft("u1", "f")).toBeNull();
    saveDraft("u1", "f", "3");
    clearDraft("u1", "f");
    expect(store.length).toBe(0);
  });

  it("clearDrafts removes the User's fields under a prefix but the kept one", () => {
    saveDraft("u1", "order:g1:11", "24");
    saveDraft("u1", "order:g1:12", "30");
    saveDraft("u1", "order:g2:11", "5");
    saveDraft("u2", "order:g1:11", "7");
    clearDrafts("u1", "order:g1:", "order:g1:12");
    expect(loadDraft("u1", "order:g1:11")).toBeNull();
    expect(loadDraft("u1", "order:g1:12")).toBe("30");
    expect(loadDraft("u1", "order:g2:11")).toBe("5");
    expect(loadDraft("u2", "order:g1:11")).toBe("7");
  });

  it("clearAllDrafts removes every draft and nothing else", () => {
    saveDraft("u1", "a", "1");
    saveDraft("u2", "b", "2");
    store.setItem("other", "x");
    clearAllDrafts();
    expect(store.length).toBe(1);
    expect(store.getItem("other")).toBe("x");
  });

  it("works without storage, or with storage that refuses", () => {
    vi.stubGlobal("window", undefined);
    expect(() => saveDraft("u1", "f", "24")).not.toThrow();
    expect(loadDraft("u1", "f")).toBeNull();
    const refusing = {
      get localStorage(): Storage {
        throw new Error("SecurityError");
      },
    };
    vi.stubGlobal("window", refusing);
    expect(() => saveDraft("u1", "f", "24")).not.toThrow();
    expect(loadDraft("u1", "f")).toBeNull();
    expect(() => clearAllDrafts()).not.toThrow();
    const full = { ...memoryStorage(), setItem: () => { throw new Error("QuotaExceededError"); } };
    vi.stubGlobal("window", { localStorage: full });
    expect(() => saveDraft("u1", "f", "24")).not.toThrow();
  });
});
