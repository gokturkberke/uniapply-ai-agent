import { type FormEvent, useState } from "react";

import { postAsk } from "../api/endpoints";
import type { Programme } from "../config/programmes";
import { useApiCall } from "../hooks/useApiCall";
import { Button } from "../ui/Button";
import { Card } from "../ui/Card";
import { ErrorBanner } from "../ui/ErrorBanner";
import { Field } from "../ui/Field";
import { Spinner } from "../ui/Spinner";
import { controlClass } from "../ui/styles";
import { AnswerPanel } from "./AnswerPanel";
import { CitationsPanel } from "./CitationsPanel";
import { DisclaimerBar } from "./DisclaimerBar";
import { RefusalNotice } from "./RefusalNotice";

export function AskPanel({ programme }: { programme: Programme }) {
  const { data, loading, error, run } = useApiCall(postAsk);
  const [question, setQuestion] = useState("");

  const canSubmit = question.trim().length > 0 && !loading;

  function onSubmit(event: FormEvent): void {
    event.preventDefault();
    void run({
      question: question.trim(),
      university_slug: programme.university_slug,
      programme_slug: programme.programme_slug,
    });
  }

  return (
    <div className="space-y-4">
      <form onSubmit={onSubmit} className="space-y-3">
        <Field
          label="Your question"
          htmlFor="ask-question"
          hint="Answers are grounded in this programme's official documents only."
        >
          <textarea
            id="ask-question"
            value={question}
            onChange={(event) => setQuestion(event.target.value)}
            rows={3}
            placeholder="e.g. What is the application deadline for this programme?"
            className={controlClass}
          />
        </Field>
        <Button type="submit" disabled={!canSubmit}>
          {loading ? "Asking..." : "Ask"}
        </Button>
      </form>

      {loading ? <Spinner label="Retrieving a grounded answer..." /> : null}
      {error ? <ErrorBanner message={error} /> : null}

      {data ? (
        <Card>
          {data.insufficient_context ? (
            <RefusalNotice message={data.answer} />
          ) : (
            <>
              <AnswerPanel answer={data.answer} confidence={data.confidence} />
              <CitationsPanel citations={data.citations} />
            </>
          )}
          <DisclaimerBar text={data.disclaimer} />
        </Card>
      ) : null}
    </div>
  );
}
