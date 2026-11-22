"use client";

import { type FormEvent, useEffect, useRef, useState } from "react";

import { ActionError } from "@/components/action-error";
import { Button } from "@/components/button";
import { Link } from "@/components/link";
import { SegmentedChoice } from "@/components/segmented-choice";
import { LoadingNote, Skeleton } from "@/components/skeleton";
import { TextField } from "@/components/text-field";
import { nb } from "@/copy/nb";
import { usePageState } from "@/lib/page-state";
import { GuardedPage } from "@/modules/identity/home-page";
import {
  ADMIN_CONTROL_TESTS_PATH,
  ADMIN_INSTITUTIONS_PATH,
  classPath,
  classSessionPath,
  HOME_PATH,
} from "@/modules/identity/homes";
import { PageShell } from "@/modules/identity/page-shell";

import { type ControlTest, type ControlTests, controlTestsKey, useControlTests, useCreateControlTest } from "./api";
import { cleanName } from "./institutions";
import { controlTestFieldErrors, controlTestNameError } from "./control-tests";
import { formatDate } from "./invitations";

const copy = nb.admin.controlTests;

const CRUMBS = [
  { label: nb.homes.adminArea, href: HOME_PATH.adminArea },
  { label: copy.title, href: ADMIN_CONTROL_TESTS_PATH },
] as const;

/**
 * Admin-område → «Kontrolltest» (Story 12.7, FR-82, AD-27, UX-DR57): «Teller aldri med i en
 * Klasseøkt.» first, then the operator's own Institution where a Control test is set up (or what
 * to do first, with a Lenke to «Institusjoner»), the create form (the Class's name, and the
 * Scoring guide version and model config under test as Valgknapper, with the pin stated above
 * the one primary button) and every Control test with what it pinned and Lenker to its Class and
 * Klasseøkt for the Admin who owns it. Only an Admin sees it.
 */
export function ControlTestsPage() {
  return (
    <GuardedPage page="adminArea">
      {(user, updatedAt) => (
        <PageShell user={user} title={copy.title} updatedAt={updatedAt} crumbs={CRUMBS}>
          <ControlTestsBody />
        </PageShell>
      )}
    </GuardedPage>
  );
}

function ControlTestsBody() {
  const found = useControlTests();
  const { phase, retry } = usePageState(found, controlTestsKey);
  const page = found.data;
  return (
    <>
      <p className="mt-2 max-w-2xl border-l-2 border-axis pl-3 text-body-phone font-semibold text-ink lg:text-body">
        {copy.never}
      </p>
      <p className="mt-3 max-w-2xl text-body-phone text-ink-secondary lg:text-body">{copy.lead}</p>
      {phase === "loading" || phase === "slow" ? (
        <div className="mt-8">
          <Skeleton heading={false} rows={3} columns={2} />
          <LoadingNote visible={phase === "slow"} />
        </div>
      ) : null}
      {phase === "failed" ? (
        <div className="mt-8 flex flex-col items-start gap-3">
          <p role="alert" className="text-body-phone text-restordre lg:text-body">
            {nb.system.pageError}
          </p>
          <Button onClick={retry}>{nb.system.retry}</Button>
        </div>
      ) : null}
      {phase === "ready" && page ? (
        <>
          <section aria-labelledby="create-title" className="mt-8">
            <h2 id="create-title" className="text-headline text-ink">
              {copy.create.title}
            </h2>
            {page.operator_institution ? (
              <>
                <p className="mt-2 mb-5 max-w-md text-body-phone text-ink-secondary lg:text-body">
                  {copy.operator(page.operator_institution.name)}
                </p>
                <CreateForm page={page} />
              </>
            ) : (
              <>
                <p className="mt-2 max-w-md text-body-phone text-ink lg:text-body">{copy.noOperator}</p>
                <p className="mt-2">
                  <Link href={ADMIN_INSTITUTIONS_PATH} standalone>
                    {copy.toInstitutions}
                  </Link>
                </p>
              </>
            )}
          </section>
          <section aria-labelledby="control-tests-title" className="mt-12">
            <h2 id="control-tests-title" className="mb-4 text-headline text-ink">
              {copy.list.title}
            </h2>
            {page.items.length === 0 ? (
              <p className="text-body-phone text-ink lg:text-body">{copy.list.empty}</p>
            ) : (
              <ul className="flex max-w-2xl flex-col border-t border-axis">
                {page.items.map((item) => (
                  <ControlTestRow key={item.id} item={item} />
                ))}
              </ul>
            )}
          </section>
        </>
      ) : null}
    </>
  );
}

