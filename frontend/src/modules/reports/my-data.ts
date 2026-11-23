import { nb } from "@/copy/nb";
import { formatNumber } from "@/lib/number-format";
import { calendarDateText, osloDateText } from "@/modules/sessions/dates";

import type { MyDataField, MyDataItem } from "./api";

const copy = nb.myData;

/** One stored value as the page shows it (pure, so it is tested without a browser): a code by its
 * label in `nb.ts` (a code not listed shows as stored), a time in Europe/Oslo, a number in
 * Norwegian notation, «Ja»/«Nei», and «–» for nothing stored. */
export function fieldValue(field: MyDataField): string {
  const { kind, value } = field;
  if (value === null || value === "") return copy.none;
  switch (kind) {
    case "bool":
      return value === "true" ? copy.yes : copy.no;
    case "datetime":
      return osloDateText(value);
    case "date":
      return calendarDateText(value);
    case "number":
      return formatNumber(value);
    case "code": {
      const codes = Object.hasOwn(copy.codes, field.key) ? copy.codes[field.key] : undefined;
      return codes && Object.hasOwn(codes, value) ? codes[value]! : value;
    }
    default:
      return value;
  }
}

/** A field's label; a key not listed shows as stored. */
export function fieldLabel(key: string): string {
  return Object.hasOwn(copy.fields, key) ? copy.fields[key]! : key;
}

/** What a row is, with its Class and Klasseøkt: «Uke · class-of-1994, Klasseøkt 1». */
export function itemHeading(item: MyDataItem): { kind: string; context: string | null } {
  return {
    kind: Object.hasOwn(copy.kinds, item.kind) ? copy.kinds[item.kind]! : item.kind,
    context: item.class_name === null ? null : copy.context(item.class_name, item.session_number),
  };
}
