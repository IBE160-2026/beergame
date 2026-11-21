"use client";

import { useEffect, useId, useLayoutEffect, useRef, useState } from "react";

import { ActionError } from "@/components/action-error";
import { Button } from "@/components/button";
import { ChainBand } from "@/components/charts/chain-band";
import type { ChainBandInput } from "@/components/charts/chain-band-layout";
import { OrderBarsTable } from "@/components/order-bars-table";
import { WeekScrubber } from "@/components/week-scrubber";
import { nb } from "@/copy/nb";
import { formatNumber } from "@/lib/number-format";
import { roleName } from "@/modules/sessions/sessions";

import { type Chain, type ChainRole, type ChainWeek, DEBRIEF_STEPS, type Debrief, useDebriefStep } from "./api";

const copy = nb.debrief.chain;
const LINE = "text-body-phone lg:text-body";
/** How long the scrubber must stand still before the chain is read out (UX-DR34). */
export const READ_AFTER_MS = 300;

function weekOf(role: ChainRole, week: number): ChainWeek | undefined {
  return role.weeks.find((w) => w.week === week);
}

/** What a Role holds in a Uke, as words: its backlog, its stock, or both for a capped Seat that
 * holds both (Story 6.22); «lager 0» when it holds neither. */
function held(w: ChainWeek, stock: (units: string) => string, backlog: (units: string) => string): string[] {
  const parts = [];
  if (w.inventory > 0 || w.backlog === 0) parts.push(stock(formatNumber(w.inventory)));
  if (w.backlog > 0) parts.push(backlog(formatNumber(w.backlog)));
  return parts;
}

/** The live reading of the chain at a Uke, Fabrikk first (UX-DR34): «Uke 15. Fabrikk: restordre 3,
 * ordre 22. Distributør: …», then the customers' order. */
export function chainReading(chain: Chain, week: number): string {
  const parts = chain.roles.flatMap((role) => {
    const w = weekOf(role, week);
    return w ? [copy.readingRole(roleName(role.role), held(w, copy.readingStock, copy.readingBacklog), formatNumber(w.order))] : [];
  });
  const retailer = chain.roles[chain.roles.length - 1];
  const customers = retailer ? weekOf(retailer, week) : undefined;
  if (customers) parts.push(copy.readingCustomers(formatNumber(customers.incoming_order)));
  return copy.reading(week, parts);
}

/** The four-Role band's numbers at a Uke, from the api's (no arithmetic beyond the bar scale). */
export function chainBandInput(chain: Chain, week: number, width: number, fontSize: number): ChainBandInput {
  const rows = chain.roles.map((role) => ({ role, w: weekOf(role, week) }));
  const retailer = rows[rows.length - 1]?.w;
  return {
    width,
    fontSize,
    upstream: copy.production,
    downstream: copy.customers,
    maxUnits: Math.max(0, ...chain.roles.flatMap((role) => role.weeks.flatMap((w) => [w.inventory, w.backlog]))),
    nodes: rows.map(({ role, w }) => ({
      label: roleName(role.role),
      numbers: w ? held(w, copy.stock, copy.backlog) : [],
      inventory: w?.inventory ?? 0,
      backlog: w?.backlog ?? 0,
      own: role.role === chain.own_role,
    })),
    orders: [...rows.map(({ w }) => (w ? formatNumber(w.order) : "")), retailer ? formatNumber(retailer.incoming_order) : ""],
    supplyLines: rows.map(({ w }) => (w && w.supply_line > 0 ? formatNumber(w.supply_line) : null)),
  };
}

/** Forsterkning as one line of text, from the customers' end up (Detaljist first). */
export function amplificationLine(chain: Chain): string {
  const parts = [...chain.roles]
    .reverse()
    .map((role) =>
      copy.amplificationPart(roleName(role.role), role.amplification === null ? copy.none : `${formatNumber(role.amplification, { decimals: 1 })}×`),
    );
  return copy.amplificationLine(parts);
}

/**
 * Debrief step 3, the whole chain (Story 9.5, FR-44, UX-DR31, UX-DR33, UX-DR34, `07-debrief.png`):
 * shown under step 2 once the Explanation is saved; the api checks the gate and answers the step.
 * The Ukeskrubber (starting at the last Uke) spools the four-Role Kjedebånd and the dashed line
 * across the Ordrestolper; the Rolle × Uke numbers and Forsterkning sit under the bars in the same
 * columns. 300 ms after the scrubber stops, a polite live region reads the chain. Nothing moves
 * by animation, so reduced motion shows each result at once. Every number is the api's (AD-10).
 */
export function ChainStep({ debrief }: { debrief: Debrief }) {
  const step = useDebriefStep(debrief.id, 3, true);
  const chain = step.data?.chain ?? null;
  // A failed refetch keeps the chain on screen; only a first read that fails shows the error.
  if (step.isError && !chain) {
    return (
      <section aria-label={nb.debriefEntry.stepOf(3, DEBRIEF_STEPS)} data-debrief-chain="failed" className="mt-10 border-t border-axis pt-4">
        <div className="flex flex-col items-start gap-2">
          <ActionError message={copy.loadFailed} />
          <Button onClick={() => void step.refetch()}>{nb.system.retry}</Button>
        </div>
      </section>
    );
  }
  if (!chain || chain.last_week < 1) return null;
  return <ChainView chain={chain} />;
}

