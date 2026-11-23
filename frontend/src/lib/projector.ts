/**
 * Display mode on a projector or a large screen («Delt skjerm», Story 9.13; «Vis i plenum», Story
 * 14.6): the root text grows with the window from 1280 px (1.25 vw, 24 px at 1920 px, at most
 * 150 %), so the whole page reads from the back of the room. `max(100%, …)` keeps a larger text
 * size the User has chosen (200 % text stays 200 %). Rendered in a `<style>` by the page.
 */
export const PROJECTOR_SCALE = "html{font-size:max(100%,min(1.25vw,150%))}";
