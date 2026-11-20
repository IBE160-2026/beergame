import type { MouseEvent } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it, vi } from "vitest";

import { nb } from "@/copy/nb";

import { ActionError } from "./action-error";
import { AppHeader } from "./app-header";
import { Breadcrumb } from "./breadcrumb";
import { Button, guardUnavailable } from "./button";
import { ColumnItem } from "./column-item";
import { ConnectionNotice } from "./connection-notice";
import { SegmentedChoice } from "./segmented-choice";
import { Stegene } from "./stegene";
import { Switch } from "./switch";
import { ViewToggle } from "./view-toggle";
import { LoadingNote, Skeleton } from "./skeleton";
import { TextField } from "./text-field";

describe("Switch", () => {
  const render = (checked: boolean) =>
    renderToStaticMarkup(
      <Switch id="s" checked={checked} onChange={() => {}} labelledBy="heading">
        {checked ? "Ja, står i emneplanen" : "Nei"}
      </Switch>,
    );

  it("is a native button exposed as a switch, named by its heading and its state text", () => {
    const html = render(true);
    expect(html).toContain('type="button"');
    expect(html).toContain('role="switch"');
    expect(html).toContain('aria-checked="true"');
    expect(html).toContain('aria-labelledby="heading s-text"');
    expect(html).toContain('id="s-text"');
    expect(html).toContain("Ja, står i emneplanen");
    expect(render(false)).toContain('aria-checked="false"');
  });

  it("fills the track in ink with the knob at the right when on, and moves the knob when off", () => {
    const on = render(true);
    for (const cls of ["rounded-full", "bg-ink", "bg-paper", "left-[calc(100%-1.5rem)]", "min-h-tap-target-min"]) {
      expect(on).toContain(cls);
    }
    const off = render(false);
    expect(off).toContain("border-ink-muted");
    expect(off).toContain("left-1");
    expect(off).not.toContain("left-[calc(100%-1.5rem)]");
  });

  it("toggles through onChange", () => {
    const onChange = vi.fn();
    const element = Switch({ id: "s", checked: false, onChange, labelledBy: "h", children: "Nei" });
    (element.props as { onClick: () => void }).onClick();
    expect(onChange).toHaveBeenCalledWith(true);
  });
});

describe("Button", () => {
  it("renders an unavailable button with aria-disabled and never the native disabled", () => {
    const html = renderToStaticMarkup(
      <Button variant="primary" unavailable>
        Logg inn
      </Button>,
    );
    expect(html).toContain('aria-disabled="true"');
    expect(html).not.toMatch(/\sdisabled(=|\s|>)/);
  });

  it("ignores presses while unavailable and passes them on otherwise", () => {
    const handler = vi.fn();
    const event = { preventDefault: vi.fn() } as unknown as MouseEvent<HTMLButtonElement>;
    guardUnavailable(true, handler)(event);
    expect(handler).not.toHaveBeenCalled();
    expect(event.preventDefault).toHaveBeenCalled();
    guardUnavailable(false, handler)(event);
    expect(handler).toHaveBeenCalledTimes(1);
  });

  it("wires the guard into the click handler Button gives React", () => {
    const pressed = (unavailable: boolean) => {
      const handler = vi.fn();
      const event = { preventDefault: vi.fn() } as unknown as MouseEvent<HTMLButtonElement>;
      const element = Button({ unavailable, onClick: handler, children: "Logg inn" });
      (element.props as { onClick: (e: typeof event) => void }).onClick(event);
      return { called: handler.mock.calls.length, prevented: vi.mocked(event.preventDefault).mock.calls.length };
    };
    expect(pressed(true)).toEqual({ called: 0, prevented: 1 });
    expect(pressed(false)).toEqual({ called: 1, prevented: 0 });
  });

  it("gives the primary button the ink fill, the paper label and the small radius", () => {
    const html = renderToStaticMarkup(<Button variant="primary">Logg inn</Button>);
    for (const cls of ["bg-ink", "text-paper", "rounded-sm", "text-button", "min-h-control-height-phone"]) {
      expect(html).toContain(cls);
    }
  });

  it("gives the secondary button an ink-muted idle border", () => {
    expect(renderToStaticMarkup(<Button>Avbryt</Button>)).toContain("border-ink-muted");
  });
});

describe("AppHeader", () => {
  it("puts the product name in a box as tall as a button, with or without the session", () => {
    for (const html of [
      renderToStaticMarkup(<AppHeader />),
      renderToStaticMarkup(<AppHeader>Logg ut</AppHeader>),
    ]) {
      expect(html).toMatch(/<p class="[^"]*min-h-control-height-phone[^"]*">ØL-spillet<\/p>/);
      expect(html).not.toContain("<nav");
    }
  });
});

