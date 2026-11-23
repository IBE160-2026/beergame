import { NetOverGame } from "@/components/charts/net-over-game";
import { nb } from "@/copy/nb";
import { formatNumber } from "@/lib/number-format";
import { type RunCells, unlikeReasons, walkthroughRows } from "@/modules/replay/walkthrough";
import { roleName } from "@/modules/sessions/sessions";

import { reportCopy } from "./copy";
import { type ReplayData, type ReplaySection, scenarioRows } from "./parts";

const copy = reportCopy.replay;
const walk = nb.replay.walkthrough;
const TEXT = "text-body text-ink";
const KEEP = "break-after-avoid";
/** The chart at a fixed size on A4's 672 px between the margins, in the report's 13 px. */
const CHART = { width: 640, height: 182, fontSize: 13 };
const CELL = "py-1 pl-2 text-right tabular-nums lining-nums";
const HEAD = "py-1 pl-2 text-right align-bottom font-semibold";

/**
 * The Replay section (Story 13.10, FR-58, FR-50, UX-DR70, AD-18): the Replay scenario as the
 * Replay's own settings, its Totalkostnad beside the Class game's, and Netto lager of both runs on
 * one Uke axis (`NetOverGame` at a fixed width, its SVG with a `<title>`), followed by the
 * walkthrough's table of every Uke; «Ikke like for like.» with its reasons whenever the two runs
 * stand side by side. A Class game played mostly by AI players is left out, as on the walkthrough;
 * a Replay closed at the Testfrist or not finished says so, and shows the Uker it had alone.
 */
export function ReplaySectionView({ section }: { section: ReplaySection }) {
  const replay = section.replay;
  return (
    <section aria-labelledby="report-replay" className="mt-8" data-section="replay">
      <h2 id="report-replay" className="text-step-title font-semibold text-ink">
        {copy.title}
      </h2>
      {replay ? <Played replay={replay} /> : <p className={`mt-3 ${TEXT}`}>{copy.none}</p>}
    </section>
  );
}

function Played({ replay }: { replay: ReplayData }) {
  const role = roleName(replay.role);
  const finished = replay.state === "finished";
  const both = replay.class_game !== null;
  const points = replay.replay.weeks.map((w) => ({ week: w.week, net: w.net_inventory }));
  const compare = replay.class_game?.weeks.map((w) => ({ week: w.week, net: w.net_inventory }));
  return (
    <>
      <h3 className={`mt-4 text-label font-semibold text-ink ${KEEP}`}>{copy.scenario}</h3>
      <table className="mt-1 w-full table-fixed border-collapse text-body" data-scenario="">
        <caption className="text-left text-label text-ink-secondary">{copy.scenarioCaption}</caption>
        <thead>
          <tr className="border-b border-axis">
            <th scope="col" className="w-1/4 py-1 pr-4 text-left font-semibold">
              {copy.setting}
            </th>
            <th scope="col" className="py-1 text-left font-semibold">
              {copy.value}
            </th>
          </tr>
        </thead>
        <tbody>
          {scenarioRows(replay, role).map((row) => (
            <tr key={row.name} className="border-b border-hairline">
              <th scope="row" className="py-1 pr-4 text-left font-normal">
                {row.name}
              </th>
              <td className="py-1">{row.value}</td>
            </tr>
          ))}
        </tbody>
      </table>

      {finished ? null : <p className={`mt-3 ${TEXT}`}>{replay.state === "closed" ? copy.closed : copy.open}</p>}
      {/* A Replay closed at the Testfrist keeps the Uker played: their cost, chart and table. */}
      {replay.replay.weeks.length > 0 ? (
        <>
          <dl className="mt-4 grid grid-cols-[max-content_1fr] gap-x-6 gap-y-1 text-body">
            <dt className="text-ink-secondary">{walk.totalLabel}</dt>
            <dd data-replay-total="">{copy.cost(formatNumber(replay.replay.total_cost, { decimals: 2 }))}</dd>
            {replay.class_game ? (
              <>
                <dt className="text-ink-secondary">{walk.classTotalLabel(replay.class_game_number)}</dt>
                <dd>{copy.cost(formatNumber(replay.class_game.total_cost, { decimals: 2 }))}</dd>
              </>
            ) : null}
          </dl>
          {both ? (
            <div className="mt-3" data-unlike="">
              <p className={`${TEXT} font-semibold`}>{walk.unlike}</p>
              {unlikeReasons(replay).map((reason) => (
                <p key={reason} className={TEXT}>
                  {reason}
                </p>
              ))}
            </div>
          ) : null}
          {replay.mostly_ai ? <p className={`mt-3 ${TEXT}`}>{walk.mostlyAi}</p> : null}

          <div className="mt-4 break-inside-avoid">
            <h3 className={`text-label font-semibold text-ink ${KEEP}`}>{both ? walk.chartTitle : walk.chartTitleAlone}</h3>
            {both ? <p className={`mt-1 text-caption text-ink-secondary ${KEEP}`}>{walk.legend}</p> : null}
            <div className="mt-2">
              <NetOverGame
                width={CHART.width}
                height={CHART.height}
                fontSize={CHART.fontSize}
                points={points}
                compare={compare}
                title={both ? walk.chartSvg : walk.chartSvgAlone}
                formatTick={(value) => formatNumber(value)}
                weekLabel={walk.week}
                lineLabels={{ main: walk.runReplay, compare: walk.runClass }}
                yUnit={nb.terms.units}
              />
            </div>
          </div>
          <RunsTable replay={replay} />
        </>
      ) : null}
    </>
  );
}

function Cells({ run }: { run: RunCells | null }) {
  if (!run) {
    return (
      <>
        <td className={CELL}>{walk.noWeek}</td>
        <td className={CELL}>{walk.noWeek}</td>
        <td className={CELL}>{walk.noWeek}</td>
      </>
    );
  }
  return (
    <>
      <td className={CELL}>{formatNumber(run.net)}</td>
      <td className={CELL}>{run.order}</td>
      <td className={CELL}>{run.cost}</td>
    </>
  );
}

/** The chart's table (NFR-6): every Uke of either run, Netto lager, Ordre and Kostnad så langt. */
function RunsTable({ replay }: { replay: ReplayData }) {
  const both = replay.class_game !== null;
  const runs = both ? [walk.runReplay, walk.runClass] : [walk.runReplay];
  return (
    <table className="mt-3 w-full border-collapse text-label text-ink" data-replay-table="">
      <caption className="text-left text-label text-ink-secondary">{both ? walk.tableCaption : walk.tableCaptionAlone}</caption>
      <thead>
        <tr className="border-b border-axis">
          <th scope="col" className="py-1 text-left align-bottom font-semibold">
            {nb.terms.week}
          </th>
          {runs.map((run) => (
            <RunHeaders key={run} run={run} />
          ))}
        </tr>
      </thead>
      <tbody>
        {walkthroughRows(replay).map((row) => (
          <tr key={row.week} className="border-b border-hairline">
            <th scope="row" className="py-1 text-left font-normal">
              {formatNumber(row.week)}
            </th>
            <Cells run={row.replay} />
            {both ? <Cells run={row.klass} /> : null}
          </tr>
        ))}
      </tbody>
    </table>
  );
}

function RunHeaders({ run }: { run: string }) {
  return (
    <>
      <th scope="col" className={HEAD}>
        {walk.columnNet(run)}
      </th>
      <th scope="col" className={HEAD}>
        {walk.columnOrder(run)}
      </th>
      <th scope="col" className={HEAD}>
        {walk.columnCost(run)}
      </th>
    </>
  );
}
