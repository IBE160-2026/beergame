import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import { DeletionLine } from "./student-hjem";

describe("DeletionLine (Story 13.9)", () => {
  it("states the deletion day and asks the Student to download the report before it", () => {
    const html = renderToStaticMarkup(<DeletionLine day="2027-06-18" />);
    expect(html).toContain(
      "Dataene dine fra denne Klasseøkten slettes 18. juni 2027. Last ned Studentrapporten før det.",
    );
    expect(html).toContain('data-deletion-date="2027-06-18"');
  });

  it("says the data is deleted once the day has come (Story 15.3)", () => {
    const html = renderToStaticMarkup(<DeletionLine day="2026-01-01" />);
    expect(html).toContain("Dataene dine fra denne Klasseøkten er slettet.");
    expect(html).not.toContain("Last ned");
  });

  it("says nothing while the Klasseøkt has no date", () => {
    expect(renderToStaticMarkup(<DeletionLine day={null} />)).toBe("");
  });
});