describe("Breadcrumb", () => {
  it("shows nothing for the home itself", () => {
    expect(renderToStaticMarkup(<Breadcrumb items={[{ label: "Lærerhjem", href: "/laererhjem" }]} />)).toBe("");
  });

  it("links every crumb but the current page, which is marked aria-current", () => {
    const html = renderToStaticMarkup(
      <Breadcrumb
        items={[
          { label: "Lærerhjem", href: "/laererhjem" },
          { label: "IBE160", href: "/klasser/1" },
          { label: "Oversikt", href: "/klasser/1/oversikt" },
        ]}
      />,
    );
    expect(html).toContain('<nav aria-label="Du er her">');
    expect(html).toContain('href="/laererhjem"');
    expect(html).toContain('href="/klasser/1"');
    expect(html).not.toContain('href="/klasser/1/oversikt"');
    expect(html).toMatch(/<span aria-current="page"[^>]*>Oversikt<\/span>/);
    expect(html.indexOf("Lærerhjem")).toBeLessThan(html.indexOf("IBE160"));
  });
});

describe("TextField", () => {
  it("puts the label above the field and ties it with for/id", () => {
    const html = renderToStaticMarkup(<TextField id="email" label="E-post" />);
    expect(html.indexOf("<label")).toBeLessThan(html.indexOf("<input"));
    expect(html).toContain('for="email"');
    expect(html).not.toContain("aria-invalid=");
  });

  it("shows the invalid state with its reason tied by aria-describedby", () => {
    const html = renderToStaticMarkup(<TextField id="email" label="E-post" error="Mangler @" />);
    expect(html).toContain('aria-invalid="true"');
    expect(html).toContain('aria-describedby="email-error"');
    expect(html).toMatch(/<p id="email-error" class="[^"]*text-restordre[^"]*">Mangler @<\/p>/);
    expect(html).toContain("aria-invalid:border-restordre");
  });

  it("ties a hint, a reason and each note to the field, notes last and in ink (Story 5.3)", () => {
    const html = renderToStaticMarkup(<TextField id="x" label="L" hint="h" error="e" notes={["n1", "n2"]} />);
    expect(html).toContain('aria-describedby="x-hint x-error x-note-0 x-note-1"');
    expect(html).toMatch(/<p id="x-note-1" class="[^"]*text-ink[^"]*">n2<\/p>/);
  });
});

describe("Skeleton", () => {
  it("draws the coming layout with no numbers, no text and nothing that moves", () => {
    const html = renderToStaticMarkup(<Skeleton rows={3} columns={4} />);
    expect(html).toContain('aria-hidden="true"');
    expect(html.replace(/<[^>]+>/g, "")).toBe("");
    expect(html.match(/border-b border-hairline/g)).toHaveLength(3);
    expect(html.match(/border-l border-axis/g)).toHaveLength(12);
    expect(html).not.toMatch(/animate|transition|spin|pulse/);
  });

  it("says «Laster …» only when told to, in a status region that is always there", () => {
    expect(renderToStaticMarkup(<LoadingNote visible={false} />)).toMatch(/^<p role="status"[^>]*><\/p>$/);
    expect(renderToStaticMarkup(<LoadingNote visible />)).toContain(">Laster …</p>");
  });
});

describe("ConnectionNotice", () => {
  it("keeps an empty polite status region when there is nothing to say", () => {
    expect(renderToStaticMarkup(<ConnectionNotice />)).toBe('<div role="status" data-connection-notice=""></div>');
  });

  it("shows one line between two rules, in the flow, with no fill", () => {
    const html = renderToStaticMarkup(<ConnectionNotice message={nb.system.offline} updatedAt={Date.UTC(2026, 10, 18, 20, 14)} />);
    expect(html).toContain("border-y border-ink-muted");
    expect(html).not.toMatch(/fixed|absolute|sticky|bg-/);
    expect(html).toContain(nb.system.offline);
    expect(html).toContain('<span class="text-ink-secondary">Sist oppdatert 21:14</span>');
  });

  it("puts «Prøv igjen» at its right as a button", () => {
    const html = renderToStaticMarkup(<ConnectionNotice message={nb.system.pageError} onRetry={() => {}} />);
    expect(html).toMatch(/<button type="button"[^>]*>Prøv igjen<\/button>/);
  });
});

describe("ActionError", () => {
  it("is an alert beside the action, and nothing when there is no error", () => {
    expect(renderToStaticMarkup(<ActionError />)).toBe("");
    expect(renderToStaticMarkup(<ActionError message={nb.system.actionFailed} />)).toMatch(
      /^<p role="alert" class="[^"]*text-restordre[^"]*">Det ble ikke lagret. Prøv igjen.<\/p>$/,
    );
  });
});

