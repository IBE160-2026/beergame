"use client";

import { useEffect, useId, useRef, useState } from "react";

import { ChainBill } from "@/components/chain-bill";
import { NetOverGame } from "@/components/charts/net-over-game";
import { LINK_BUTTON } from "@/components/link";
import { ScrollRegion } from "@/components/scroll-region";
import { WeekScrubber } from "@/components/week-scrubber";
import { nb } from "@/copy/nb";
import { ApiRequestError } from "@/lib/api/client";
import { useBoxSize } from "@/lib/box-size";
import { formatNumber } from "@/lib/number-format";
import { usePageState } from "@/lib/page-state";
import { cn } from "@/lib/utils";
import type { SessionUser } from "@/modules/identity/api";
import { AccessDenied, GuardedPage } from "@/modules/identity/home-page";
import { DEBRIEF_PATH } from "@/modules/identity/homes";
import { PageLink, PageShell } from "@/modules/identity/page-shell";
import { roleName } from "@/modules/sessions/sessions";

import {
  DEBRIEF_STEPS,
  INDIVIDUAL_STEP,
  type Shared,
  type SharedChain,
  sharedCostRows,
  sharedKey,
  sharedNetRows,
  useSharedDebrief,
} from "./api";
import { chainReading, FourRoleBand, READ_AFTER_MS } from "./chain-step";

const copy = nb.debrief.shared;
const LINE = "text-body-phone lg:text-body";
const money = (value: string) => formatNumber(value, { decimals: 2 });
/** Each Role's Netto lager chart, in caption lines (about 80 px at 13 px, `07-debrief.png`). */
const NET_LINES = 6;
const FALLBACK = { width: 288, fontSize: 13 };
/** The Role column beside each chart and the gap after it, in em of the caption size. */
const LABEL_EM = 8.5;
const GAP_EM = 0.5;

/**
 * «Delt skjerm: hele kjeden» (Story 9.13, FR-74, UX-DR34, UX-DR35, `07-debrief.png`, right): a
 * joined Student's own session in display mode, for a laptop or projector in the room. The page
 * has no header with the Student's name and reads only `GET /api/debriefs/{id}/shared`, which has
 * no name, Explanation, answer or moment in it. While a joined Student has not sent, it says the
 * reveal is locked; then it shows the chain at a Uke the scrubber on this screen chooses (each
 * phone keeps its own), Netto lager per Role on one scale with the chosen Uke dashed, and «Kostnad,
 * kr» per Role with Lager and Restordre beside each total and the chain's total. Fabrikk at the
 * top, upstream on the left. The `debrief:<id>` event reads it again, without reload.
 */
export function SharedScreenPage({ debriefId }: { debriefId: string }) {
  return <GuardedPage page="home">{(user, updatedAt) => <SharedView debriefId={debriefId} user={user} updatedAt={updatedAt} />}</GuardedPage>;
}

function SharedView({ debriefId, user, updatedAt }: { debriefId: string; user: SessionUser; updatedAt: number }) {
  const found = useSharedDebrief(debriefId);
  const { phase, retry } = usePageState(found, sharedKey(debriefId));
  // Also once the screen was showing: a Student who leaves the group (or drops out) loses it at
  // the next `debrief:<id>` read, and the cached chart must not stay on the projector.
  if (found.error instanceof ApiRequestError && found.error.code === "forbidden") {
    return <AccessDenied user={user} updatedAt={updatedAt} />;
  }
  const shared = found.data;
  // No `user`: display mode shows no header with the Student's name.
  return (
    <PageShell
      title={copy.title}
      updatedAt={found.dataUpdatedAt || updatedAt}
      phase={shared ? "ready" : phase === "ready" ? "loading" : phase}
      onRetry={retry}
    >
      {shared ? <Screen shared={shared} /> : null}
    </PageShell>
  );
}

