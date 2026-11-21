"use client";

import { useEffect, useRef } from "react";

import { nb } from "@/copy/nb";
import { ApiRequestError } from "@/lib/api/client";
import { usePageState } from "@/lib/page-state";
import type { SessionUser } from "@/modules/identity/api";
import { AccessDenied, GuardedPage } from "@/modules/identity/home-page";
import { HOME_LINK, HOME_PATH } from "@/modules/identity/homes";
import { PageLink, PageShell } from "@/modules/identity/page-shell";
import { roleName } from "@/modules/sessions/sessions";

import {
  DEBRIEF_STEPS,
  type Debrief,
  debriefView,
  INDIVIDUAL_STEP,
  myDebriefKey,
  reach,
  reflectionDone,
  useMyDebrief,
  useMyExplanation,
  useMyReflection,
} from "./api";
import { BillStep } from "./bill-step";
import { ChainStep } from "./chain-step";
import { ExplanationStep } from "./explanation-step";
import { GroupAnnouncer, GroupJoin, GroupStepBar, STEP_HEADING_ID } from "./group";
import { MomentsStep } from "./moments-step";
import { QuizStep } from "./quiz-step";
import { ReflectionStep } from "./reflection-step";
import { RevealStep } from "./reveal-step";

const copy = nb.debriefEntry;
const LINE = "text-body-phone lg:text-body";

/**
 * The Debrief (Story 9.2, FR-42, `07-debrief.png`): reached by «Gå til Debrief» on «Spillet er
 * ferdig» and by Stegene's Debrief step. Opening the page opens the Student's Debrief session, so
 * it lands on the step the session stands at, step 1 «Skriv Forklaringen først» the first time,
 * where the Student writes their Explanation (Story 9.3). Once it is saved, step 2, the reveal of
 * customer demand, follows under it (Story 9.4); later steps come with their stories. Before the
 * game has finished the page says the
 * Debrief opens then; while the Faglærer holds every Debrief, that it opens when all Class games
 * have finished, never how many remain. Another Student's or an unknown session shows the
 * permission-denied page. Every number and state comes from the api (AD-10).
 */
export function DebriefPage({ classSessionId }: { classSessionId: string }) {
  return (
    <GuardedPage page="home">
      {(user, updatedAt) => <DebriefView classSessionId={classSessionId} user={user} updatedAt={updatedAt} />}
    </GuardedPage>
  );
}

function DebriefView({
  classSessionId,
  user,
  updatedAt,
}: {
  classSessionId: string;
  user: SessionUser;
  updatedAt: number;
}) {
  const found = useMyDebrief(classSessionId);
  const { phase, retry } = usePageState(found, myDebriefKey(classSessionId));
  const code = found.error instanceof ApiRequestError ? found.error.code : null;
  const view = debriefView(found.data, code);
  if (view === "denied") return <AccessDenied user={user} updatedAt={updatedAt} />;
  if (view === "notOpen" || view === "held") {
    return (
      <PageShell user={user} title={copy.locked} updatedAt={updatedAt}>
        <p data-debrief-locked={view} className={`${LINE} mt-4 max-w-md text-ink`}>
          {view === "held" ? copy.held : copy.notOpen}
        </p>
        <PageLink href={HOME_PATH.home}>{HOME_LINK.home}</PageLink>
      </PageShell>
    );
  }
  const debrief = found.data;
  return (
    <PageShell
      user={user}
      title={debrief ? copy.title(debrief.game_number) : copy.locked}
      updatedAt={updatedAt}
      phase={debrief ? "ready" : phase === "ready" ? "loading" : phase}
      onRetry={retry}
    >
      {debrief ? <Steps debrief={debrief} userId={user.id} /> : null}
    </PageShell>
  );
}

/** The Student's Role under the title, then the steps as `07-debrief.png` numbers them («1 Skriv
 * Forklaringen først»): step 1, and once the Explanation is saved, steps 2 and 3 under it, so the
 * Explanation stays beside the data, then the reflection questions (Story 9.6) and, once they are
 * all answered, the own moments (Story 9.7), then Kjedens regning and «Fullfør Debriefen» (Story
 * 9.8), and once finished, step 5, the Debrief quiz (Story 9.9). A finished Debrief reads the same,
 * with nothing left to send.
 *
 * Story 9.11, the Group debrief: a Student of the game who has not joined sees only «Bli med i
 * Gruppedebriefen». A joined Student sees the steps up to the shared pointer (`reach`), with the
 * group's line under the step it is on, and from the reflection questions on works alone; the
 * pointer moves with the `debrief:<id>` event, without reload, and the move is announced. */
function Steps({ debrief, userId }: { debrief: Debrief; userId: string }) {
  const group = debrief.group ?? null;
  const explanation = useMyExplanation(debrief.id);
  const sent = Boolean(explanation.data?.explanation);
  const far = reach(debrief, sent);
  const reflected = reflectionDone(useMyReflection(debrief.id, sent && far >= INDIVIDUAL_STEP).data);
  // Joined just now (Story 9.11): the join panel gave way to the steps, so focus moves to step 1.
  const wasJoined = useRef(group?.joined ?? true);
  useEffect(() => {
    const joined = group?.joined ?? true;
    if (joined && !wasJoined.current) document.getElementById(STEP_HEADING_ID)?.focus();
    wasJoined.current = joined;
  }, [group?.joined]);
  const bar = (step: number) =>
    group && group.joined && explanation.isSuccess && Math.min(group.step, sent ? group.step : 1) === step ? (
      <GroupStepBar debrief={debrief} group={group} sent={sent} />
    ) : null;
  return (
    <>
      <p className={`${LINE} mt-1 text-ink-secondary`}>{copy.roleGame(roleName(debrief.role), debrief.game_number)}</p>
      <PageLink href={HOME_PATH.home}>{HOME_LINK.home}</PageLink>
      {group ? <GroupAnnouncer group={group} /> : null}
      {far === 0 ? (
        <GroupJoin debrief={debrief} />
      ) : (
        <>
          <section aria-labelledby={STEP_HEADING_ID} data-debrief-step={1} className="mt-8 max-w-md border-t border-axis pt-4">
            <h2 id={STEP_HEADING_ID} tabIndex={-1} className="text-headline text-ink focus:outline-none">
              <span className="sr-only">{copy.stepOf(1, DEBRIEF_STEPS)}: </span>
              <span aria-hidden="true" className="mr-3 tabular-nums">
                1
              </span>
              {copy.firstStep}
            </h2>
            <ExplanationStep debrief={debrief} userId={userId} />
          </section>
          {bar(1)}
          {sent && far >= 2 ? <RevealStep debrief={debrief} /> : null}
          {bar(2)}
          {sent && far >= 3 ? <ChainStep debrief={debrief} /> : null}
          {bar(3)}
          {sent && far >= INDIVIDUAL_STEP ? <ReflectionStep debrief={debrief} userId={userId} /> : null}
          {sent && far >= INDIVIDUAL_STEP && reflected ? <MomentsStep debrief={debrief} /> : null}
          {sent && far >= INDIVIDUAL_STEP && reflected ? <BillStep debrief={debrief} /> : null}
          {sent && far >= INDIVIDUAL_STEP && reflected ? <QuizStep debrief={debrief} /> : null}
        </>
      )}
    </>
  );
}