/** One Control test: its name, then each fact labelled in text, and the Lenker for its owner. */
function ControlTestRow({ item }: { item: ControlTest }) {
  const facts: [string, string][] = [
    [copy.list.institution, item.institution_name ?? copy.list.configGone],
    [copy.list.created, formatDate(item.created_at)],
    [copy.list.guide, copy.guide(item.scoring_guide.version, item.scoring_guide.edited, item.scoring_guide.draft)],
    [
      copy.list.config,
      item.ai_config ? copy.config(item.ai_config.name, item.ai_config.model_version, false) : copy.list.configGone,
    ],
  ];
  return (
    <li className="border-b border-hairline py-4">
      <h3 className="text-body-phone font-semibold text-ink [overflow-wrap:anywhere] lg:text-body">{item.name}</h3>
      <dl className="mt-2 grid grid-cols-1 gap-x-6 gap-y-1 text-body-phone tabular-nums text-ink sm:grid-cols-[max-content_1fr] lg:text-body">
        {facts.map(([label, value]) => (
          <div key={label} className="contents">
            <dt className="text-ink-secondary">{label}</dt>
            <dd className="m-0 [overflow-wrap:anywhere] max-sm:mb-1">{value}</dd>
          </div>
        ))}
      </dl>
      {item.can_open ? (
        <p className="mt-2 flex flex-wrap gap-x-6">
          <Link href={classPath(item.class_id)} standalone>
            {copy.list.openClass(item.name)}
          </Link>
          <Link href={classSessionPath(item.id)} standalone>
            {copy.list.openSession(item.name)}
          </Link>
        </p>
      ) : (
        <p className="mt-2 text-body-phone text-ink-secondary lg:text-body">{copy.list.notOwner}</p>
      )}
    </li>
  );
}

/**
 * «Ny Kontrolltest»: the Class's name, the Scoring guide version and the model config under test.
 * The pin is stated above the button, which says what it does; no dialog follows. A refused field
 * shows its reason beside it; a created Control test empties the name and its line takes focus.
 */
function CreateForm({ page }: { page: ControlTests }) {
  const action = useCreateControlTest();
  const nameRef = useRef<HTMLInputElement>(null);
  const createdRef = useRef<HTMLParagraphElement>(null);
  // The chosen ids; until one is chosen (or when a refetch drops it), the first choice.
  const [guideChoice, setGuide] = useState<string>();
  const [configChoice, setModelConfig] = useState<string>();
  const guide = page.scoring_guides.some((g) => g.id === guideChoice) ? guideChoice! : (page.scoring_guides[0]?.id ?? "");
  const modelConfig = page.model_configs.some((c) => c.id === configChoice)
    ? configChoice!
    : (page.model_configs[0]?.id ?? "");
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [created, setCreated] = useState<ControlTest>();

  useEffect(() => {
    if (created) createdRef.current?.focus();
  }, [created]);

  function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (action.isPending) return;
    setCreated(undefined);
    action.reset();
    const value = nameRef.current?.value ?? "";
    const nameError = controlTestNameError(value);
    setErrors(nameError ? { name: nameError } : {});
    if (nameError) {
      nameRef.current?.focus();
      return;
    }
    action.mutate(
      { name: cleanName(value), scoring_guide_id: guide, model_config_id: modelConfig },
      {
        onSuccess: (made) => {
          if (nameRef.current) nameRef.current.value = "";
          setCreated(made);
        },
        onError: (failure) => {
          const fields = controlTestFieldErrors(failure);
          setErrors(fields);
          if (fields.name) nameRef.current?.focus();
        },
      },
    );
  }

  const fieldErrors = Object.keys(errors).length > 0;
  const general = action.isError && !fieldErrors ? copy.create.failed : undefined;
  if (page.model_configs.length === 0 || page.scoring_guides.length === 0) {
    return <p className="max-w-md text-body-phone text-ink lg:text-body">{copy.create.noChoices}</p>;
  }

  return (
    <form method="post" noValidate onSubmit={onSubmit} className="flex max-w-xl flex-col gap-6">
      <TextField
        ref={nameRef}
        id="control-test-name"
        name="name"
        autoComplete="off"
        label={copy.create.name}
        className="max-w-md"
        error={errors.name}
        onChange={() => setCreated(undefined)}
      />
      <div>
        <SegmentedChoice
          name="scoring_guide"
          legend={copy.create.guide}
          value={guide}
          onChange={setGuide}
          options={page.scoring_guides.map((g) => ({ value: g.id, label: copy.guide(g.version, g.edited, g.draft) }))}
        />
        {errors.scoring_guide_id ? (
          <p role="alert" className="mt-2 text-body-phone text-restordre lg:text-body">
            {errors.scoring_guide_id}
          </p>
        ) : null}
      </div>
      <div>
        <SegmentedChoice
          name="model_config"
          legend={copy.create.config}
          value={modelConfig}
          onChange={setModelConfig}
          options={page.model_configs.map((c) => ({ value: c.id, label: copy.config(c.name, c.model_version, c.default) }))}
        />
        {errors.model_config_id ? (
          <p role="alert" className="mt-2 text-body-phone text-restordre lg:text-body">
            {errors.model_config_id}
          </p>
        ) : null}
      </div>
      <p className="max-w-md text-body-phone text-ink lg:text-body">{copy.create.pinned}</p>
      <ActionError message={errors.general ?? general} />
      <Button type="submit" variant="primary" unavailable={action.isPending} className="w-full max-w-md">
        {copy.create.submit}
      </Button>
      {created ? (
        <p
          ref={createdRef}
          tabIndex={-1}
          role="status"
          className="max-w-md border-y border-ink-muted py-2 text-body-phone text-ink lg:text-body"
        >
          {copy.create.created(created.name)}
        </p>
      ) : null}
    </form>
  );
}
