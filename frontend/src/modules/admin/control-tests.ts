import { nb } from "@/copy/nb";
import { ApiRequestError } from "@/lib/api/client";

import { cleanName } from "./institutions";

const errors = nb.admin.controlTests.create.errors;

/** The api's longest Class name (`CLASS_NAME_MAX_LENGTH` in `classes/schemas.py`). */
export const CONTROL_TEST_NAME_MAX_LENGTH = 200;

/** The Class name rule (`class_name` in `classes/schemas.py`), checked before sending: the line
 * under the name field, or undefined. The api has the last word. */
export function controlTestNameError(value: string): string | undefined {
  const name = cleanName(value);
  if (!name) return errors.name_empty;
  if ([...name].length > CONTROL_TEST_NAME_MAX_LENGTH) return errors.name_too_long;
  if (/[\u0000-\u001f\u007f-\u009f]/.test(name)) return errors.name_invalid;
  return undefined;
}

/** A refused «Opprett Kontrolltest» as lines by field (`name`, `scoring_guide_id`,
 * `model_config_id`), or `general` for a refusal that belongs to no field. An empty object for a
 * failure with no words of its own: the form's general line then says it was not created. */
export function controlTestFieldErrors(error: unknown): Record<string, string> {
  if (!(error instanceof ApiRequestError)) return {};
  if (error.code === "operator_institution_missing") return { general: errors.operator_institution_missing };
  if (error.code !== "invalid_request") return {};
  const found: Record<string, string> = {};
  for (const [field, reason] of Object.entries(error.fields)) {
    if (typeof reason !== "string") continue;
    found[field] = Object.hasOwn(errors, reason) ? errors[reason] : errors.unknown;
  }
  return found;
}
