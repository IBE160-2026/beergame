import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import { nb } from "@/copy/nb";
import { GROUP } from "@/lib/number-format";
import { AdminSections } from "@/modules/identity/home-page";
import { ADMIN_CROSS_INSTITUTION_PATH } from "@/modules/identity/homes";

import { institutionRows } from "./cross-institution";
import type { ComparedInstitution, InstitutionMeasure } from "./cross-institution-api";

/** «Tverrinstitusjonell statistikk» (Story 14.7, cut list): the rows name Institutions only, say a
 * withheld or unmeasured figure in words, and the Admin-område links the page only with its flag. */
const copy = nb.crossInstitution;
const X = "01a1f8ee-34f2-70af-8800-f79281ed7c00";
const Y = "01a1f8ee-34f2-70af-8800-f79281ed7c01";
const Z = "01a1f8ee-34f2-70af-8800-f79281ed7c02";

const institutions: ComparedInstitution[] = [
  { institution_id: X, name: "NTNU", sessions: 2, withheld: false, differs: ["ai_mode"] },
  { institution_id: Y, name: "USN Bø", sessions: 2, withheld: false, differs: [] },
  { institution_id: Z, name: "UiA", sessions: 1, withheld: true, differs: [] },
];

const measure: InstitutionMeasure = {
  key: "chain.median",
  unit: "kroner",
  values: [
    { institution_id: X, value: "4000", withheld: false, sessions: 2 },
    { institution_id: Y, value: null, withheld: true, sessions: 0 },
    { institution_id: Z, value: null, withheld: true, sessions: 0 },
  ],
  comparable: null,
};

describe("institutionRows", () => {
  it("names the Institution, the figure and how many Class sessions it rests on", () => {
    const [ntnu, usn, uia] = institutionRows(measure, institutions);
    expect(ntnu.session).toBe("NTNU");
    expect(ntnu.figure).toBe(`4${GROUP}000 kr`);
    expect(ntnu.text).toBe(`4${GROUP}000 kr (2 Klasseøkter)`);
    expect(ntnu.share).toBe(1);
    expect(ntnu.reads).toBe(`NTNU: 4${GROUP}000 kr (2 Klasseøkter). Ulikt oppsett: KI-modus`);
    // A withheld figure and a withheld Institution are said in words and not drawn.
    expect([usn.text, usn.share, usn.differs]).toEqual([nb.crossClass.withheld, null, null]);
    expect([uia.text, uia.share]).toEqual([copy.withheld, null]);
  });

  it("says one Class session in the singular, and a figure not measured in words", () => {
    const [row] = institutionRows(
      { ...measure, values: [{ institution_id: Y, value: "1954.4", withheld: false, sessions: 1 }] },
      institutions,
    );
    expect(row.text).toBe(`1${GROUP}954 kr (1 Klasseøkt)`);
    const [none] = institutionRows(
      { ...measure, values: [{ institution_id: Y, value: null, withheld: false, sessions: 0 }] },
      institutions,
    );
    expect(none.text).toBe(nb.crossClass.notMeasured);
  });
});

describe("the Admin-område's link", () => {
  const render = (on: boolean) =>
    renderToStaticMarkup(
      <QueryClientProvider client={new QueryClient()}>
        <AdminSections user={{ cross_institution_stats: on }} />
      </QueryClientProvider>,
    );

  it("shows «Tverrinstitusjonell statistikk» only while the flag is on", () => {
    expect(render(true)).toContain(ADMIN_CROSS_INSTITUTION_PATH);
    expect(render(true)).toContain(nb.admin.sections.crossInstitution);
    expect(render(false)).not.toContain(ADMIN_CROSS_INSTITUTION_PATH);
  });
});
