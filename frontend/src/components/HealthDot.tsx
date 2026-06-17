import { useEffect } from "react";

import { getHealth } from "../api/endpoints";
import { useApiCall } from "../hooks/useApiCall";

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
    <span
      className="flex items-center gap-1.5 text-xs text-slate-500"
      title={error ?? text}
    >
      <span className={`h-2 w-2 rounded-full ${color}`} aria-hidden="true" />
      {text}
    </span>
  );
}
