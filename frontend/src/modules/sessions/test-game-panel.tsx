"use client";

import { useQueryClient } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { useId, useState } from "react";

import { ActionError } from "@/components/action-error";
import { Button } from "@/components/button";
import { Link } from "@/components/link";
import { SegmentedChoice } from "@/components/segmented-choice";
import { nb } from "@/copy/nb";
import { useAction } from "@/lib/api/mutation";
import { gamePath } from "@/modules/identity/homes";

import { type ClassSession, classSessionKey, startTestGame } from "./api";
import { roleName } from "./sessions";

const copy = nb.sessions.testGame;
const LINE = "text-body-phone text-ink lg:text-body";

type Role = ClassSession["game_settings"]["roles"][number];

/**
 * «Testspill» on the Klasseøkt (Story 6.20, FR-87, cut list behind `FEATURE_LECTURER_TEST_GAME`):
 * the owner plays the stored Game settings against three AI players before the Start date. The
 * Role is chosen with Valgknapper (the chain's first Role by default) and «Start testspill», a
 * secondary button beside «Lagre Klasseøkt», starts the game and opens its play route. An
 * unfinished test Game is continued from here instead; a finished one stays one Lenke away.
 * Nothing renders while the flag is off or for a User who may not manage the session.
 */
export function TestGameBlock({ item }: { item: ClassSession }) {
  const router = useRouter();
  const queryClient = useQueryClient();
  const titleId = useId();
  const roles = item.game_settings.roles;
  const [chosen, setRole] = useState<Role>(roles[0]!);
  // Settings saved meanwhile may have dropped the chosen Role: the first one stands then.
  const role = roles.includes(chosen) ? chosen : roles[0]!;
  const start = useAction({
    mutationFn: () => startTestGame(item.id, role),
    messages: copy.refused,
    onSuccess: (started) => {
      // Back on the Klasseøkt, the block reads where the test Game stands now, not 30 s ago.
      void queryClient.invalidateQueries({ queryKey: classSessionKey(item.id), exact: true });
      router.push(gamePath(started.id));
    },
  });
  if (!item.lecturer_test_enabled || !item.can_manage) return null;
  const game = item.test_game;
  const running = game != null && game.status !== "finished";
  return (
    <section aria-labelledby={titleId} className="mt-12 border-t border-hairline pt-8" data-test-game="">
      <h2 id={titleId} className="text-headline text-ink">
        {copy.title}
      </h2>
      {running ? (
        <div className="mt-3 flex flex-col items-start gap-1">
          <p className={LINE}>{copy.running}</p>
          <Link href={gamePath(game.id)} standalone>
            {copy.resume}
          </Link>
        </div>
      ) : item.locked ? (
        <p className={`${LINE} mt-3`}>{copy.closed}</p>
      ) : (
        <>
          <p className={`${LINE} mt-3 max-w-2xl`}>{copy.lead}</p>
          <SegmentedChoice
            name={`${titleId}-role`}
            legend={copy.role}
            options={roles.map((value) => ({ value, label: roleName(value) }))}
            value={role}
            onChange={setRole}
            // As the Klasseøkt's other Valgknapper: as wide as the labels on a wide screen.
            className="mt-5 lg:[&_label]:flex-none"
          />
          <div className="mt-5 flex flex-col items-start gap-2">
            <Button
              variant="secondary"
              unavailable={start.isPending || start.isSuccess}
              onClick={() => {
                if (!start.isPending && !start.isSuccess) start.mutate();
              }}
            >
              {start.isPending || start.isSuccess ? copy.starting : copy.start}
            </Button>
            <ActionError message={start.errorMessage} />
          </div>
        </>
      )}
      {game != null && !running ? (
        <Link href={gamePath(game.id)} standalone className="mt-2">
          {copy.previous}
        </Link>
      ) : null}
    </section>
  );
}
