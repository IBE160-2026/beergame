import { Link } from "@/components/link";
import { nb } from "@/copy/nb";
import { allGamesPath } from "@/modules/identity/homes";

const copy = nb.allGames;

/**
 * Hjem's entry for «Alle spill side om side» (Story 14.5, FR-86, UX-DR64), under Stegene: a Lenke
 * once the api says it is open (`all_games_open`: the Student's Debrief is done and the Play
 * deadline has passed), else its name and «Åpnes når Debriefen din er ferdig og Spillfristen er
 * passert.» in `ink-secondary`, no link. The api decides; this only words it.
 */
export function AllGamesEntry({ sessionId, open }: { sessionId: string; open: boolean }) {
  if (open) {
    return (
      <p className="mt-3" data-all-games-entry="open">
        <Link href={allGamesPath(sessionId)} standalone>
          {copy.entry}
        </Link>
      </p>
    );
  }
  return (
    <p className="mt-3 flex flex-col text-body-phone text-ink-secondary lg:text-body" data-all-games-entry="locked">
      <span className="font-semibold">{copy.entry}</span>
      <span>{copy.locked}</span>
    </p>
  );
}
