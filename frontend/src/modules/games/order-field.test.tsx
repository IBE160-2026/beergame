import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import { nb } from "@/copy/nb";
import { formatNumber } from "@/lib/number-format";
import { orderPreview } from "@/lib/preview";

import { OrderField } from "./order-field";
import { lastOrder, orderError, parseOrder, stepOrder } from "./order-input";
import week11 from "./fixtures/play-week-11.json";

const copy = nb.games.play.order;
const NONE = () => undefined;
const free = { guided: false, order: null, viewed: false } as const;

function render(text: string, extra: Partial<Parameters<typeof OrderField>[0]> = {}) {
  const parsed = parseOrder(text, 999);
  const preview =
    parsed.kind === "valid" ? orderPreview({ order_arrival_week: 15, supply_line_base: 16, position_base: -4 }, parsed.value) : null;
  return renderToStaticMarkup(
    <OrderField week={11} turn={free} max={999} lastOrder={8} text={text} onText={NONE} preview={preview} {...extra} />,
  );
}

describe("Ordrefelt, Veiledet uke (Story 6.10)", () => {
  it("shows the fixed Order read-only with the reason, no button and no text cursor (Issue 128)", () => {
    const html = renderToStaticMarkup(
      <OrderField week={2} turn={{ guided: true, order: 4, viewed: false }} max={999} text="" onText={NONE} preview={null} />,
    );
    expect(html).toContain("Din ordre for Uke 2");
    expect(html).toMatch(/<input[^>]*readonly[^>]*value="4"/i);
    expect(html).toMatch(/<input[^>]*cursor-default caret-transparent/);
    expect(html).toContain(copy.guided);
    expect(html).not.toContain("<button");
  });

  it("never says how many Veiledede uker remain", () => {
    expect(copy.guided).not.toMatch(/\d/);
    expect(copy.guided.toLowerCase()).not.toContain("igjen");
  });
});

describe("Ordrefelt, typing an Order (Story 6.11)", () => {
  it("empty: the label, a numeric text field, the help line tied to it, last Uke's Order and an unavailable button", () => {
    const html = render("");
    expect(html).toContain(copy.label(11));
    expect(html).toMatch(/<input[^>]*type="text"[^>]*inputMode="numeric"[^>]*pattern="\[0-9\]\*"/);
    expect(html).toContain(`placeholder="${copy.placeholder}"`);
    const help = html.match(/<p id="([^"]+)"[^>]*>Hele tall fra 0 til 999\.<\/p>/);
    expect(help).not.toBeNull();
    expect(html).toMatch(new RegExp(`aria-describedby="${help![1]}"`));
    expect(html).toContain(copy.last("8"));
    expect(html).toMatch(/<button[^>]*aria-disabled="true"[^>]*>Bekreft ordre<\/button>/);
    // − cannot act on an empty field; + can.
    expect(html).toMatch(/<button[^>]*aria-label="Én færre"[^>]*aria-disabled="true"/);
    expect(html).not.toMatch(/<button[^>]*aria-label="Én flere"[^>]*aria-disabled="true"/);
    expect(html).not.toContain("aria-invalid");
  });

  it("valid: «Bekreft ordre på 24» under where it arrives; no last-Uke line", () => {
    const html = render("24");
    expect(html).toContain(copy.arrives(15));
    expect(html).toMatch(/<button[^>]*>Bekreft ordre på 24<\/button>/);
    expect(html).not.toMatch(/aria-disabled="true"[^>]*>Bekreft/);
    expect(html).not.toContain(copy.last("8"));
    expect(html).toContain("border-ink");
  });

  it("0 is a valid Order", () => {
    expect(render("0")).toMatch(/>Bekreft ordre på 0<\/button>/);
  });

  it.each(["2a", "2,5", "2.5", "-1", "2 4", " 4"])("«%s» is not a whole number", (text) => {
    const html = render(text);
    expect(html).toContain(copy.invalid("999"));
    expect(html).toContain('aria-invalid="true"');
    expect(html).toContain("border-restordre");
    expect(html).toMatch(/aria-disabled="true"[^>]*>Bekreft ordre<\/button>/);
    expect(html).not.toContain(copy.arrives(15));
  });

  it("too large: «1000 er mer enn 999 …»", () => {
    const html = render("1000");
    expect(html).toContain(copy.tooLarge(formatNumber(1000), "999"));
    expect(html).toContain('aria-invalid="true"');
  });

  it("no number is suggested anywhere (UX-DR78)", () => {
    expect(render("")).toMatch(/<input[^>]*value=""/);
  });

});

