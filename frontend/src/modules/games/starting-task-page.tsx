"use client";

import { useQueryClient } from "@tanstack/react-query";
import NextLink from "next/link";
import { type ReactNode, useEffect, useRef, useState } from "react";

import { ActionError } from "@/components/action-error";
import { Button, buttonClassName } from "@/components/button";
import { ColumnItem } from "@/components/column-item";
import { SegmentedChoice } from "@/components/segmented-choice";
import { nb } from "@/copy/nb";
import { ApiRequestError } from "@/lib/api/client";
import { useAction } from "@/lib/api/mutation";
import { formatNumber } from "@/lib/number-format";
import { usePageState } from "@/lib/page-state";
import type { SessionUser } from "@/modules/identity/api";
import { AccessDenied, GuardedPage } from "@/modules/identity/home-page";
import { HOME_LINK, HOME_PATH } from "@/modules/identity/homes";
import { PageLink, PageShell } from "@/modules/identity/page-shell";
import { enrolledSessionsKey } from "@/modules/sessions/api";

import { answerItem, finishTask, myGameKey, startingTaskKey, useStartingTask } from "./api";
import {
  type FinalChoice,
  firstOpen,
  parseWholeNumber,
  resultLine,
  type StartingTask,
  type StartingTaskItem,
} from "./starting-task";

const copy = nb.games.startingTask;
const BODY = "text-body-phone text-ink lg:text-body";

/**
 * The Startoppgave (Story 6.3, FR-85, UX-DR63, UX-DR70, mockup `09-alle-sider`): short sums on one
 * column of the week table, labelled «Demodata», each answered by a whole number. The api scores
 * each answer once (computed rules) and the line under the column says right or wrong in words with
 * the sum; the Student goes on either way. After the last item the optional question «Har du spilt
 * et spill som ligner dette før?», then «Ferdig. Gå til Uke 1.». It resumes at the first item
 * without an answer, on any device. Another Student's game shows the permission-denied page.
 */
export function StartingTaskPage({ gameId }: { gameId: string }) {
  return (
    <GuardedPage page="home">
      {(user, updatedAt) => <StartingTaskView gameId={gameId} user={user} updatedAt={updatedAt} />}
    </GuardedPage>
  );
}

function StartingTaskView({ gameId, user, updatedAt }: { gameId: string; user: SessionUser; updatedAt: number }) {
  const found = useStartingTask(gameId);
  const { phase, retry } = usePageState(found, startingTaskKey(gameId));
  if (found.error instanceof ApiRequestError && found.error.code === "forbidden") {
    return <AccessDenied user={user} updatedAt={updatedAt} />;
  }
  const task = found.data;
  return (
    <PageShell
      user={user}
      title={copy.title}
      updatedAt={updatedAt}
      phase={task ? "ready" : phase === "ready" ? "loading" : phase}
      onRetry={retry}
    >
      <PageLink href={HOME_PATH.home}>{HOME_LINK.home}</PageLink>
      {task ? <Task gameId={gameId} task={task} /> : null}
    </PageShell>
  );
}

function Task({ gameId, task }: { gameId: string; task: StartingTask }) {
  const queryClient = useQueryClient();
  const open = firstOpen(task);
  // The item whose result line takes focus once its answer is stored.
  const [focusResult, setFocusResult] = useState<string | null>(null);
  const [focusDone, setFocusDone] = useState(false);
  const store = (next: StartingTask) => {
    queryClient.setQueryData(startingTaskKey(gameId), next);
    // `briefing_first` changes once the task is done: Hjem and the game read again.
    if (next.done) {
      void queryClient.invalidateQueries({ queryKey: myGameKey(gameId) });
      void queryClient.invalidateQueries({ queryKey: enrolledSessionsKey });
    }
  };
  const shown = open === -1 ? task.items : task.items.slice(0, open + 1);
  return (
    <div className="mt-4 max-w-prose">
      <p className={BODY}>{copy.lead}</p>
      <ol className="m-0 list-none p-0">
        {shown.map((item, index) => (
          <li key={item.id} className="mt-8">
            <h2 className="text-headline text-ink">{copy.progress(index + 1, task.items.length)}</h2>
            <p className={`${BODY} mt-2`}>{item.prompt}</p>
            {item.result ? (
              <AnsweredItem item={item} focus={focusResult === item.id} />
            ) : (
              <OpenItem
                gameId={gameId}
                item={item}
                onStored={(next) => {
                  setFocusResult(item.id);
                  store(next);
                }}
              />
            )}
          </li>
        ))}
      </ol>
      {open === -1 && !task.done ? (
        <FinalQuestion
          gameId={gameId}
          onStored={(next) => {
            setFocusDone(true);
            store(next);
          }}
        />
      ) : null}
      {task.done ? <Done focus={focusDone} /> : null}
    </div>
  );
}

