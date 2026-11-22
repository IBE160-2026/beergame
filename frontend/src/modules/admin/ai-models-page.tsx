"use client";

import { type FormEvent, useState } from "react";

import { ActionError } from "@/components/action-error";
import { Button } from "@/components/button";
import { Link } from "@/components/link";
import { SelectField } from "@/components/select-field";
import { LoadingNote, Skeleton } from "@/components/skeleton";
import { nb } from "@/copy/nb";
import { formatNumber } from "@/lib/number-format";
import { usePageState } from "@/lib/page-state";
import { GuardedPage } from "@/modules/identity/home-page";
import { ADMIN_AI_COST_PATH, HOME_PATH } from "@/modules/identity/homes";
import { PageShell } from "@/modules/identity/page-shell";

import { levelName, modelName, percentText, refusalText, usdText, FREEZE_SESSIONS_MAX } from "./ai-models";
import {
  type DailySpend,
  type ModelConfig,
  type ModelSession,
  modelConfigsKey,
  useDailySpend,
  useFreezeModel,
  useLiftFreeze,
  useModelConfigs,
  useModelFreeze,
  useModelSessions,
  usePinModel,
} from "./api";
import { formatTime } from "./audit";
import { dailySpendPath, dayText, dayUsdText, shiftDay } from "./daily-spend";
import { sessionLabel } from "./evaluation";
import { formatDate } from "./invitations";
import { Cell, type RowLine, RowMessage } from "./user-list";

const copy = nb.admin.aiCost;

const CRUMBS = [
  { label: nb.homes.adminArea, href: HOME_PATH.adminArea },
  { label: copy.title, href: ADMIN_AI_COST_PATH },
] as const;

const TABLE =
  "w-full border-collapse text-left text-table-cell tabular-nums lining-nums text-ink @max-[60em]:block lg:text-table-cell-laptop";
const HEAD = "py-2 pr-6 align-bottom text-label font-semibold text-ink";
const ROW = "border-b border-hairline align-baseline @max-[60em]:block @max-[60em]:py-3";
const BODY = "@max-[60em]:block @max-[60em]:border-t @max-[60em]:border-axis";
const LEAD = "mt-2 mb-5 max-w-2xl text-body-phone text-ink-secondary lg:text-body";
const TEXT = "text-body-phone text-ink lg:text-body";

/**
 * «KI-kostnad» in the Admin-område, its first page (Story 15.5, FR-68, FR-78, UX-DR57): the model
 * configs with the measured figures of their Effort levels as stored, the model of each Class
 * session (pinned before its Start date, read-only once locked) and the freeze of one model for a
 * learning study, whose button is the page's one primary button. Story 15.7 adds the AI spend of
 * a day (`day`, from `?dag=`; today without it) with its alert, first on the page; Story 15.6 adds
 * the cost per Class session and the limit. Only an Admin sees it; anyone else gets the
 * permission-denied page.
 */
export function AiModelsPage({ day }: { day?: string }) {
  return (
    <GuardedPage page="adminArea">
      {(user, updatedAt) => (
        <PageShell user={user} title={copy.title} updatedAt={updatedAt} crumbs={CRUMBS}>
          <p className="mt-2 max-w-2xl text-body-phone text-ink-secondary lg:text-body">{copy.lead}</p>
          <DaySection day={day} />
          <Content />
        </PageShell>
      )}
    </GuardedPage>
  );
}

function Content() {
  const configs = useModelConfigs();
  const pageState = usePageState(configs, modelConfigsKey);
  const items = configs.data?.items ?? [];
  return (
    <>
      <section aria-labelledby="configs-title" className="mt-10 @container">
        <h2 id="configs-title" className="text-headline text-ink">
          {copy.configs.title}
        </h2>
        <p className={LEAD}>{copy.configs.lead}</p>
        {pageState.phase === "loading" || pageState.phase === "slow" ? (
          <div>
            <Skeleton heading={false} rows={3} columns={5} />
            <LoadingNote visible={pageState.phase === "slow"} />
          </div>
        ) : null}
        {pageState.phase === "failed" ? (
          <div className="flex flex-col items-start gap-3">
            <p role="alert" className="text-body-phone text-restordre lg:text-body">
              {nb.system.pageError}
            </p>
            <Button onClick={pageState.retry}>{nb.system.retry}</Button>
          </div>
        ) : null}
        {pageState.phase === "ready" ? <ConfigList items={items} /> : null}
      </section>
      {pageState.phase === "ready" ? (
        <>
          <Sessions configs={items} />
          <FreezeSection configs={items} />
        </>
      ) : null}
    </>
  );
}

