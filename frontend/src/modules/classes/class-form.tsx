"use client";

import { useRouter } from "next/navigation";
import { type FormEvent, useEffect, useRef, useState } from "react";

import { ActionError } from "@/components/action-error";
import { Button } from "@/components/button";
import { SelectField } from "@/components/select-field";
import { TextField } from "@/components/text-field";
import { nb } from "@/copy/nb";
import { classPath } from "@/modules/identity/homes";

import { type InstitutionChoice, useCreateClass } from "./api";
import { type ClassField, type ClassValues, classErrors, clean, type FieldErrors, firstInvalid, refusalFields } from "./classes";

const copy = nb.classes.create;

const FIELD_ID: Record<ClassField, string> = {
  name: "class-name",
  institution_id: "class-institution",
  course_code: "class-course-code",
};

/**
 * «Lag Klasse» (Story 4.1, FR-6, UX-DR11): Navn, Institusjon and an optional Emnekode in one
 * column, and the page's one primary button. A refused field shows the Tekstfelt's invalid state
 * with the reason under it, focus goes to the first refused field, and nothing is stored. After
 * the first press each reason follows what is typed, so it goes as soon as the field is right; a
 * general failure line goes when the form changes or is sent again. A created Class opens its page.
 */
export function ClassForm({ institutions }: { institutions: readonly InstitutionChoice[] }) {
  const router = useRouter();
  const action = useCreateClass();
  const [errors, setErrors] = useState<FieldErrors>({});
  const [submitted, setSubmitted] = useState(false);
  const [focusRequest, setFocusRequest] = useState<{ field: ClassField; n: number }>();
  const formRef = useRef<HTMLFormElement>(null);

  useEffect(() => {
    if (focusRequest) document.getElementById(FIELD_ID[focusRequest.field])?.focus();
  }, [focusRequest]);

  function values(): ClassValues {
    const data = new FormData(formRef.current ?? undefined);
    return {
      name: String(data.get("name") ?? ""),
      institution_id: String(data.get("institution_id") ?? ""),
      course_code: String(data.get("course_code") ?? ""),
    };
  }

  function focus(found: FieldErrors) {
    const field = firstInvalid(found);
    if (field) setFocusRequest((prev) => ({ field, n: (prev?.n ?? 0) + 1 }));
  }

  function onChange(field: ClassField) {
    if (action.isError) action.reset();
    if (!submitted) return;
    const reason = classErrors(values())[field];
    setErrors((prev) => ({ ...prev, [field]: reason }));
  }

  function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (action.isPending) return;
    action.reset();
    const current = values();
    const found = classErrors(current);
    setErrors(found);
    setSubmitted(true);
    if (firstInvalid(found)) {
      focus(found);
      return;
    }
    const code = clean(current.course_code);
    action.mutate(
      { name: clean(current.name), institution_id: current.institution_id, course_code: code || null },
      {
        onSuccess: (created) => router.push(classPath(created.id)),
        onError: (failure) => {
          const refused = refusalFields(failure);
          if (firstInvalid(refused)) {
            setErrors(refused);
            focus(refused);
          }
        },
      },
    );
  }

  const general = action.isError && !firstInvalid(refusalFields(action.error)) ? copy.failed : undefined;

  return (
    <form ref={formRef} method="post" noValidate onSubmit={onSubmit} className="mt-8 flex max-w-md flex-col gap-5">
      <TextField
        id={FIELD_ID.name}
        name="name"
        autoComplete="off"
        label={copy.name}
        error={errors.name}
        onChange={() => onChange("name")}
      />
      <SelectField
        id={FIELD_ID.institution_id}
        name="institution_id"
        label={copy.institution}
        defaultValue=""
        error={errors.institution_id}
        hint={institutions.length === 0 ? copy.noInstitutions : undefined}
        onChange={() => onChange("institution_id")}
      >
        <option value="">{copy.choose}</option>
        {institutions.map((institution) => (
          <option key={institution.id} value={institution.id}>
            {institution.name}
          </option>
        ))}
      </SelectField>
      <TextField
        id={FIELD_ID.course_code}
        name="course_code"
        autoComplete="off"
        label={copy.courseCode}
        error={errors.course_code}
        onChange={() => onChange("course_code")}
      />
      <ActionError message={general} />
      <Button type="submit" variant="primary" unavailable={action.isPending || action.isSuccess} className="mt-1 w-full">
        {copy.submit}
      </Button>
    </form>
  );
}
