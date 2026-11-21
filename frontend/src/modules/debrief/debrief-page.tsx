"use client";

import { nb } from "@/copy/nb";
import { ApiRequestError } from "@/lib/api/client";
import { usePageState } from "@/lib/page-state";
import type { SessionUser } from "@/modules/identity/api";
import { AccessDenied, GuardedPage } from "@/modules/identity/home-page";
import { HOME_LINK, HOME_PATH } from "@/modules/identity/homes";
import { PageLink, PageShell } from "@/modules/identity/page-shell";
import { roleName } from "@/modules/sessions/sessions";

import { DEBRIEF_STEPS, type Debrief, debriefView, myDebriefKey, useMyDebrief } from "./api";
import { ExplanationStep } from "./explanation-step";

const copy = nb.debriefEntry;
const LINE = "text-body-phone lg:text-body";

/**
 * The Debrief (Story 9.2, FR-42, `07-debrief.png`): reached by «Gå til Debrief» on «Spillet er
 * ferdig» and by Stegene's Debrief step. Opening the page opens the Student's Debrief session, so
 * it lands on the step the session stands at, step 1 «Skriv Forklaringen først» the first time,
 * where the Student writes their Explanation (Story 9.3); later steps' content comes with 9.4 on. Before the game has finished the page says the
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

/** The Student's Role under the title, then the step the session stands at: its number and
 * heading, as `07-debrief.png` numbers them («1 Skriv Forklaringen først»). */
function Steps({ debrief, userId }: { debrief: Debrief; userId: string }) {
  const heading = debrief.step === 1 ? copy.firstStep : null;
  return (
    <>
      <p className={`${LINE} mt-1 text-ink-secondary`}>{copy.roleGame(roleName(debrief.role), debrief.game_number)}</p>
      <PageLink href={HOME_PATH.home}>{HOME_LINK.home}</PageLink>
      <section aria-labelledby="debrief-step" data-debrief-step={debrief.step} className="mt-8 max-w-md border-t border-axis pt-4">
        {heading ? (
          <h2 id="debrief-step" className="text-headline text-ink">
            <span className="sr-only">{copy.stepOf(debrief.step, DEBRIEF_STEPS)}: </span>
            <span aria-hidden="true" className="mr-3 tabular-nums">
              {debrief.step}
            </span>
            {heading}
          </h2>
        ) : (
          // Steps 2 to 5 get their headings with their stories; until then the step in words.
          <h2 id="debrief-step" className="text-headline text-ink">
            {copy.stepOf(debrief.step, DEBRIEF_STEPS)}
          </h2>
        )}
        {debrief.step === 1 ? <ExplanationStep debrief={debrief} userId={userId} /> : null}
      </section>
    </>
  );
}
