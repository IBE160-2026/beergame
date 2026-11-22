import { nb } from "@/copy/nb";
import { osloDateText } from "@/modules/sessions/dates";

import type { MyTest, MyTestItem } from "./api";

const copy = nb.tests.individual;

/** Where the Individual test page stands, from the api's answer or refusal alone (AD-10). */
export type TestView = "statement" | "open" | "closed" | "locked" | "denied" | "other";

export function testView(data: MyTest | undefined, code: string | null): TestView {
  if (data) return data.state;
  if (code === "replay_required") return "locked";
  if (code === "forbidden") return "denied";
  return "other";
}

/** «Testfrist to. 18. des. kl. 23:59.», or null when the Class session has none. */
export function deadlineLine(test: Pick<MyTest, "test_deadline">): string | null {
  return test.test_deadline ? copy.deadline(osloDateText(test.test_deadline)) : null;
}

/** An item's heading and its type in words: «Oppgave 3», «Langsvar». */
export function itemLines(item: Pick<MyTestItem, "number" | "type">): { heading: string; type: string } {
  return { heading: copy.item(item.number), type: copy.types[item.type] };
}