describe("Ordrefelt, sending and confirmed (Story 6.12)", () => {
  it("sending: «Sender ordre på 24 …», busy and unavailable, the field read-only, − and + unavailable", () => {
    const html = render("24", { sending: true });
    expect(html).toMatch(/<button[^>]*aria-disabled="true"[^>]*aria-busy="true"[^>]*>Sender ordre på 24 …<\/button>/);
    expect(html).toMatch(/<input[^>]*readOnly=""/);
    expect(html).toMatch(/<button[^>]*aria-label="Én færre"[^>]*aria-disabled="true"/);
    expect(html).toMatch(/<button[^>]*aria-label="Én flere"[^>]*aria-disabled="true"/);
    expect(html).toMatch(/aria-live="polite"[^>]*>Sender ordre på 24 …</);
  });

  it("«…» never wraps alone: a non-breaking space before it (Issue #130)", () => {
    expect(copy.sending("24")).toBe("Sender ordre på 24 …");
    expect(copy.checking.endsWith("Sjekker …")).toBe(true);
  });

  it("confirmed: «Ordren på 24 er sendt.» focusable by script, the next line, no field and no button", () => {
    const html = render("", { turn: { guided: false, order: 24, viewed: false } });
    expect(html).toMatch(/<p data-order-sent="" tabindex="-1"[^>]*>Ordren på 24 er sendt\.<\/p>/i);
    expect(html).toContain(copy.next);
    expect(html).not.toContain("<input");
    expect(html).not.toContain("<button");
    expect(html).not.toContain(copy.guided);
  });

  it("confirmed while the game waits for others names them with the wait (Story 6.14)", () => {
    const html = render("", { turn: { guided: false, order: 24, viewed: false }, waitingFor: "Jonas (3 min)" });
    expect(html).toMatch(/data-order-sent=""[^>]*>Ordren på 24 er sendt\. Venter på Jonas \(3 min\)\.<\/p>/);
    expect(html).not.toContain("andre spillere");
  });
});

describe("Ordrefelt, a send that did not place the Order (Story 6.13)", () => {
  const regions = (html: string) => ({
    alert: html.match(/<div role="alert" data-order-failure="">(.*?)<\/div>/)?.[1] ?? null,
    status: html.match(/<div aria-live="polite" data-order-status="">(.*?)<\/div>/)?.[1] ?? null,
  });

  it("nothing to say: both regions are there and empty", () => {
    expect(regions(render("24"))).toEqual({ alert: "", status: "" });
  });

  it("submit failed: the alert, the value editable and «Prøv å sende 24 igjen» active", () => {
    const html = render("24", { failure: copy.failed, retry: true });
    expect(regions(html).alert).toContain(copy.failed);
    expect(html).toMatch(/<input[^>]*value="24"/);
    expect(html).not.toMatch(/<input[^>]*readOnly/);
    expect(html).toMatch(/<button[^>]*>Prøv å sende 24 igjen<\/button>/);
    expect(html).not.toMatch(/aria-disabled="true"[^>]*>Prøv å sende/);
  });

  it("refused by code: the code's words, the normal button", () => {
    const html = render("24", { failure: copy.seatGone("24") });
    expect(regions(html).alert).toContain(copy.seatGone("24"));
    expect(html).toMatch(/>Bekreft ordre på 24<\/button>/);
  });

  it("timed out: «Vi vet ikke om ordren kom fram. Sjekker …» politely, still busy, not said twice", () => {
    const html = render("24", { sending: true, checking: true });
    expect(regions(html).status).toContain(copy.checking);
    expect(html).toMatch(/aria-busy="true"[^>]*>Sender ordre på 24 …<\/button>/);
    expect(html).toMatch(/<p aria-live="polite" class="sr-only" data-order-announce=""><\/p>/);
  });

  it("the words for a closed Uke and a lost Seat name the Order", () => {
    expect(copy.weekGone(11, "24")).toBe("Uke 11 er over. Ordren på 24 ble ikke sendt.");
    expect(copy.seatGone("24")).toContain("Ordren på 24 ble ikke sendt.");
    expect(copy.offline("24")).toBe("Ordren på 24 er ikke sendt.");
  });
});

describe("order-input rules", () => {
  it("parses whole numbers from 0 to max", () => {
    expect(parseOrder("", 10)).toEqual({ kind: "empty" });
    expect(parseOrder("007", 10)).toEqual({ kind: "valid", value: 7 });
    expect(parseOrder("10", 10)).toEqual({ kind: "valid", value: 10 });
    expect(parseOrder("011", 10)).toEqual({ kind: "too-large", digits: "11" });
    expect(parseOrder("1e3", 10)).toEqual({ kind: "invalid" });
    expect(parseOrder("+3", 10)).toEqual({ kind: "invalid" });
  });

  it("formats the too-large reason, even past safe integers", () => {
    expect(orderError(parseOrder("1200", 999), 999)).toBe(copy.tooLarge(formatNumber(1200), "999"));
    expect(orderError(parseOrder("99999999999999999999", 999), 999)).toContain("99999999999999999999 er mer enn 999");
  });

  it("«Sist Uke bestilte du n.» takes the Uke before nå; in the first free Uke the last fixed Order", () => {
    expect(lastOrder(week11.seat_state.history)).toBe(8);
    // Uke 5 follows the four Guided Weeks: the history ends with the fixed Order 4.
    expect(lastOrder(week11.seat_state.history.slice(0, 4))).toBe(4);
    expect(lastOrder([])).toBeUndefined();
  });

  it("− and +: limits and steps", () => {
    const at = (text: string, d: -1 | 1) => stepOrder(parseOrder(text, 999), 999, d);
    expect(at("", 1)).toBe(1);
    expect(at("", -1)).toBeNull();
    expect(at("0", -1)).toBeNull();
    expect(at("0", 1)).toBe(1);
    expect(at("999", 1)).toBeNull();
    expect(at("999", -1)).toBe(998);
    expect(at("1500", -1)).toBe(999);
    expect(at("1500", 1)).toBeNull();
    expect(at("2a", 1)).toBeNull();
    expect(at("2a", -1)).toBeNull();
    expect(stepOrder(parseOrder("", 0), 0, 1)).toBeNull();
  });
});
