# Visual check, Story 9.12 (f93c388), Debrief /debrief/{classSessionId}

Each shot exists at -390 and -1280 (full page). No horizontal overflow in any shot (scrollWidth == clientWidth).

- group-bar-opener-step1: opener on step 1, «Gå videre for alle» + «Forlat gruppen», both outlined; matches (no filled primary since Send is disabled).
- join-panel-before-join: «Bli med i Gruppedebriefen» (filled primary) + «Ta en Personlig debrief» (outlined) with lead; matches.
- group-bar-member-step1: non-opener in group, «Forlat gruppen» only; matches.
- leave-confirm-focus-avbryt (390, 1280, 390-text200): confirmation inline, focus on «Avbryt»; matches. 200 % text: nothing cut off, no sideways scroll.
- alone-line-left (390, 1280, 390-text200): alone line under step 1 after leaving; matches.
- group-bar-opener-gone-step1: Ida becomes opener after Sara left; shows «Gå videre for alle» + «Forlat gruppen»; matches.
- alone-line-dropout: dropout line; matches copy.
- group-bar-opener-step2: step 2 with «Ferdig med steget», «Gå videre for alle», «Forlat gruppen»: all three outlined, NO filled primary; chart demand label clipped ("ørsel: 8"), chart squeezed to the right edge; DEVIATION.
- group-bar-too-early-step2: too-early shown twice (caption «Du kan flytte gruppen videre fra kl. 21:02…» and red alert «Gruppen kan gå videre fra kl. 21:02.»); DEVIATION.
- group-bar-step3-or-after: group after steps done (see shot).
- alone-line-missed: missed line; matches copy.
- alone-line-fallback: 48-hour fallback line; matches copy.
