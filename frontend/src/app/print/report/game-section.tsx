"use client";

// A client module only because the shared chart tables take functions (the Ordrestolper's «Uke n»
// label) and are client components themselves: the print route still renders it on the server to
// complete HTML, and WeasyPrint runs no script (AD-18).
import type { FixedLayout } from "@/components/graph-over-table";
import { OrderBarsTable } from "@/components/order-bars-table";
import { StockBacklogTable } from "@/components/stock-backlog-table";
import { nb } from "@/copy/nb";
import type { components } from "@/lib/api/schema";
import { formatNumber } from "@/lib/number-format";
import type { SeatState } from "@/modules/games/api";
import { chartWeeks, orderRoles, stockRoles, stockTableRows } from "@/modules/games/chain-charts";
import { WeekTable } from "@/modules/games/week-table-view";
import { roleName } from "@/modules/sessions/sessions";

import { reportCopy } from "./copy";
import { chainRoleName, type GameData, holderRuns, inWeeks, largestOrder, markLines, stockMost, weekBlocks } from "./game";

type GameSection = components["schemas"]["GameSectionOut"];

const copy = reportCopy.game;
const charts = nb.insight.charts;
const TEXT = "text-body text-ink";
/** Px widths that hold every number at 13 px (as `/print/graf-over-tabell`) and 18 Uker with
 * their row labels («Distributør, restordre») on A4's 672 px between the margins. */
const FIXED: FixedLayout = { labelWidth: 136, columnWidth: 28, fontSize: 13 };
/** A heading or key stays with the chart under it. */
const KEEP = "break-after-avoid";
/** A chart block stays on one page, with its table under it. */
const BLOCK = "mt-4 break-inside-avoid";

/**
 * The game section (Story 13.8, FR-58, FR-34, AD-15, AD-18): «Klassespill» or «Oppfølgingsspill»,
 * the Role, the Uker played and the Totalkostnad; the Student's Seat as Graf over tabell (Story
 * 6.7) over its week table; the chain in the Ordrestolper over the Rolle × Uke Orders and «Lager
 * og restordre» over its table (Story 7.8); and who played each Role, with the marks in words.
 * Every chart is the shared component at a fixed width, its SVG has a `<title>`, and its table
 * follows it; a long game is drawn in even blocks of Uker on one scale.
 */
export function GameSectionView({ section }: { section: GameSection }) {
  const game = section.game;
  const title = game?.makeup ? copy.makeup : copy.classGame;
  return (
    <section aria-labelledby="report-game" className="mt-8" data-section="game">
      <h2 id="report-game" className="text-step-title font-semibold text-ink">
        {title}
      </h2>
      {game ? <Played game={game} /> : <p className={`mt-3 ${TEXT}`}>{copy.none}</p>}
    </section>
  );
}

