import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import { nb } from "@/copy/nb";

import { ConfigEntry } from "./ai-models-page";
import type { ModelConfig } from "./api";

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
