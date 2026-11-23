import { type Browser, type BrowserContext, expect, type Page } from "@playwright/test";

import { nextMail } from "./auth";
import { freshClass, lecturerPage, type Session, test } from "./classes";

/** A real, started Class game on the local stack (Story 6.15), for the specs that measure live
 * play end to end. Everything is fresh: a Class of the worker's fresh Lecturer, Students made from
 * mailed Invitations (never the demo Students), a Class session with no Veiledede uker, locked at
 * once through the local dev lock (`POST /api/dev/class-sessions/{id}/lock`, the stand-in for the
 * early lock of Epic 8), each Student's Starting task done through the api, and the game started. */
const CSRF = { "X-Requested-With": "olspillet" };
const DAY = 24 * 60 * 60 * 1000;
const PASSWORD = "spill-passord-1";

export type LiveStudent = { email: string; name: string; context: BrowserContext };
export type LiveGame = { gameId: string; sessionId: string; students: LiveStudent[] };
/** With `start: false` (Story 8.10): the locked Class session's games, not started, by game number. */
export type LockedGames = { gameIds: string[]; sessionId: string; students: LiveStudent[] };

/** `count` fresh Students in a fresh Class of `lecturerSession`, logged in each in a context of
 * its own at `width`; the rest of the game's Seats are AI players of the session's AI mode. */
export async function liveClassGame(
  browser: Browser,
  lecturerSession: Session,
  count: number,
  {
    aiMode = "llm",
    width = 360,
    gameSettings = {},
    debriefMode,
    obligatory,
  }: {
    aiMode?: "llm" | "rule_based";
    /** The Class session's Debrief mode; left out, the session's default (Story 9.14). */
    debriefMode?: "group" | "personal";
    /** Story 13.1: mark the Class session Obligatorisk. */
    obligatory?: boolean;
    width?: number;
    /** More Game settings for the Class session, over `guided_weeks: 0` (Story 6.18: a short game). */
    gameSettings?: Record<string, unknown>;
  } = {},
): Promise<LiveGame> {
  const locked = await lockedClassGames(browser, lecturerSession, count, {
    aiMode,
    width,
    gameSettings,
    debriefMode,
    obligatory,
  });
  const { sessionId, students } = locked;
  // Each Student's Starting task, the Students side by side (each answers its own Seat's items).
  const gameIds = new Set<string>();
  await Promise.all(
    students.map(async (student) => {
      const sessions = await (await student.context.request.get("/api/me/class-sessions")).json();
      const item = (sessions.items as { id: string; game: { id: string } | null }[]).find((s) => s.id === sessionId)!;
      const gameId = item.game!.id;
      gameIds.add(gameId);
      const task = await (await student.context.request.get(`/api/me/games/${gameId}/starting-task`)).json();
      for (const each of task.items as { id: string }[]) {
        const answered = await student.context.request.post(`/api/me/games/${gameId}/starting-task/answers`, {
          data: { item_id: each.id, answer: 0 },
          headers: CSRF,
        });
        expect(answered.status()).toBe(200);
      }
      const done = await student.context.request.post(`/api/me/games/${gameId}/starting-task/final`, {
        data: { choice: "skipped" },
        headers: CSRF,
      });
      expect(done.status()).toBe(200);
    }),
  );
  expect(gameIds.size, "every Student holds a Seat in the one Class game").toBe(1);
  const [gameId] = [...gameIds] as [string];
  const started = await students[0]!.context.request.post(`/api/me/games/${gameId}/start`, { headers: CSRF });
  expect(started.status()).toBe(200);
  return { gameId, sessionId, students };
}

/** As `liveClassGame`, up to the lock (Story 8.10): the Class session's games have their snapshot
 * and none has started; `count` Students fill as many games as the allocation draws. */