function Played({ game }: { game: GameData }) {
  const facts = copy.facts;
  const seat: SeatState = game.seat;
  const seatWeeks = Array.from({ length: seat.week }, (_, i) => i + 1);
  const chain = { roles: game.roles, demand: game.demand };
  const largest = largestOrder(chain);
  const most = stockMost(chain);
  const role = roleName(game.role);
  return (
    <>
      <dl className="mt-3 grid grid-cols-[max-content_1fr] gap-x-6 gap-y-1 text-body">
        {game.game_number !== null ? (
          <>
            <dt className="text-ink-secondary">{facts.game}</dt>
            <dd>{formatNumber(game.game_number)}</dd>
          </>
        ) : null}
        <dt className="text-ink-secondary">{facts.role}</dt>
        <dd>{role}</dd>
        <dt className="text-ink-secondary">{facts.weeks}</dt>
        <dd>{copy.weeks(formatNumber(game.weeks_played), game.weeks_total === null ? null : formatNumber(game.weeks_total))}</dd>
        <dt className="text-ink-secondary">{facts.cost}</dt>
        <dd data-total-cost="">{copy.cost(formatNumber(game.total_cost, { decimals: 2 }))}</dd>
      </dl>
      {game.finished ? null : <p className={`mt-3 ${TEXT}`}>{copy.notFinished}</p>}

      <h3 className={`mt-6 text-label font-semibold text-ink ${KEEP}`}>{copy.seat.title}</h3>
      <p className={`mt-1 ${TEXT} ${KEEP}`}>{copy.seat.intro(role)}</p>
      {weekBlocks(seatWeeks).map((block) => (
        <div key={block.from} className={BLOCK} data-block="seat">
          <WeekTable
            state={seat}
            nowOrder={game.last_order ?? undefined}
            fixed={FIXED}
            span={block}
            label={copy.seat.region(block.from, block.to)}
          />
        </div>
      ))}

      <h3 className={`mt-6 text-label font-semibold text-ink ${KEEP}`}>{copy.chain.title}</h3>
      <p className={`mt-1 ${TEXT} ${KEEP}`}>{copy.chain.intro}</p>
      <h4 className={`mt-4 text-label text-ink ${KEEP}`}>{charts.orders.title}</h4>
      <p className={`mt-1 text-caption text-ink-secondary ${KEEP}`}>{charts.orders.key}</p>
      {weekBlocks(chartWeeks(chain)).map((block) => (
        <div key={block.from} className={BLOCK} data-block="orders">
          <OrderBarsTable
            label={`${charts.orders.region}, ${copy.chain.block(block.from, block.to)}`}
            roles={orderRoles(inWeeks(chain, block.from, block.to))}
            ownRole={game.role}
            fixed={FIXED}
            largest={largest}
            texts={{
              week: charts.week,
              weekLabel: charts.weekLabel,
              amplification: charts.orders.amplification,
              own: charts.orders.own,
              none: charts.orders.none,
              svg: charts.orders.svg,
              axisSvg: charts.axisSvg,
              swipe: charts.swipe,
            }}
          />
        </div>
      ))}
      <h4 className={`mt-4 text-label text-ink ${KEEP}`}>{charts.stock.title}</h4>
      <p className={`mt-1 text-caption text-ink-secondary ${KEEP}`}>{charts.stock.key}</p>
      {weekBlocks(chartWeeks(chain)).map((block) => {
        const part = inWeeks(chain, block.from, block.to);
        return (
          <div key={block.from} className={BLOCK} data-block="stock">
            <StockBacklogTable
              label={`${charts.stock.region}, ${copy.chain.block(block.from, block.to)}`}
              roles={stockRoles(part)}
              fixed={FIXED}
              most={most}
              rows={stockTableRows(part)}
              texts={{ week: charts.week, svg: charts.stock.svg, axisSvg: charts.axisSvg, swipe: charts.swipe }}
            />
          </div>
        );
      })}

      <Holders game={game} />
    </>
  );
}

/** «Hvem spilte»: per Role, Fabrikk first, who held it by runs of Uker and each mark of the one
 * AD-15 mapping in words (FR-34). Other Students by Role only. */
function Holders({ game }: { game: GameData }) {
  const holders = copy.holders;
  return (
    <>
      <h3 className={`mt-6 text-label font-semibold text-ink ${KEEP}`}>{holders.title}</h3>
      <table className="mt-3 w-full table-fixed border-collapse text-body" data-holders="">
        <caption className="text-left text-label text-ink-secondary">{holders.caption}</caption>
        <thead>
          <tr className="border-b border-axis">
            <th scope="col" className="w-1/5 py-1 pr-4 text-left font-semibold">
              {holders.role}
            </th>
            <th scope="col" className="w-2/5 py-1 pr-4 text-left font-semibold">
              {holders.playedBy}
            </th>
            <th scope="col" className="py-1 text-left font-semibold">
              {holders.marks}
            </th>
          </tr>
        </thead>
        <tbody>
          {[...game.roles].reverse().map((role) => {
            const marks = markLines(role);
            return (
              <tr key={role.role} className="border-b border-hairline align-top" data-role={role.role}>
                <th scope="row" className="py-1 pr-4 text-left font-normal">
                  {chainRoleName(role.role, game.role)}
                </th>
                <td className="py-1 pr-4">{`${holderRuns(role).join(". ")}.`}</td>
                <td className="py-1">{marks.length > 0 ? marks.join(" ") : holders.none}</td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </>
  );
}
