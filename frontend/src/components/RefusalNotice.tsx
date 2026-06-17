const DEFAULT_REFUSAL =
  "The official documents for this programme do not cover this. Try rephrasing, or verify directly on the university portal.";

export function RefusalNotice({ message }: { message?: string }) {
  const text = message && message.trim() ? message : DEFAULT_REFUSAL;
  return (
    <div className="rounded-md border border-amber-200 bg-amber-50 px-3 py-3 text-sm text-amber-800">
      <p className="font-medium">Not found in the official documents</p>
      <p className="mt-1">{text}</p>
    </div>
  );
}
