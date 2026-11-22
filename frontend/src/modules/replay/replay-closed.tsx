import { nb } from "@/copy/nb";
import { HOME_LINK, HOME_PATH } from "@/modules/identity/homes";
import { PageLink } from "@/modules/identity/page-shell";

const copy = nb.games.play.replayClosed;
const LINE = "text-body-phone text-ink lg:text-body";

/**
 * A Replay closed at the Testfrist without its last Uke (Story 10.6, FR-18), under
 * `GameEndHeading` («Replay stengt» over «Grossist, Replay»): it is not finished, so no Totalkostnad,
 * no walkthrough and no button forward; the lines say why and that the Orders stand, and «Til Hjem»
 * leads back, where Stegene says the same. Every state is the api's (`end_reason`, AD-10).
 */
export function ReplayClosed() {
  return (
    <div data-replay-closed="" className="mt-6 max-w-md">
      <p className={LINE}>{copy.lead}</p>
      <p className={`${LINE} mt-3`}>{copy.kept}</p>
      <PageLink href={HOME_PATH.home}>{HOME_LINK.home}</PageLink>
    </div>
  );
}