function ChainView({ chain }: { chain: Chain }) {
  const id = useId();
  const [week, setWeek] = useState(chain.last_week);
  const [reading, setReading] = useState("");
  const moved = useRef(false);
  const bars = useRef<HTMLDivElement>(null);

  // The reading follows the scrubber once it has stood still for 300 ms (never on load).
  useEffect(() => {
    if (!moved.current) return;
    const timer = window.setTimeout(() => setReading(chainReading(chain, week)), READ_AFTER_MS);
    return () => window.clearTimeout(timer);
  }, [chain, week]);

  // Keep the chosen Uke's column in view in the bars' scroll region.
  useLayoutEffect(() => {
    if (!moved.current) return;
    const region = bars.current?.querySelector<HTMLElement>("[role=region]");
    const th = region?.querySelector<HTMLElement>(`th[scope=col][data-col="${week}"]`);
    const label = region?.querySelector<HTMLElement>("thead th[scope=row]");
    if (!region || !th || !label) return;
    const box = region.getBoundingClientRect();
    const cell = th.getBoundingClientRect();
    const left = box.left + label.getBoundingClientRect().width;
    if (cell.left < left) region.scrollLeft -= left - cell.left;
    else if (cell.right > box.right) region.scrollLeft += cell.right - box.right;
  }, [week]);

  const choose = (next: number) => {
    moved.current = true;
    setWeek(next);
  };
  const capped = chain.roles.filter((role) => role.capacity !== null);
  return (
    <section aria-labelledby={`${id}-heading`} data-debrief-chain="" className="mt-10 border-t border-axis pt-4">
      <h2 id={`${id}-heading`} className="max-w-3xl text-headline text-ink">
        <span className="sr-only">{nb.debriefEntry.stepOf(3, DEBRIEF_STEPS)}: </span>
        <span aria-hidden="true" className="mr-3 tabular-nums">
          3
        </span>
        {copy.heading}
      </h2>
      <div className="mt-4 grid max-w-[56rem] gap-x-8 gap-y-2 lg:grid-cols-[1fr_minmax(20rem,28rem)] lg:items-end">
        <p data-chain-at="" className={`${LINE} text-ink-secondary`}>
          {copy.at(week)}
        </p>
        <WeekScrubber
          value={week}
          last={chain.last_week}
          onChange={choose}
          label={copy.scrubber}
          weekText={copy.week}
          back={copy.back}
          forward={copy.forward}
        />
      </div>
      <p aria-live="polite" data-chain-reading="" className="sr-only">
        {reading}
      </p>
      {capped.length > 0 ? (
        <ul data-chain-capacity="" className={`${LINE} mt-3 text-ink`}>
          {capped.map((role) => (
            <li key={role.role}>{copy.capacity(roleName(role.role), formatNumber(role.capacity!))}</li>
          ))}
        </ul>
      ) : null}
      <FourRoleBand chain={chain} week={week} />
      <div ref={bars} className="mt-6">
        <OrderBarsTable
          label={copy.region}
          labelledBy={`${id}-heading`}
          ownRole={chain.own_role}
          chosenWeek={week}
          caption={copy.barsKey(formatNumber(chain.large_order))}
          roles={chain.roles.map((role) => ({
            key: role.role,
            name: roleName(role.role),
            orders: role.weeks.map((w) => ({ week: w.week, order: w.order })),
            amplification: role.amplification,
            firstLargeWeek: role.first_large_order_week,
          }))}
          texts={{
            week: nb.terms.week,
            weekLabel: copy.week,
            amplification: copy.amplification,
            own: copy.own,
            none: copy.none,
            svg: copy.barsSvg,
            axisSvg: copy.barsAxisSvg,
            swipe: copy.swipe,
          }}
        />
      </div>
      <p data-amplification-line="" className={`${LINE} mt-3 max-w-2xl text-ink`}>
        {amplificationLine(chain)}
      </p>
    </section>
  );
}

type Size = { width: number; fontSize: number };

/** The four-Role Kjedebånd at the chosen Uke, at the width it is given and the current text size,
 * measured again whenever either changes. Hidden from screen readers: the live reading and the
 * Rolle × Uke table carry its numbers. */
function FourRoleBand({ chain, week }: { chain: Chain; week: number }) {
  const box = useRef<HTMLDivElement>(null);
  const [size, setSize] = useState<Size | null>(null);
  useLayoutEffect(() => {
    const element = box.current;
    if (!element) return;
    const measure = () => {
      const next = { width: element.clientWidth, fontSize: parseFloat(getComputedStyle(element).fontSize) };
      setSize((was) => (was && was.width === next.width && was.fontSize === next.fontSize ? was : next));
    };
    measure();
    const observer = new ResizeObserver(measure);
    observer.observe(element);
    return () => observer.disconnect();
  }, []);
  return (
    <div data-chain-band="chain" className="mt-4 max-w-[56rem]">
      <p className="text-caption text-ink-secondary">{copy.bandKey}</p>
      <div ref={box} aria-hidden="true" className="mt-1 min-h-[8em] text-caption">
        {size && size.width > 0 ? <ChainBand variant="chain" title={copy.bandSvg} {...chainBandInput(chain, week, size.width, size.fontSize)} /> : null}
      </div>
    </div>
  );
}