/** An item's column, labelled «Demodata» under it (UX-DR70). */
function Demo({ children }: { children: ReactNode }) {
  return (
    <figure className="m-0 mt-4 max-w-xs">
      {children}
      <figcaption className="mt-2 text-right text-caption text-ink-muted">{copy.demoData}</figcaption>
    </figure>
  );
}

function AnsweredItem({ item, focus }: { item: StartingTaskItem; focus: boolean }) {
  const resultRef = useRef<HTMLParagraphElement>(null);
  useEffect(() => {
    if (focus) resultRef.current?.focus();
  }, [focus]);
  const result = item.result!;
  return (
    <Demo>
      <ColumnItem
        id={`item-${item.id}`}
        caption={item.column}
        rows={item.rows}
        askedLabel={item.asked_label}
        hint={item.hint}
        answer={formatNumber(result.answer)}
        result={resultLine(result)}
        resultRef={resultRef}
      />
    </Demo>
  );
}

function OpenItem({
  gameId,
  item,
  onStored,
}: {
  gameId: string;
  item: StartingTaskItem;
  onStored: (next: StartingTask) => void;
}) {
  const [text, setText] = useState("");
  const [error, setError] = useState<string | undefined>(undefined);
  const inputRef = useRef<HTMLInputElement>(null);
  const sending = useAction({
    mutationFn: (answer: number) => answerItem(gameId, item.id, answer),
    onSuccess: onStored,
  });
  const check = () => {
    const parsed = parseWholeNumber(text);
    setError(parsed === null ? copy.notWhole : undefined);
    return parsed;
  };
  const send = () => {
    if (sending.isPending) return;
    const parsed = check();
    if (parsed === null) {
      inputRef.current?.focus();
      return;
    }
    sending.mutate(parsed);
  };
  return (
    <div className="flex flex-col gap-4">
      <Demo>
        <ColumnItem
          id={`item-${item.id}`}
          caption={item.column}
          rows={item.rows}
          askedLabel={item.asked_label}
          hint={item.hint}
          value={text}
          onChange={(next) => {
            setText(next);
            if (error && parseWholeNumber(next) !== null) setError(undefined);
          }}
          onBlur={check}
          onEnter={send}
          error={error}
          inputRef={inputRef}
        />
      </Demo>
      <div className="flex flex-col items-start gap-2">
        <Button variant="primary" unavailable={sending.isPending} onClick={send}>
          {copy.send}
        </Button>
        <ActionError message={sending.errorMessage} />
      </div>
    </div>
  );
}

type Picked = FinalChoice | "";

function FinalQuestion({ gameId, onStored }: { gameId: string; onStored: (next: StartingTask) => void }) {
  const [picked, setPicked] = useState<Picked>("");
  const [error, setError] = useState<string | undefined>(undefined);
  const sending = useAction({
    mutationFn: (choice: FinalChoice) => finishTask(gameId, choice),
    onSuccess: onStored,
  });
  const final = copy.final;
  const options = (["yes", "no", "unknown"] as const).map((value) => ({
    value,
    label: final.choices[value],
  }));
  const send = (choice: Picked) => {
    if (sending.isPending) return;
    if (choice === "") {
      setError(final.none);
      return;
    }
    setError(undefined);
    sending.mutate(choice);
  };
  return (
    <section className="mt-10">
      <SegmentedChoice<Picked>
        name="played-before"
        legend={final.question}
        options={options}
        value={picked}
        onChange={(value) => {
          setPicked(value);
          setError(undefined);
        }}
        describedBy="final-optional"
        className="max-w-xs"
      />
      <p id="final-optional" className="mt-2 text-body-phone text-ink-secondary">
        {final.optional}
      </p>
      {error ? (
        <p role="alert" className="mt-2 text-body-phone text-restordre">
          {error}
        </p>
      ) : null}
      <div className="mt-6 flex flex-wrap gap-3">
        <Button variant="primary" unavailable={sending.isPending} onClick={() => send(picked)}>
          {copy.send}
        </Button>
        <Button unavailable={sending.isPending} onClick={() => send("skipped")}>
          {final.skip}
        </Button>
      </div>
      <ActionError message={sending.errorMessage} className="mt-2" />
    </section>
  );
}

function Done({ focus }: { focus: boolean }) {
  const ref = useRef<HTMLParagraphElement>(null);
  useEffect(() => {
    if (focus) ref.current?.focus();
  }, [focus]);
  return (
    <section className="mt-10">
      <p ref={ref} tabIndex={-1} className="text-headline text-ink">
        {copy.done}
      </p>
      <p className={`${BODY} mt-2`}>{copy.startsFromHome}</p>
      <div className="mt-6">
        <NextLink href={HOME_PATH.home} className={buttonClassName("primary")}>
          {copy.toHome}
        </NextLink>
      </div>
    </section>
  );
}
