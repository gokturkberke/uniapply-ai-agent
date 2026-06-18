import { useEffect } from "react";

import { getHealth } from "../api/endpoints";
import { useApiCall } from "../hooks/useApiCall";

function ProviderChip({
  provider,
  model,
}: {
  provider: string;
  model: string | null;
}) {
  if (provider === "mock") {
    return (
      <span
        className="rounded-full bg-amber-100 px-2 py-0.5 text-xs font-medium text-amber-800"
        title="Mock provider returns refusals by design. Run the API with a local model (make run-local) for real answers."
      >
        mock (demo stub)
      </span>
    );
  }
  return (
    <span
      className="rounded-full bg-slate-100 px-2 py-0.5 text-xs font-medium text-slate-600"
      title={`LLM provider: ${provider}`}
    >
      {model ?? provider}
    </span>
  );
}

export function HealthDot() {
  const { data, loading, error, run } = useApiCall(getHealth);

  useEffect(() => {
    void run();
  }, [run]);

  let color = "bg-slate-300";
  let text = "Checking API...";
  if (!loading && data) {
    color = "bg-green-500";
    text = "API online";
  } else if (!loading && error) {
    color = "bg-red-500";
    text = "API offline";
  }

  return (
    <span className="flex items-center gap-2 text-xs text-slate-500">
      <span className="flex items-center gap-1.5" title={error ?? text}>
        <span className={`h-2 w-2 rounded-full ${color}`} aria-hidden="true" />
        {text}
      </span>
      {data ? (
        <ProviderChip provider={data.llm_provider} model={data.llm_model} />
      ) : null}
    </span>
  );
}
