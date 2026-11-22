import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import { nb } from "@/copy/nb";

import { BelievabilityQuestion } from "./believability-question";

const copy = nb.believability;

const render = (rating: number | null, errorMessage?: string) =>
  renderToStaticMarkup(<BelievabilityQuestion rating={rating} onSend={() => {}} errorMessage={errorMessage} />);

/** The text of the element with `id` in the markup. */
function textOf(html: string, id: string): string | undefined {
  const escaped = id.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  return new RegExp(`id="${escaped}"[^>]*>([^<]*)<`).exec(html)?.[1];
}

describe("BelievabilityQuestion (Story 10.8)", () => {
  it("is a labelled radio group of five options, none chosen, with the end points in words", () => {
    const html = render(null);
    expect(html).toContain(`<legend class="text-label text-ink mb-field-gap">${copy.legend}</legend>`);
    const radios = [...html.matchAll(/<input type="radio"[^>]*>/g)].map(([tag]) => tag);
    expect(radios.map((tag) => /value="(\d)"/.exec(tag)?.[1])).toEqual(["1", "2", "3", "4", "5"]);
    expect(radios.some((tag) => tag.includes("checked"))).toBe(false);
    expect(new Set(radios.map((tag) => /name="([^"]+)"/.exec(tag)?.[1])).size).toBe(1);
    // Options 1 and 5 are described by their words; the words also stand under the scale.
    const describedBy = radios.map((tag) => /aria-describedby="([^"]+)"/.exec(tag)?.[1]);
    expect(textOf(html, describedBy[0]!)).toBe(copy.low);
    expect(textOf(html, describedBy[4]!)).toBe(copy.high);
    expect(describedBy.slice(1, 4)).toEqual([undefined, undefined, undefined]);
    expect(html).toContain(copy.note);
    // Each segment is a tap target of at least 44 px (Valgknapper).
    expect([...html.matchAll(/<label class="([^"]*)"/g)].every(([, cls]) => cls!.includes("min-w-tap-target-min"))).toBe(true);
    // «Send svar» waits for a choice, and is secondary, never the screen's one primary.
    const button = /<button[^>]*>([^<]*)<\/button>/.exec(html)!;
    expect(button[1]).toBe(copy.send);
    expect(button[0]).toContain('aria-disabled="true"');
    expect(button[0]).not.toContain("bg-ink ");
  });

  it("shows only the Student's own answer once given, and the failed-send line", () => {
    const html = render(4);
    expect(html).toMatch(new RegExp(`role="status"[^>]*>${copy.saved(4)}<`));
    expect(html).not.toContain("<fieldset");
    expect(render(null, copy.failed)).toMatch(new RegExp(`role="alert"[^>]*>${copy.failed}<`));
  });
});
