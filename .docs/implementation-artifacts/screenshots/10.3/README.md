# Story 10.3 visual check (commit ae5efdf). Replay start is stubbed over the real api, as in the e2e spec. No horizontal scroll in any shot.

- hjem-390.png, hjem-1280.png: Hjem before the quiz is passed. Quiz is current, Replay says "åpnes når du har bestått Debrief-quizen", no Start Replay and no primary button. Matches.
- hjem-startreplay-390.png, hjem-startreplay-1280.png, hjem-startreplay-390-200pct.png: after the quiz. The Replay block has the consequence text and one ink primary «Start Replay». Matches nb.ts and DESIGN.md. At 200 % the text wraps and nothing is cut off.
- replay-started-390.png, replay-started-1280.png, replay-started-390-200pct.png: «Replay · Du er Grossist» with three «KI-spiller» Seats and «Demo Student (deg)», Stegene shows Replay «pågår». Matches. No button or link into the Replay (see report).
- hjem-refusal-quiz-390.png, hjem-refusal-quiz-1280.png, hjem-refusal-quiz-390-200pct.png: 409 quiz_required. Red «Bestå Debrief-quizen først.» under the button. Matches. The button is underlined (hover, per DESIGN).
- hjem-stegene-closed-390.png, hjem-stegene-closed-1280.png, hjem-stegene-closed-390-200pct.png: after the Test deadline. Stegene says «ikke gjort, Testfristen er ute», no button. Matches.