/** «KI-kostnad per dag» (Story 15.7, FR-69): the day's AI spend across every scope, the alert
 * amount or that none is set, the alert when the sweep sent it, the dearest Class sessions and the
 * simulation runs apart, with links to the days next to it. Read again every minute. */
function DaySection({ day }: { day?: string }) {
  const spend = useDailySpend(day);
  const text = copy.day;
  return (
    <section aria-labelledby="day-title" className="mt-10 @container">
      <h2 id="day-title" className="text-headline text-ink">
        {text.title}
      </h2>
      <p className={LEAD}>{text.lead}</p>
      {spend.isPending ? <Skeleton heading={false} rows={3} columns={3} /> : null}
      {spend.isError ? (
        <p role="alert" className="text-body-phone text-restordre lg:text-body">
          {nb.system.pageError}
        </p>
      ) : null}
      {spend.data ? <DaySpendView found={spend.data} /> : null}
    </section>
  );
}

export function DaySpendView({ found }: { found: DailySpend }) {
  const text = copy.day;
  const columns = text.columns;
  const previous = shiftDay(found.day, -1);
  const next = shiftDay(found.day, 1);
  return (
    <div className="flex flex-col gap-4">
      <div>
        <h3 className="text-step-title font-semibold text-ink">{dayText(found.day)}</h3>
        <p className={`${TEXT} mt-1 tabular-nums lining-nums`}>
          {text.total(dayUsdText(found.total_usd), formatNumber(found.calls))}
        </p>
        <p className={`${TEXT} tabular-nums lining-nums`}>
          {found.alert_usd === null ? text.noAlert : text.alertLimit(dayUsdText(found.alert_usd))}
        </p>
        {found.passed || found.alerted_at ? (
          <p className={`${TEXT} font-semibold`}>
            {text.passed}
            {found.alerted_at ? ` ${text.alerted(formatTime(found.alerted_at))}` : ""}
          </p>
        ) : null}
      </div>
      {found.sessions.length === 0 ? (
        <p className={TEXT}>{text.noSessions}</p>
      ) : (
        <div>
          <table className={TABLE}>
            <thead className="@max-[60em]:hidden">
              <tr className="border-b border-axis">
                <th scope="col" className={HEAD}>
                  {columns.session}
                </th>
                <th scope="col" className={HEAD}>
                  {columns.cost}
                </th>
                <th scope="col" className={HEAD}>
                  {columns.calls}
                </th>
              </tr>
            </thead>
            <tbody className={BODY}>
              {found.sessions.map((item) => (
                <tr key={item.class_session_id} className={ROW}>
                  <Cell label={columns.session}>
                    <span className="font-semibold [overflow-wrap:anywhere]">{item.label}</span>
                    {item.institution_name ? (
                      <span className="block text-ink-secondary [overflow-wrap:anywhere]">{item.institution_name}</span>
                    ) : null}
                  </Cell>
                  <Cell label={columns.cost}>{dayUsdText(item.usd)}</Cell>
                  <Cell label={columns.calls}>{formatNumber(item.calls)}</Cell>
                </tr>
              ))}
            </tbody>
          </table>
          {found.session_count > found.sessions.length ? (
            <p className="mt-2 text-label text-ink-secondary">{text.more(found.sessions.length, found.session_count)}</p>
          ) : null}
        </div>
      )}
      <p className={`${TEXT} tabular-nums lining-nums`}>{text.evaluation(dayUsdText(found.evaluation_usd))}</p>
      <nav aria-label={text.days} className="flex flex-col items-start">
        <Link href={dailySpendPath(previous)} standalone>
          {text.previous(dayText(previous))}
        </Link>
        {next <= found.today ? (
          <Link href={dailySpendPath(next)} standalone>
            {text.next(dayText(next))}
          </Link>
        ) : null}
      </nav>
    </div>
  );
}

