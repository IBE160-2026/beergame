import type { MouseEvent } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it, vi } from "vitest";

import { nb } from "@/copy/nb";

import { ActionError } from "./action-error";
import { AppHeader } from "./app-header";
import { Breadcrumb } from "./breadcrumb";
import { Button, guardUnavailable } from "./button";
import { ConnectionNotice } from "./connection-notice";
import { LoadingNote, Skeleton } from "./skeleton";
import { TextField } from "./text-field";

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