describe("SegmentedChoice", () => {
  const html = renderToStaticMarkup(
    <SegmentedChoice
      name="role"
      legend="Rolle"
      options={[
        { value: "lecturer", label: "Faglærer" },
        { value: "admin", label: "Admin" },
      ]}
      value="admin"
      onChange={() => {}}
    />,
  );

  it("is a fieldset of native radios named by its legend", () => {
    expect(html).toMatch(/^<fieldset[^>]*><legend[^>]*>Rolle<\/legend>/);
    expect(html.match(/type="radio"/g)).toHaveLength(2);
    expect(html.match(/name="role"/g)).toHaveLength(2);
  });

  it("checks exactly the chosen option", () => {
    expect(html.match(/checked=""/g)).toHaveLength(1);
    expect(html).toMatch(/checked="" value="admin"/);
  });

  it("marks an unavailable option aria-disabled with its reason and never chooses it", () => {
    const chosen: string[] = [];
    const element = SegmentedChoice({
      name: "ai",
      legend: "KI-modus",
      options: [
        { value: "llm", label: "LLM-spillere", unavailable: true, describedBy: "why" },
        { value: "rule_based", label: "Regelbaserte spillere" },
      ],
      value: "rule_based",
      onChange: (value) => chosen.push(value),
      describedBy: "scope",
    });
    const markup = renderToStaticMarkup(element);
    expect(markup).toMatch(/^<fieldset[^>]*aria-describedby="scope"/);
    const llm = markup.match(/<input[^>]*value="llm"[^>]*>/)?.[0] ?? "";
    expect(llm).toContain('aria-disabled="true"');
    expect(llm).toContain('aria-describedby="why"');
    expect(markup).toMatch(/bg-future-tint[^"]*text-ink-muted/);
    expect(markup.match(/aria-disabled/g)).toHaveLength(1);
    // The radios' change handlers, in option order: the unavailable one does nothing.
    const radios = collectRadios(element);
    radios[0]?.props.onChange();
    radios[1]?.props.onChange();
    expect(chosen).toEqual(["rule_based"]);
  });
});

/** The radio inputs of a rendered SegmentedChoice tree, in order. */
function collectRadios(node: unknown): { props: { onChange: () => void } }[] {
  if (!node || typeof node !== "object") return [];
  if (Array.isArray(node)) return node.flatMap(collectRadios);
  const element = node as { type?: unknown; props?: { type?: string; children?: unknown; onChange?: () => void } };
  if (element.type === "input" && element.props?.type === "radio") {
    return [element as { props: { onChange: () => void } }];
  }
  return collectRadios(element.props?.children);
}

describe("ViewToggle", () => {
  it("is two Valgknapper segments named by its legend", () => {
    const html = renderToStaticMarkup(
      <ViewToggle
        name="view"
        legend="Vis fordelingen"
        options={[
          { value: "diagram", label: "Diagram" },
          { value: "list", label: "Liste" },
        ]}
        value="list"
        onChange={() => {}}
      />,
    );
    expect(html).toMatch(/^<fieldset[^>]*><legend[^>]*>Vis fordelingen<\/legend>/);
    expect(html.match(/type="radio"/g)).toHaveLength(2);
    expect(html).toMatch(/checked="" value="list"/);
    expect(html).toMatch(/min-h-control-height-phone/);
  });
});

describe("Stegene", () => {
  const html = renderToStaticMarkup(
    <Stegene
      title="Stegene"
      titleId="st"
      items={[
        { key: "a", name: "Klassespill", state: "current", note: "pågår" },
        { key: "b", name: "Replay", state: "locked", note: "Replay, åpnes når du har bestått Debrief-quizen." },
      ]}
    />,
  );

  it("is an ordered list named by its heading, with the state of each step in words", () => {
    expect(html).toContain('aria-labelledby="st"');
    expect(html).toContain("<ol");
    expect(html).toContain("pågår");
    expect(html).toContain("Replay, åpnes når du har bestått Debrief-quizen.");
    expect(html).toContain('data-state="current"');
    expect(html).toContain('data-state="locked"');
  });

  it("keeps its markers out of the accessibility tree", () => {
    expect(html.match(/aria-hidden="true"/g)?.length).toBe(3);
  });
});

describe("ColumnItem", () => {
  const rows = [
    { label: "Lager", value: 0 },
    { label: "Restordre", value: 13 },
    { label: "På vei", value: 16 },
  ];

  it("asks one row of the column with a labelled number field and announces its error", () => {
    const html = renderToStaticMarkup(
      <ColumnItem id="p" caption="Uke 11" rows={rows} askedLabel="Posisjon" hint="Posisjon = …" value="x" error="Skriv et helt tall." />,
    );
    expect(html).toContain("<caption");
    expect(html).toContain('<label for="p-answer">Posisjon</label>');
    expect(html).toMatch(/inputmode="numeric"/i);
    expect(html).toContain('aria-invalid="true"');
    expect(html).toContain('aria-describedby="p-hint p-error"');
    expect(html).toMatch(/<p id="p-error" role="alert"[^>]*>Skriv et helt tall\.<\/p>/);
  });

  it("shows the stored answer and the result in words, without a field", () => {
    const html = renderToStaticMarkup(
      <ColumnItem id="p" caption="Uke 11" rows={rows} askedLabel="Posisjon" answer="5" result="Ikke riktig. Svaret er 3: 0 − 13 + 16." />,
    );
    expect(html).not.toContain("<input");
    expect(html).toContain("Ikke riktig. Svaret er 3: 0 − 13 + 16.");
    expect(html).toContain('tabindex="-1"');
  });
});
