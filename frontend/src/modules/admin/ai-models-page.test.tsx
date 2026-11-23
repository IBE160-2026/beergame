import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import { nb } from "@/copy/nb";

import { ConfigEntry, DaySpendView } from "./ai-models-page";
import type { DailySpend, ModelConfig } from "./api";
import { formatTime } from "./audit";

const copy = nb.admin.aiCost;
const NBSP = "\u00a0";

const MEASURED: ModelConfig = {
  id: "c1",
  name: "ekte",
  provider: "openrouter",
  endpoint: "https://example.invalid/v1",
  region: "eu",
  model_version: "v1",
  quantisation: "none",
  prompts: { player_order: 1 },
  referenced: true,
  may_answer: false,
  pinnable: true,
  active_default: true,
  frozen: false,
  effort_levels: [
    {
      name: "fast",
      label: "Rask",
      offered: true,
      measurement: {
        mock: false,
        games: 40,
        cost_per_game_usd: "0.0725",
        fallback_share: "0.0125",
        switched_share: "0.025",
        time_per_order_p95_s: "3.4",
        approved_at: "2026-11-20T10:00:00Z",
      },
    },
    { name: "deep", label: null, offered: false, measurement: null },
  ],
};

/** The cells of each body row, in column order. */
function rows(html: string): string[][] {
  const body = html.split("<tbody")[1] ?? "";
  return body
    .split("<tr")
    .slice(1)
    .map((row) =>
      row
        .split("<td")
        .slice(1)
        .map((cell) =>
          `<td${cell}`
            .replace(/<[^>]*>/g, " ")
            .replace(/[ \t\n]+/g, " ")
            .trim(),
        ),
    );
}

describe("«KI-kostnad» config entry (Story 15.5)", () => {
  it("puts each stored figure under its own column", () => {
    const html = renderToStaticMarkup(<ConfigEntry item={MEASURED} />);
    const [fast, deep] = rows(html);
    const c = copy.configs.columns;
    expect(fast).toEqual([
      `${c.level} Rask`,
      `${c.cost} 0,0725${NBSP}USD`,
      `${c.fallback} 1,25${NBSP}%`,
      `${c.switched} 2,5${NBSP}%`,
      `${c.measured} ${copy.configs.measuredOn("40", "20. nov. 2026")}`,
    ]);
    expect(deep).toEqual([
      `${c.level} deep`,
      `${c.cost} ${copy.configs.none}`,
      `${c.fallback} ${copy.configs.none}`,
      `${c.switched} ${copy.configs.none}`,
      `${c.measured} ${copy.configs.notMeasured}`,
    ]);
    expect(html).toContain(copy.configs.isDefault);
    expect(html).toContain(copy.configs.noKey);
  });
});

const DAY: DailySpend = {
  day: "2026-11-19",
  today: "2026-11-19",
  total_usd: "1.90000000",
  calls: 1234,
  evaluation_usd: "0.40000000",
  alert_usd: "1.00",
  passed: true,
  alerted_at: "2026-11-19T09:00:00Z",
  sessions: [
    {
      class_session_id: "s1",
      label: "class-of-1994 · Klasseøkt 1",
      institution_name: "USN Bø",
      usd: "1.50000000",
      calls: 3,
    },
  ],
  session_count: 4,
};

describe("«KI-kostnad per dag» (Story 15.7)", () => {
  it("shows the day's spend, its alert and its dearest Class sessions", () => {
    const html = renderToStaticMarkup(<DaySpendView found={DAY} />);
    expect(html).toContain(copy.day.total(`1,90${NBSP}USD`, `1${NBSP}234`));
    expect(html).toContain(copy.day.alertLimit(`1,00${NBSP}USD`));
    expect(html).toContain(copy.day.passed);
    expect(html).toContain(copy.day.alerted(formatTime("2026-11-19T09:00:00Z")));
    expect(html).toContain("class-of-1994 · Klasseøkt 1");
    expect(html).toContain(`1,50${NBSP}USD`);
    expect(html).toContain(copy.day.more(1, 4));
    expect(html).toContain(copy.day.evaluation(`0,40${NBSP}USD`));
    expect(html).toContain('href="/admin/ki-kostnad?dag=2026-11-18"');
    expect(html).not.toContain("dag=2026-11-20"); // no day after today
  });

  it("says when no daily alert is set and when no Class session spent", () => {
    const html = renderToStaticMarkup(
      <DaySpendView
        found={{
          ...DAY,
          day: "2026-11-18",
          alert_usd: null,
          passed: false,
          alerted_at: null,
          sessions: [],
          session_count: 0,
        }}
      />,
    );
    expect(html).toContain(copy.day.noAlert);
    expect(html).toContain(copy.day.noSessions);
    expect(html).not.toContain(copy.day.passed);
    expect(html).toContain('href="/admin/ki-kostnad?dag=2026-11-19"');
  });
});