function Screen({ shared }: { shared: Shared }) {
  // The polite line once the lock opens on this screen, never on load.
  const wasLocked = useRef(shared.locked);
  const [announced, setAnnounced] = useState("");
  useEffect(() => {
    if (wasLocked.current && !shared.locked) setAnnounced(copy.unlocked);
    wasLocked.current = shared.locked;
  }, [shared.locked]);
  return (
    <div data-shared-screen={shared.locked ? "locked" : "open"}>
      <p className={`${LINE} mt-1 text-ink-secondary`}>
        {copy.game(shared.game_number)}. <span data-shared-step={shared.step}>{copy.step(shared.step, INDIVIDUAL_STEP, DEBRIEF_STEPS)}</span>
      </p>
      <PageLink href={DEBRIEF_PATH(shared.class_session_id)}>{copy.back}</PageLink>
      <p aria-live="polite" className="sr-only">
        {announced}
      </p>
      {shared.locked || !shared.chain ? (
        <p data-shared-locked="" className={`${LINE} mt-8 max-w-md border-t border-axis pt-4 text-ink`}>
          {copy.locked}
        </p>
      ) : shared.chain.last_week < 1 ? null : (
        <ChainScreen chain={shared.chain} />
      )}
    </div>
  );
}

function ChainScreen({ chain }: { chain: SharedChain }) {
  const id = useId();
  const [week, setWeek] = useState(chain.last_week);
  const [reading, setReading] = useState("");
  const moved = useRef(false);
  // The reading follows the scrubber once it has stood still for 300 ms (never on load).
  useEffect(() => {
    if (!moved.current) return;
    const timer = window.setTimeout(() => setReading(chainReading(chain, week)), READ_AFTER_MS);
    return () => window.clearTimeout(timer);
  }, [chain, week]);
  const choose = (next: number) => {
    moved.current = true;
    setWeek(next);
  };
  const costs = sharedCostRows(chain, roleName, money);
  return (
    <>
      <section aria-labelledby={`${id}-at`} data-shared-chain="" className="mt-8 border-t border-axis pt-4">
        <div className="grid gap-x-8 gap-y-2 lg:grid-cols-[1fr_minmax(20rem,28rem)] lg:items-end">
          <div>
            <h2 id={`${id}-at`} data-shared-at="" className="text-headline text-ink">
              {copy.at(week)}
            </h2>
            <p className="mt-1 text-caption text-ink-secondary">{copy.scrubberNote}</p>
          </div>
          <WeekScrubber
            value={week}
            last={chain.last_week}
            onChange={choose}
            label={nb.debrief.chain.scrubber}
            weekText={nb.debrief.chain.week}
            back={nb.debrief.chain.back}
            forward={nb.debrief.chain.forward}
          />
        </div>
        <p aria-live="polite" data-shared-reading="" className="sr-only">
          {reading}
        </p>
        <FourRoleBand chain={chain} week={week} />
        <BandTable chain={chain} week={week} />
      </section>
      <div className="mt-10 grid grid-cols-1 gap-x-12 gap-y-10 lg:grid-cols-[minmax(0,1fr)_minmax(18rem,26rem)]">
        <NetPerRole chain={chain} week={week} />
        <ChainBill rows={costs.rows} chain={costs.chain} titleId={`${id}-cost`} title={copy.costTitle} className="border-t border-axis pt-4" />
      </div>
      <p className="mt-6 max-w-2xl text-caption text-ink-secondary">{copy.direction}</p>
    </>
  );
}

/** The band's numbers at the chosen Uke as a table, for screen readers (the band is hidden). In a
 * box of its own: a table is never narrower than its content, so `sr-only` on the table itself
 * would widen the page. */