export async function lockedClassGames(
  browser: Browser,
  lecturerSession: Session,
  count: number,
  {
    aiMode = "llm",
    width = 360,
    gameSettings = {},
    debriefMode,
    obligatory,
  }: {
    aiMode?: "llm" | "rule_based";
    width?: number;
    gameSettings?: Record<string, unknown>;
    debriefMode?: "group" | "personal";
    obligatory?: boolean;
  } = {},
): Promise<LockedGames> {
  const lecturer = await lecturerPage(browser, lecturerSession, { width: 1280, height: 800 });
  try {
    const klass = await freshClass(lecturer);
    const tag = `${Date.now()}${Math.floor(Math.random() * 1e6)}`;
    const emails = Array.from({ length: count }, (_, i) => `spill-${tag}-${i}@stud.example.no`);
    const staged = await lecturer.request.post(`/api/classes/${klass.id}/roster-paste`, {
      data: { text: emails.join("\n") },
      headers: CSRF,
    });
    expect(staged.status()).toBe(201);
    const sent = await lecturer.request.post(`/api/classes/${klass.id}/invitations`, {
      data: { upload_id: (await staged.json()).id, valid_days: 14 },
      headers: CSRF,
    });
    expect(sent.status()).toBe(201);
    const students = await Promise.all(
      emails.map(async (email, i) => {
        const mail = await nextMail(lecturer, email, null);
        const token = mail.text.match(/\/invitasjon#([A-Za-z0-9_-]+)/)![1];
        const context = await browser.newContext({
          baseURL: test.info().project.use.baseURL,
          viewport: { width, height: 800 },
        });
        const name = `Spiller${i} ${tag.slice(-4)}`;
        const accepted = await context.request.post("/api/auth/invitation/accept", {
          data: { token, name, password: PASSWORD },
          headers: CSRF,
        });
        expect(accepted.status()).toBe(200);
        return { email, name, context };
      }),
    );

    const created = await lecturer.request.post(`/api/classes/${klass.id}/class-sessions`, { headers: CSRF });
    expect(created.status()).toBe(201);
    const sessionId = (await created.json()).id as string;
    const [start_at, play_deadline, debrief_deadline, test_deadline] = [3, 17, 20, 27].map((d) =>
      new Date(Date.now() + d * DAY).toISOString(),
    );
    const saved = await lecturer.request.put(`/api/class-sessions/${sessionId}`, {
      data: {
        ai_mode: aiMode,
        ...(debriefMode ? { debrief_mode: debriefMode } : {}),
        ...(obligatory ? { obligatory: true } : {}),
        dates: { start_at, play_deadline, debrief_deadline, test_deadline },
        game_settings: { guided_weeks: 0, ...gameSettings },
      },
      headers: CSRF,
    });
    expect(saved.status()).toBe(200);
    const drawn = await (await lecturer.request.post(`/api/class-sessions/${sessionId}/allocation`, { headers: CSRF })).json();
    const confirmed = await lecturer.request.post(`/api/class-sessions/${sessionId}/allocation/confirm`, {
      data: { draft_id: drawn.draft.id, revision: drawn.draft.revision },
      headers: CSRF,
    });
    expect(confirmed.ok()).toBe(true);
    const locked = await lecturer.request.post(`/api/dev/class-sessions/${sessionId}/lock`, { headers: CSRF });
    expect(locked.status()).toBe(200);
    const games = await (
      await lecturer.request.get(`/api/class-sessions/${sessionId}/start-games`, { headers: CSRF })
    ).json();
    return { gameIds: (games.games as { game_id: string }[]).map((g) => g.game_id), sessionId, students };
  } finally {
    await lecturer.context().close();
  }
}

/** Place the Student's Order for `week` through the api, as «Bekreft ordre» does. */
export async function orderByApi(student: LiveStudent, gameId: string, week: number, order: number) {
  const answer = await student.context.request.post(`/api/me/games/${gameId}/weeks/${week}/order`, {
    data: { order },
    headers: CSRF,
  });
  expect(answer.status()).toBe(204);
}

/**
 * Records on the page, in `Date.now()` ms (one clock for every page of the browser and the test):
 * when the heading first reads `Uke {week}` (`window.__weekShown`), each SSE change event
 * (`window.__events`), and each answer of the play envelope (`window.__playRead`). Installed before
 * the page loads.
 */
export async function instrument(page: Page, week: number) {
  await page.addInitScript((target: number) => {
    const w = window as unknown as Record<string, unknown>;
    w.__events = [] as number[];
    w.__playRead = [] as number[];
    const Native = window.EventSource;
    window.EventSource = class extends Native {
      constructor(url: string | URL, init?: EventSourceInit) {
        super(url, init);
        this.addEventListener("message", () => (w.__events as number[]).push(Date.now()));
      }
    } as typeof EventSource;
    const fetchNative = window.fetch.bind(window);
    window.fetch = async (...args: Parameters<typeof fetch>) => {
      const response = await fetchNative(...args);
      const url = String(args[0] instanceof Request ? args[0].url : args[0]);
      if (url.endsWith("/play")) (w.__playRead as number[]).push(Date.now());
      return response;
    };
    const seen = () => {
      const heading = document.getElementById("play-week");
      if (heading && heading.textContent === `Uke ${target}` && w.__weekShown === undefined) w.__weekShown = Date.now();
    };
    new MutationObserver(seen).observe(document, { subtree: true, childList: true, characterData: true });
  }, week);
}

export type Timing = { shown: number; events: number[]; playRead: number[] };

export async function timing(page: Page): Promise<Timing> {
  return page.evaluate(() => {
    const w = window as unknown as Record<string, unknown>;
    return { shown: w.__weekShown as number, events: w.__events as number[], playRead: w.__playRead as number[] };
  });
}
