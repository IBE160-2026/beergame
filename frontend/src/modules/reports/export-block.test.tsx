import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import { nb } from "@/copy/nb";
import { topicKeys } from "@/lib/api/topics";

import { reportsZipKey, type ZipState } from "./api";
import { ExportBlock, zipView } from "./export-block";

/** The Klasseøkt's «Eksport» block (Story 13.13, FR-59, UX-DR49): the ZIP action's states. */
const copy = nb.reports.export.zip;
const state = (over: Partial<ZipState> = {}): ZipState => ({
  status: "none",
  generated_at: null,
  students: null,
  deleted: false,
  completion_export: false,
  ...over,
});

const render = (seeded: ZipState) => {
  const client = new QueryClient();
  client.setQueryData(reportsZipKey("s1"), seeded);
  return renderToStaticMarkup(
    <QueryClientProvider client={client}>
      <ExportBlock sessionId="s1" />
    </QueryClientProvider>,
  );
};

describe("zipView", () => {
  it("offers the action, then the pending line, then the download or the retry", () => {
    expect(zipView(state(), false)).toBe("make");
    expect(zipView(state(), true)).toBe("pending");
    expect(zipView(state({ status: "pending" }), false)).toBe("pending");
    expect(zipView(state({ status: "ready", generated_at: "2026-12-11T09:00:00Z", students: 2 }), false)).toBe("ready");
    expect(zipView(state({ status: "failed" }), false)).toBe("failed");
    expect(zipView(state({ deleted: true }), false)).toBe("deleted");
  });

  it("is read again on the requester's user event", () => {
    expect(topicKeys({ topic: "user", id: "u1", version: null })).toContainEqual(reportsZipKey("s1").slice(0, 2));
  });
});

describe("ExportBlock", () => {
  it("shows «Eksport» with the action and the note that the ZIP never holds the AI assessment", () => {
    const html = render(state());
    expect(html).toContain(nb.reports.export.title);
    expect(html).toContain(copy.action);
    expect(html).toContain(copy.note);
    expect(html).toContain('role="status"');
    expect(html).not.toContain("reports/zip/file");
  });

  it("says the ZIP is being made while pending", () => {
    const html = render(state({ status: "pending" }));
    expect(html).toContain(copy.pending);
    expect(html).not.toContain("<button");
  });

  it("links to the file once ready, with when it was made and how many reports it holds", () => {
    const html = render(state({ status: "ready", generated_at: "2026-12-11T09:00:00Z", students: 28 }));
    expect(html).toContain('href="/api/class-sessions/s1/reports/zip/file"');
    expect(html).toContain("med 28 Studentrapporter.");
    expect(html).toContain(copy.again);
  });

  it("keeps the earlier ZIP downloadable while a new one is made or after one failed", () => {
    for (const status of ["pending", "failed"] as const) {
      const html = render(state({ status, generated_at: "2026-12-11T09:00:00Z", students: 3 }));
      expect(html).toContain('href="/api/class-sessions/s1/reports/zip/file"');
      expect(html).toContain("med 3 Studentrapporter.");
    }
  });

  it("says it failed with «Prøv igjen»", () => {
    const html = render(state({ status: "failed" }));
    expect(html).toContain(copy.failed);
    expect(html).toContain(copy.retry);
  });

  it("offers nothing once the Student data is deleted", () => {
    const html = render(state({ deleted: true }));
    expect(html).toContain(copy.deleted);
    expect(html).not.toContain("<button");
  });

  it("offers the Completion export to the Lecturers of the Class, as CSV or Excel, with its note", () => {
    const completion = nb.reports.export.completion;
    const html = render(state({ completion_export: true }));
    expect(html).toContain(completion.action);
    expect(html).toContain('aria-expanded="false"');
    expect(html).toContain('href="/api/class-sessions/s1/completion-export?format=csv"');
    expect(html).toContain('href="/api/class-sessions/s1/completion-export?format=xlsx"');
    expect(html).toContain(completion.note);
  });

  it("shows an Assistant lecturer the report downloads only, and nobody the export once data is deleted", () => {
    const completion = nb.reports.export.completion;
    for (const seeded of [state(), state({ completion_export: true, deleted: true })]) {
      const html = render(seeded);
      expect(html).not.toContain(completion.action);
      expect(html).not.toContain("completion-export");
      expect(html).not.toContain(completion.note);
    }
  });
});