function BandTable({ chain, week }: { chain: SharedChain; week: number }) {
  const columns = copy.columns;
  return (
    <div className="sr-only">
      <table data-shared-band-table="">
        <caption>{copy.bandCaption(week)}</caption>
        <thead>
          <tr>
            <th scope="col">{columns.role}</th>
            <th scope="col">{columns.stock}</th>
            <th scope="col">{columns.backlog}</th>
            <th scope="col">{columns.supplyLine}</th>
            <th scope="col">{columns.order}</th>
          </tr>
        </thead>
        <tbody>
          {chain.roles.map((role) => {
            const w = role.weeks.find((each) => each.week === week);
            return (
              <tr key={role.role}>
                <th scope="row">{roleName(role.role)}</th>
                <td>{w ? formatNumber(w.inventory) : ""}</td>
                <td>{w ? formatNumber(w.backlog) : ""}</td>
                <td>{w ? formatNumber(w.supply_line) : ""}</td>
                <td>{w ? formatNumber(w.order) : ""}</td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

/** «Netto lager» per Role, Fabrikk at the top, on one scale, with the chosen Uke dashed; «Vis som
 * tabell» swaps the charts for Uke × Role in place, and back. */
function NetPerRole({ chain, week }: { chain: SharedChain; week: number }) {
  const id = useId();
  const [asTable, setAsTable] = useState(false);
  const box = useRef<HTMLDivElement>(null);
  const size = useBoxSize(box, FALLBACK);
  const all = chain.roles.flatMap((role) => role.weeks.map((w) => w.net_inventory));
  // The box stays in place in both modes, so its size follows the page (a chart box would be
  // measured once and lost when the table takes its place); the charts get its width less the
  // Role column.
  const chartWidth = Math.max(0, Math.floor(size.width - (LABEL_EM + GAP_EM) * size.fontSize));
  return (
    <section aria-labelledby={`${id}-title`} data-shared-net="" className="min-w-0 border-t border-axis pt-4">
      <h2 id={`${id}-title`} className="text-headline text-ink">
        {copy.netTitle}
      </h2>
      <div ref={box} className="mt-3 text-caption">
        {asTable ? (
          <ScrollRegion labelledBy={`${id}-title`} scrollClassName="max-h-[24em] overflow-y-auto">
            <NetTable chain={chain} />
          </ScrollRegion>
        ) : (
          <div
            className="grid items-center gap-y-1"
            style={{ gridTemplateColumns: `${LABEL_EM}em minmax(0,1fr)`, columnGap: `${GAP_EM}em` }}
          >
            {chain.roles.map((role) => (
              <div key={role.role} data-shared-net-role={role.role} className="contents">
                <p className="text-label text-ink">{roleName(role.role)}</p>
                <NetOverGame
                  width={chartWidth}
                  height={Math.round(size.fontSize * NET_LINES)}
                  fontSize={size.fontSize}
                  points={role.weeks.map((w) => ({ week: w.week, net: w.net_inventory }))}
                  title={copy.netSvg(roleName(role.role))}
                  formatTick={(value) => formatNumber(value)}
                  weekLabel={(w) => String(w)}
                  marker={week}
                  scaleWith={all}
                />
              </div>
            ))}
          </div>
        )}
      </div>
      <button
        type="button"
        className={cn(LINK_BUTTON, "mt-2")}
        data-shared-net-toggle=""
        aria-expanded={asTable}
        onClick={() => setAsTable((shown) => !shown)}
      >
        {asTable ? copy.showChart : copy.showTable}
      </button>
    </section>
  );
}

function NetTable({ chain }: { chain: SharedChain }) {
  const cell = "py-1 pl-3 text-right";
  return (
    <table data-shared-net-table="" className="w-full border-collapse text-caption text-ink tabular-nums lining-nums">
      <caption className="sr-only">{copy.netCaption}</caption>
      <thead className="sticky top-0 bg-paper">
        <tr className="border-b border-axis text-ink-secondary">
          <th scope="col" className="py-1 text-left font-normal">
            {nb.terms.week}
          </th>
          {chain.roles.map((role) => (
            <th key={role.role} scope="col" className={cn(cell, "font-normal")}>
              {roleName(role.role)}
            </th>
          ))}
        </tr>
      </thead>
      <tbody>
        {sharedNetRows(chain).map((row) => (
          <tr key={row.week} className="border-b border-hairline">
            <th scope="row" className="py-1 text-left font-normal">
              {row.week}
            </th>
            {row.nets.map((net, index) => (
              <td key={chain.roles[index]!.role} className={cn(cell, net !== null && net < 0 && "text-restordre")}>
                {net === null ? "" : formatNumber(net)}
              </td>
            ))}
          </tr>
        ))}
      </tbody>
    </table>
  );
}
