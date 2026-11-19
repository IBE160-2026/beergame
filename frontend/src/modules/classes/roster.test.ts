import { describe, expect, it } from "vitest";

import { nb } from "@/copy/nb";

import type { RosterUpload } from "./api";
import { columnHasNoAddress, columnLabel, columnReason, invalidReason } from "./roster";

const copy = nb.classes.roster;

function upload(overrides: Partial<RosterUpload> = {}): RosterUpload {
  return {
    source: "file",
    file_name: "ibe160-canvas-eksport.xlsx",
    row_count: 250,
    has_header: true,
    columns: [
      { index: 0, letter: "A", header: "Navn" },
      { index: 1, letter: "B", header: "Student-ID" },
      { index: 2, letter: "C", header: "E-post" },
    ],
    suggested_column: 2,
    suggested_count: 246,
    chosen_column: 2,
    chosen_count: 246,
    valid_count: 246,
    invalid_rows: [],
    preview: [],
    ...overrides,
  };
}

describe("the e-mail column", () => {
  it("names a column by letter and header, or by letter alone", () => {
    expect(columnLabel({ index: 2, letter: "C", header: "E-post" })).toBe("Kolonne C, E-post");
    expect(columnLabel({ index: 27, letter: "AB", header: "" })).toBe("Kolonne AB");
  });

  it("gives the preselected column the reason in the UX spine's words", () => {
    expect(columnReason(upload())).toBe("Kolonne C, E-post. Valgt fordi alle rader unntatt fire ser ut som adresser.");
  });

  it("words every share of matching rows", () => {
    expect(copy.suggested(250, 250)).toBe("Valgt fordi alle rader ser ut som adresser.");
    expect(copy.suggested(12, 13)).toBe("Valgt fordi alle rader unntatt én ser ut som adresser.");
    expect(copy.suggested(200, 250)).toBe("Valgt fordi alle rader unntatt 50 ser ut som adresser.");
    expect(copy.suggested(3, 250)).toBe("Valgt fordi 3 av 250 rader ser ut som adresser.");
  });

  it("gives a column the Lecturer chose the api's count for it", () => {
    expect(columnReason(upload({ chosen_column: 0, chosen_count: 0 }))).toBe(
      "Kolonne A, Navn. Ingen rader i denne kolonnen ser ut som adresser.",
    );
    expect(columnReason(upload({ chosen_column: 1, chosen_count: 5 }))).toBe(
      "Kolonne B, Student-ID. 5 av 250 rader ser ut som adresser.",
    );
  });

  it("says so when no column looks like addresses", () => {
    expect(columnReason(upload({ suggested_column: null, chosen_column: null, chosen_count: 0 }))).toBe(
      copy.noEmailColumn,
    );
  });

  it("counts the rows read", () => {
    expect(copy.rowsRead(250)).toBe("250 rader lest");
    expect(copy.rowsRead(1)).toBe("1 rad lest");
  });
});

describe("invalid rows (Story 4.3)", () => {
  it("words each reason in text, a duplicate naming the first row", () => {
    const row = (reason: RosterUpload["invalid_rows"][number]["reason"], first_row: number | null = null) =>
      invalidReason({ row_number: 9, value: "x", reason, first_row });
    expect(row("missing_domain")).toBe("Domene mangler");
    expect(row("missing_at")).toBe("Mangler @");
    expect(row("two_at")).toBe("To @");
    expect(row("empty")).toBe("Tom celle");
    expect(row("whitespace")).toBe("Mellomrom i adressen");
    expect(row("missing_name")).toBe("Mangler navn før @");
    expect(row("duplicate", 2)).toBe("Dublett av rad 2");
  });

  it("counts Invitations in the button, one in the singular", () => {
    expect(copy.send(246)).toBe("Send 246 Invitasjoner");
    expect(copy.send(1)).toBe("Send 1 Invitasjon");
    expect(copy.invalidTitle(4, 250)).toBe("Ugyldige rader: 4 av 250");
  });

  it("treats a chosen column with no address as an error, and no column as guidance", () => {
    expect(columnHasNoAddress(upload({ chosen_column: 0, chosen_count: 0 }))).toBe(true);
    expect(columnHasNoAddress(upload())).toBe(false);
    expect(columnHasNoAddress(upload({ chosen_column: null, chosen_count: 0 }))).toBe(false);
  });
});
