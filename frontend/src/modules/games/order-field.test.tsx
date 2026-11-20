import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import { nb } from "@/copy/nb";

import { OrderField } from "./order-field";

const copy = nb.games.play.order;

describe("Ordrefelt, Veiledet uke (Story 6.10)", () => {
  it("shows the fixed Order read-only with the reason and no button", () => {
    const html = renderToStaticMarkup(<OrderField week={2} turn={{ guided: true, order: 4, viewed: false }} />);
    expect(html).toContain(copy.label(2));
    expect(html).toContain("Din ordre for Uke 2");
    expect(html).toMatch(/<input[^>]*readonly[^>]*value="4"/i);
    expect(html).toContain(copy.guided);
    expect(html).not.toContain("<button");
  });

  it("never says how many Veiledede uker remain", () => {
    expect(copy.guided).not.toMatch(/\d/);
    expect(copy.guided.toLowerCase()).not.toContain("igjen");
  });

  it("renders nothing outside a Guided Week until Story 6.11", () => {
    expect(renderToStaticMarkup(<OrderField week={11} turn={{ guided: false, order: null, viewed: false }} />)).toBe("");
  });
});
