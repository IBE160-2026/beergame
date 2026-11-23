import { nb } from "@/copy/nb";

import { tenth, whole } from "./class-report";
import type { ClassLearning, ReportDistribution } from "./class-report-api";

/**
 * The learning part's text and order (Story 14.2, UX-DR55). Every number is the api's (AD-10):
 * these only pick the words and format with the shared number formatter. A bar's share (the api's
 * percent over 100) only sets the width of an `aria-hidden` bar.
 */
const copy = nb.classReport.learning;

type Question = ClassLearning["questions"][number];
type StartingItem = ClassLearning["starting_task"]["items"][number];

const percent = (value: string | null | undefined) =>
  value == null ? "–" : copy.percent(tenth(value));
const share = (value: string | null | undefined) =>
  value == null ? 0 : Math.min(1, Math.max(0, Number(value) / 100));

export type LearningBar = {
  key: string;
  label: string;
  count: string;
  share: number;
  reads: string;
};

/** «14 av 20 studenter har levert testen. 3 kan fortsatt levere.» */
export function learningStatus(
  data: Pick<ClassLearning, "students" | "submitted" | "still_to_submit">,
): string {
  if (data.students === 0) return copy.noStudents;
  return copy.status(data.submitted, data.students, data.still_to_submit);
}

/** One Starting task item beside its test item: the Starting task's share right and the test's mean. */
export function startingBars(item: StartingItem): LearningBar[] {
  return [
    {
      key: "start",
      label: copy.starting.startLabel,
      count: percent(item.start_percent),
      share: share(item.start_percent),
      reads:
        item.start_percent == null
          ? `${copy.starting.startLabel}: ${copy.questions.noAnswers}`
          : copy.starting.startReads(item.start_correct, item.students, tenth(item.start_percent)),
    },
    {
      key: "test",
      label: copy.starting.testLabel,
      count: percent(item.test_percent),
      share: share(item.test_percent),
      reads:
        item.test_percent == null
          ? `${copy.starting.testLabel}: ${copy.questions.noAnswers}`
          : copy.starting.testReads(item.test_right, item.students, tenth(item.test_percent)),
    },
  ];
}

export type StartingRow = { key: string; head: string; cells: string[] };

/** The Starting task table, in the test's order. */
export function startingRows(items: readonly StartingItem[]): StartingRow[] {
  return items.map((item) => ({
    key: String(item.number),
    head: copy.questionLabel(item.number, item.title),
    cells: [
      whole(item.students),
      `${whole(item.start_correct)} (${percent(item.start_percent)})`,
      whole(item.test_right),
      percent(item.test_percent),
    ],
  }));
}

/** A question's label: «3. Flervalg om årsaker», or its title alone when it was taken out. */
export function questionLabel(question: Question): string {
  return question.number == null
    ? question.title
    : copy.questionLabel(question.number, question.title);
}

/** Results per question as bars, in the test's order: a computed question's mean, a long answer
 * marked as the AI's, a question taken out marked as such. */
export function questionBars(questions: readonly Question[]): LearningBar[] {
  return questions.map((q) => {
    const label = questionLabel(q);
    if (q.excluded) {
      return {
        key: q.id,
        label,
        count: copy.questions.excluded,
        share: 0,
        reads: `${label}: ${copy.questions.excluded}`,
      };
    }
    if (q.scoring === "ai") {
      return {
        key: q.id,
        label,
        count: copy.questions.aiScored,
        share: 0,
        reads: `${copy.questions.longReads(label, q.answered, q.students)}. ${copy.questions.aiScored}`,
      };
    }
    return {
      key: q.id,
      label,
      count: percent(q.percent),
      share: share(q.percent),
      reads:
        q.percent == null
          ? `${label}: ${copy.questions.noAnswers}`
          : copy.questions.reads(
              label,
              tenth(q.percent),
              q.answered,
              q.students,
            ),
    };
  });
}

/** Results per question as a table: handed in, right, partly, wrong, not answered and the mean. */
export function questionRows(questions: readonly Question[]): StartingRow[] {
  return questions.map((q) => {
    const label = questionLabel(q);
    if (q.excluded)
      return {
        key: q.id,
        head: label,
        cells: [copy.questions.excluded, "–", "–", "–", "–", "–"],
      };
    if (q.scoring === "ai") {
      return {
        key: q.id,
        head: label,
        cells: [
          whole(q.students),
          "–",
          "–",
          "–",
          whole(q.students - q.answered),
          copy.questions.aiScored,
        ],
      };
    }
    return {
      key: q.id,
      head: label,
      cells: [
        whole(q.students),
        whole(q.right),
        whole(q.partly),
        whole(q.wrong),
        whole(q.not_answered),
        percent(q.percent),
      ],
    };
  });
}

/** The AI part's line: off, not ready, or how many handed-in tests are assessed. */
export function aiLine(ai: ClassLearning["ai"]): string {
  if (ai.state === "switched_off") return copy.ai.switchedOff;
  if (ai.state === "not_ready") return copy.ai.notReady;
  return copy.ai.ready(ai.ready, ai.submitted);
}

/** «Median 62,5. Midterste halvdel 48,0–71,3.» in points of 100. */
export function scoreSummary(spread: ReportDistribution): string {
  return nb.classReport.summary(
    tenth(spread.median),
    tenth(spread.lower_quartile),
    tenth(spread.upper_quartile),
  );
}

/** The score table: one row per 10-point band, totals and Core-only subscores. */
export function bandRows(ai: ClassLearning["ai"]): StartingRow[] {
  return ai.bands.map((band) => ({
    key: String(band.low),
    head: copy.ai.band(band.low, band.high),
    cells: [whole(band.total), whole(band.core)],
  }));
}
