import { postChecklist } from "../api/endpoints";
import type { Programme } from "../config/programmes";
import { useApiCall } from "../hooks/useApiCall";
import { Button } from "../ui/Button";
import { Card } from "../ui/Card";
import { ErrorBanner } from "../ui/ErrorBanner";
import { Spinner } from "../ui/Spinner";
import { CitationsPanel } from "./CitationsPanel";
import { DisclaimerBar } from "./DisclaimerBar";
import { RefusalNotice } from "./RefusalNotice";

export function ChecklistPanel({ programme }: { programme: Programme }) {
  const { data, loading, error, run } = useApiCall(postChecklist);

  function onGenerate(): void {
    void run({
      university_slug: programme.university_slug,
      programme_slug: programme.programme_slug,
    });
  }

  return (
    <div className="space-y-4">
      <p className="text-sm text-slate-600">
        Generate the application checklist for {programme.title}.
      </p>
      <Button type="button" onClick={onGenerate} disabled={loading}>
        {loading ? "Generating..." : "Generate checklist"}
      </Button>

      {loading ? <Spinner label="Building the checklist..." /> : null}
      {error ? <ErrorBanner message={error} /> : null}

      {data ? (
        <Card>
          {data.insufficient_context || data.items.length === 0 ? (
            <RefusalNotice />
          ) : (
            <ul className="space-y-3">
              {data.items.map((item, index) => (
                <li key={`${item.requirement}-${index}`}>
                  <p className="text-sm font-medium text-slate-900">
                    {item.requirement}
                  </p>
                  <p className="text-sm text-slate-600">{item.detail}</p>
                </li>
              ))}
            </ul>
          )}
          <CitationsPanel citations={data.citations} />
          <DisclaimerBar text={data.disclaimer} />
        </Card>
      ) : null}
    </div>
  );
}
