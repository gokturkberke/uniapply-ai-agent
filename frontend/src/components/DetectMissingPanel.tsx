import { type FormEvent, useState } from "react";

import { postDetectMissing } from "../api/endpoints";
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

function StringList({ title, items }: { title: string; items: string[] }) {
  return (
    <div>
      <h3 className="text-xs font-semibold uppercase tracking-wide text-slate-500">
        {title} ({items.length})
      </h3>
      {items.length === 0 ? (
        <p className="mt-2 text-sm text-slate-500">None.</p>
      ) : (
        <ul className="mt-2 list-disc space-y-1 pl-5 text-sm text-slate-700">
          {items.map((item, index) => (
            <li key={`${item}-${index}`}>{item}</li>
          ))}
        </ul>
      )}
    </div>
  );
}

export function DetectMissingPanel({ programme }: { programme: Programme }) {
  const { data, loading, error, run } = useApiCall(postDetectMissing);
  const [profileText, setProfileText] = useState("");

  function onSubmit(event: FormEvent): void {
    event.preventDefault();
    const profile = profileText
      .split("\n")
      .map((line) => line.trim())
      .filter((line) => line.length > 0);
    void run({
      university_slug: programme.university_slug,
      programme_slug: programme.programme_slug,
      profile,
    });
  }

  return (
    <div className="space-y-4">
      <form onSubmit={onSubmit} className="space-y-3">
        <Field
          label="What you already have"
          htmlFor="profile"
          hint="One credential or document per line (e.g. Bachelor's degree, IELTS 7.0)."
        >
          <textarea
            id="profile"
            value={profileText}
            onChange={(event) => setProfileText(event.target.value)}
            rows={4}
            placeholder={"Bachelor's degree\nIELTS 7.0"}
            className={controlClass}
          />
        </Field>
        <Button type="submit" disabled={loading}>
          {loading ? "Checking..." : "Detect missing documents"}
        </Button>
      </form>

      {loading ? <Spinner label="Comparing your profile..." /> : null}
      {error ? <ErrorBanner message={error} /> : null}

      {data ? (
        <Card>
          {data.insufficient_context ? (
            <RefusalNotice />
          ) : (
            <div className="grid gap-4 sm:grid-cols-2">
              <StringList title="Missing" items={data.missing} />
              <StringList title="Already satisfied" items={data.satisfied} />
            </div>
          )}
          <CitationsPanel citations={data.citations} />
          <DisclaimerBar text={data.disclaimer} />
        </Card>
      ) : null}
    </div>
  );
}
