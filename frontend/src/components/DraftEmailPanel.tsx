import { type FormEvent, useState } from "react";

import { postDraftEmail } from "../api/endpoints";
import type { Programme } from "../config/programmes";
import { useApiCall } from "../hooks/useApiCall";
import { Button } from "../ui/Button";
import { Card } from "../ui/Card";
import { ErrorBanner } from "../ui/ErrorBanner";
import { Field } from "../ui/Field";
import { Spinner } from "../ui/Spinner";
import { controlClass } from "../ui/styles";
import { CitationsPanel } from "./CitationsPanel";
import { DisclaimerBar } from "./DisclaimerBar";
import { RefusalNotice } from "./RefusalNotice";

export function DraftEmailPanel({ programme }: { programme: Programme }) {
  const { data, loading, error, run } = useApiCall(postDraftEmail);
  const [topic, setTopic] = useState("");
  const [copied, setCopied] = useState(false);

  const canSubmit = topic.trim().length > 0 && !loading;

  function onSubmit(event: FormEvent): void {
    event.preventDefault();
    setCopied(false);
    void run({
      university_slug: programme.university_slug,
      programme_slug: programme.programme_slug,
      topic: topic.trim(),
    });
  }

  function onCopy(): void {
    if (!data) {
      return;
    }
    void navigator.clipboard
      ?.writeText(`Subject: ${data.subject}\n\n${data.body}`)
      .then(() => setCopied(true));
  }

  const hasDraft = data && !data.insufficient_context && data.body.trim().length > 0;

  return (
    <div className="space-y-4">
      <form onSubmit={onSubmit} className="space-y-3">
        <Field
          label="Email topic"
          htmlFor="email-topic"
          hint="What should the email to the admissions office ask or state?"
        >
          <input
            id="email-topic"
            type="text"
            value={topic}
            onChange={(event) => setTopic(event.target.value)}
            placeholder="e.g. Clarify the document submission deadline"
            className={controlClass}
          />
        </Field>
        <Button type="submit" disabled={!canSubmit}>
          {loading ? "Drafting..." : "Draft email"}
        </Button>
      </form>

      {loading ? <Spinner label="Drafting the email..." /> : null}
      {error ? <ErrorBanner message={error} /> : null}

      {data ? (
        <Card>
          {hasDraft ? (
            <section className="space-y-3">
              <div className="flex items-center justify-between">
                <h3 className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                  Draft
                </h3>
                <button
                  type="button"
                  onClick={onCopy}
                  className="text-xs font-medium text-slate-600 underline hover:text-slate-900"
                >
                  {copied ? "Copied" : "Copy"}
                </button>
              </div>
              <p className="text-sm font-medium text-slate-900">
                Subject: {data.subject}
              </p>
              <p className="whitespace-pre-wrap text-sm leading-relaxed text-slate-800">
                {data.body}
              </p>
            </section>
          ) : (
            <RefusalNotice />
          )}
          <CitationsPanel citations={data.citations} />
          <DisclaimerBar text={data.disclaimer} />
        </Card>
      ) : null}
    </div>
  );
}