function ConfigList({ items }: { items: ModelConfig[] }) {
  if (items.length === 0) return <p className={TEXT}>{copy.configs.empty}</p>;
  return (
    <ul className="flex flex-col gap-10">
      {items.map((item) => (
        <li key={item.id}>
          <ConfigEntry item={item} />
        </li>
      ))}
    </ul>
  );
}

/** One model config: its name with its standing, its facts, and a table of its Effort levels. */
export function ConfigEntry({ item }: { item: ModelConfig }) {
  const facts = copy.configs.facts;
  const columns = copy.configs.columns;
  const marks: string[] = [];
  if (item.active_default) marks.push(copy.configs.isDefault);
  if (item.frozen) marks.push(copy.configs.isFrozen);
  return (
    <article aria-labelledby={`config-${item.id}`}>
      <h3 id={`config-${item.id}`} className="text-step-title font-semibold text-ink [overflow-wrap:anywhere]">
        {modelName(item)}
      </h3>
      {marks.length > 0 ? <p className="mt-1 text-label text-ink-secondary">{marks.join(" · ")}</p> : null}
      <dl className="mt-3 grid max-w-2xl grid-cols-[auto_1fr] gap-x-6 gap-y-1 text-body-phone lg:text-body">
        {(
          [
            [facts.provider, item.provider],
            [facts.endpoint, item.endpoint],
            [facts.region, item.region],
            [facts.version, item.model_version],
          ] as const
        ).map(([label, value]) => (
          <div key={label} className="contents">
            <dt className="text-ink-secondary">{label}</dt>
            <dd className="min-w-0 text-ink [overflow-wrap:anywhere]">{value}</dd>
          </div>
        ))}
      </dl>
      {!item.may_answer ? (
        <p className="mt-3 max-w-2xl text-body-phone text-restordre lg:text-body">{copy.configs.noKey}</p>
      ) : null}
      <div className="mt-4 @container">
        <table className={TABLE}>
          <thead className="@max-[60em]:hidden">
            <tr className="border-b border-axis">
              {[columns.level, columns.cost, columns.fallback, columns.switched, columns.measured].map((heading) => (
                <th key={heading} scope="col" className={HEAD}>
                  {heading}
                </th>
              ))}
            </tr>
          </thead>
          <tbody className={BODY}>
            {item.effort_levels.map((level) => {
              const found = level.measurement;
              const figure = (value: string | null | undefined, show: (v: string) => string) =>
                value === null || value === undefined ? copy.configs.none : show(value);
              return (
                <tr key={level.name} className={ROW}>
                  <Cell label={columns.level}>
                    <span className="font-semibold">{levelName(level)}</span>
                    {found && !level.offered ? (
                      <span className="block text-ink-secondary">{copy.configs.notOffered}</span>
                    ) : null}
                  </Cell>
                  <Cell label={columns.cost}>{figure(found?.cost_per_game_usd, usdText)}</Cell>
                  <Cell label={columns.fallback}>{figure(found?.fallback_share, percentText)}</Cell>
                  <Cell label={columns.switched}>{figure(found?.switched_share, percentText)}</Cell>
                  <Cell label={columns.measured}>
                    {!found
                      ? copy.configs.notMeasured
                      : found.mock
                        ? copy.configs.mockMeasured
                        : copy.configs.measuredOn(String(found.games ?? 0), formatDate(found.approved_at))}
                  </Cell>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </article>
  );
}

function Sessions({ configs }: { configs: ModelConfig[] }) {
  const sessions = useModelSessions();
  const items = sessions.data?.items ?? [];
  const pinnable = configs.filter((item) => item.pinnable);
  return (
    <section aria-labelledby="model-sessions-title" className="mt-12 @container">
      <h2 id="model-sessions-title" className="text-headline text-ink">
        {copy.sessions.title}
      </h2>
      <p className={LEAD}>{copy.sessions.lead}</p>
      {sessions.isPending ? <Skeleton heading={false} rows={3} columns={4} /> : null}
      {sessions.isError ? (
        <p role="alert" className="text-body-phone text-restordre lg:text-body">
          {nb.system.pageError}
        </p>
      ) : null}
      {sessions.isSuccess && items.length === 0 ? <p className={TEXT}>{copy.sessions.empty}</p> : null}
      {items.length > 0 ? <SessionTable items={items} pinnable={pinnable} /> : null}
    </section>
  );
}

function SessionTable({ items, pinnable }: { items: ModelSession[]; pinnable: ModelConfig[] }) {
  const pin = usePinModel();
  const [line, setLine] = useState<RowLine>();
  const columns = copy.sessions.columns;

  function onPin(item: ModelSession, modelConfigId: string) {
    if (pin.isPending) return;
    setLine(undefined);
    const label = sessionLabel(item);
    pin.mutate(
      { id: item.id, modelConfigId },
      {
        onSuccess: (found) =>
          setLine({
            key: item.id,
            text: copy.sessions.pinned(label, found.model_name ?? copy.sessions.noModel),
            refused: false,
          }),
        onError: (error) =>
          setLine({
            key: item.id,
            text: refusalText(error, copy.sessions.refused, copy.sessions.failed),
            refused: true,
          }),
      },
    );
  }

  return (
    <table className={TABLE}>
      <thead className="@max-[60em]:hidden">
        <tr className="border-b border-axis">
          <th scope="col" className={HEAD}>
            {columns.session}
          </th>
          <th scope="col" className={`${HEAD} w-[9em]`}>
            {columns.start}
          </th>
          <th scope="col" className={HEAD}>
            {columns.model}
          </th>
          <th scope="col" className={HEAD}>
            {columns.level}
          </th>
          <th scope="col" className={HEAD}>
            {columns.action}
          </th>
        </tr>
      </thead>
      <tbody className={BODY}>
        {items.map((item) => (
          <SessionRow
            // A new pinned config re-seeds the row's choice, so it never shows a stale model.
            key={`${item.id}:${item.model_config_id ?? ""}`}
            item={item}
            pinnable={pinnable}
            busy={pin.isPending}
            line={line?.key === item.id ? line : undefined}
            onPin={(id) => onPin(item, id)}
          />
        ))}
      </tbody>
    </table>
  );
}

function SessionRow({
  item,
  pinnable,
  busy,
  line,
  onPin,
}: {
  item: ModelSession;
  pinnable: ModelConfig[];
  busy: boolean;
  line?: RowLine;
  onPin: (modelConfigId: string) => void;
}) {
  const columns = copy.sessions.columns;
  const label = sessionLabel(item);
  const current = pinnable.some((config) => config.id === item.model_config_id)
    ? (item.model_config_id ?? "")
    : (pinnable[0]?.id ?? "");
  const [chosen, setChosen] = useState(current);
  const held = item.frozen;
  return (
    <tr className={ROW}>
      <Cell label={columns.session}>
        <span className="font-semibold [overflow-wrap:anywhere]">{label}</span>
        {item.institution_name ? (
          <span className="block text-ink-secondary [overflow-wrap:anywhere]">{item.institution_name}</span>
        ) : null}
        {item.in_freeze ? <span className="block text-ink-secondary">{copy.sessions.inStudy}</span> : null}
      </Cell>
      <Cell label={columns.start}>{item.start_at ? formatDate(item.start_at) : copy.sessions.noStart}</Cell>
      <Cell label={columns.model}>
        {held ? (
          <span className="[overflow-wrap:anywhere]">
            {held.model_name ?? copy.sessions.noModel}
            <span className="block text-ink-secondary">
              {copy.sessions.lockedModel(held.model_version ?? copy.configs.none, held.endpoint ?? copy.configs.none)}
            </span>
            <span className="block text-ink-secondary">
              {copy.sessions.prompts}:{" "}
              {Object.entries(held.prompt_versions)
                .map(([purpose, version]) => copy.sessions.promptVersion(purpose, version))
                .join(", ")}
            </span>
          </span>
        ) : (
          <span className="[overflow-wrap:anywhere]">
            {item.model_name && item.model_version
              ? modelName({
                  name: item.model_name,
                  model_version: item.model_version,
                })
              : copy.sessions.noModel}
            {item.ai_mode !== "llm" ? (
              <span className="block text-ink-secondary">{copy.sessions.ruleBased}</span>
            ) : null}
          </span>
        )}
      </Cell>
      <Cell label={columns.level}>{(held ? held.effort_level : item.effort_level) ?? copy.configs.none}</Cell>
      <td className="py-3 @max-[60em]:block @max-[60em]:pt-2 @max-[60em]:pb-0 @min-[60em]:w-[22em]">
        {item.locked ? (
          <p className={TEXT}>
            <span className="font-semibold">{copy.sessions.locked}.</span> {copy.sessions.lockedNote}
          </p>
        ) : pinnable.length > 0 ? (
          <form
            method="post"
            noValidate
            className="flex flex-col gap-3"
            onSubmit={(event: FormEvent<HTMLFormElement>) => {
              event.preventDefault();
              if (chosen) onPin(chosen);
            }}
          >
            <SelectField
              id={`model-${item.id}`}
              label={copy.sessions.choose(label)}
              value={chosen}
              onChange={(event) => setChosen(event.target.value)}
            >
              {pinnable.map((config) => (
                <option key={config.id} value={config.id}>
                  {modelName(config)}
                </option>
              ))}
            </SelectField>
            <Button
              type="submit"
              unavailable={busy}
              className="[overflow-wrap:anywhere] @max-[60em]:w-full @min-[60em]:px-3 @min-[60em]:text-left"
            >
              {copy.sessions.pin(label)}
            </Button>
          </form>
        ) : null}
        {item.warnings.includes("provider_key_missing") ? (
          <p className="mt-2 max-w-sm text-body-phone text-restordre lg:text-body">{copy.sessions.keyMissing}</p>
        ) : null}
        <RowMessage line={line} />
      </td>
    </tr>
  );
}

/** «Frys en modell for en studie»: the freeze in force with its lift, or the form whose button is
 * the page's one primary button. */
function FreezeSection({ configs }: { configs: ModelConfig[] }) {
  const state = useModelFreeze();
  const sessions = useModelSessions();
  const lift = useLiftFreeze();
  const [lifted, setLifted] = useState(false);
  const form = copy.freeze;
  const active = state.data?.active;
  return (
    <section aria-labelledby="freeze-title" className="mt-12">
      <h2 id="freeze-title" className="text-headline text-ink">
        {form.title}
      </h2>
      <p className={LEAD}>{form.lead}</p>
      {state.isPending ? <Skeleton heading={false} rows={2} columns={2} /> : null}
      {state.isError ? (
        <p role="alert" className="text-body-phone text-restordre lg:text-body">
          {nb.system.pageError}
        </p>
      ) : null}
      {active ? (
        <div className="flex max-w-xl flex-col items-start gap-4">
          <p className={TEXT}>
            {form.active(
              active.model_name && active.model_version
                ? modelName({
                    name: active.model_name,
                    model_version: active.model_version,
                  })
                : copy.sessions.noModel,
              active.class_session_ids.length,
              formatTime(active.frozen_at),
            )}
          </p>

          <Button
            unavailable={lift.isPending}
            className="w-full sm:w-auto"
            onClick={() => {
              if (lift.isPending) return;
              setLifted(false);
              lift.mutate(active.id, { onSuccess: () => setLifted(true) });
            }}
          >
            {form.lift}
          </Button>
        </div>
      ) : null}
      {lifted && !active ? (
        <p role="status" className={`${TEXT} mb-4`}>
          {form.lifted}
        </p>
      ) : null}
      {/* Outside the freeze block, so a refused lift keeps its reason after the page reads again. */}
      <ActionError message={lift.isError ? refusalText(lift.error, form.refused, form.liftFailed) : undefined} />
      {state.isSuccess && !active && sessions.isPending ? <Skeleton heading={false} rows={2} columns={2} /> : null}
      {state.isSuccess && !active && sessions.isError ? (
        <p role="alert" className="text-body-phone text-restordre lg:text-body">
          {nb.system.pageError}
        </p>
      ) : null}
      {state.isSuccess && !active && sessions.isSuccess ? (
        <FreezeForm
          configs={configs.filter((item) => item.pinnable)}
          sessions={sessions.data.items.filter((item) => !item.locked)}
        />
      ) : null}
    </section>
  );
}

function FreezeForm({ configs, sessions }: { configs: ModelConfig[]; sessions: ModelSession[] }) {
  const freeze = useFreezeModel();
  const form = copy.freeze;
  const [modelId, setModelId] = useState((configs.find((item) => item.active_default) ?? configs[0])?.id ?? "");
  const [chosen, setChosen] = useState<string[]>([]);
  const [choiceError, setChoiceError] = useState<string>();

  if (configs.length === 0) return <p className={TEXT}>{form.none}</p>;
  if (sessions.length === 0) return <p className={TEXT}>{form.noSessions}</p>;

  function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (freeze.isPending) return;
    freeze.reset();
    const ids = chosen.filter((id) => sessions.some((item) => item.id === id));
    const problem = ids.length === 0 ? form.pickOne : ids.length > FREEZE_SESSIONS_MAX ? form.tooMany : undefined;
    setChoiceError(problem);
    if (problem) return;
    freeze.mutate({ modelConfigId: modelId || configs[0].id, ids }, { onSuccess: () => setChosen([]) });
  }

  return (
    <form method="post" noValidate onSubmit={onSubmit} className="flex max-w-xl flex-col gap-5">
      <SelectField
        id="freeze-model"
        label={form.model}
        value={modelId}
        onChange={(event) => setModelId(event.target.value)}
      >
        {configs.map((config) => (
          <option key={config.id} value={config.id}>
            {modelName(config)}
          </option>
        ))}
      </SelectField>
      <fieldset aria-describedby={choiceError ? "freeze-sessions-error" : undefined} className="flex flex-col gap-1">
        <legend className="mb-2 text-label text-ink">{form.sessions}</legend>
        {sessions.map((item) => (
          <label
            key={item.id}
            className="group relative flex min-h-tap-target-min cursor-pointer items-center gap-3 rounded-sm pr-2 text-body-phone text-ink has-focus-visible:outline-2 has-focus-visible:outline-offset-2 has-focus-visible:outline-ink lg:text-body"
          >
            <input
              type="checkbox"
              className="absolute inset-0 m-0 size-full cursor-pointer opacity-0"
              checked={chosen.includes(item.id)}
              onChange={(event) => {
                setChoiceError(undefined);
                setChosen((prev) => (event.target.checked ? [...prev, item.id] : prev.filter((id) => id !== item.id)));
              }}
            />
            <span
              aria-hidden="true"
              className="flex size-5 shrink-0 items-center justify-center rounded-sm border border-ink-muted bg-paper group-hover:border-ink group-has-checked:border-ink group-has-checked:bg-ink group-has-checked:text-paper"
            >
              <svg viewBox="0 0 16 16" className="hidden size-3.5 group-has-checked:block" fill="none">
                <path
                  d="M3 8.5l3 3 7-7"
                  stroke="currentColor"
                  strokeWidth="2"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                />
              </svg>
            </span>
            <span className="min-w-0 [overflow-wrap:anywhere]">{sessionLabel(item)}</span>
          </label>
        ))}
        {choiceError ? (
          <p id="freeze-sessions-error" className="text-body-phone text-restordre">
            {choiceError}
          </p>
        ) : null}
      </fieldset>
      <ActionError message={freeze.isError ? refusalText(freeze.error, form.refused, form.failed) : undefined} />
      <Button type="submit" variant="primary" unavailable={freeze.isPending} className="w-full sm:w-auto sm:self-start">
        {form.submit}
      </Button>
    </form>
  );
}
