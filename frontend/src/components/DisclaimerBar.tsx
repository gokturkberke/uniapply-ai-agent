export function DisclaimerBar({ text }: { text: string }) {
  return (
    <p className="border-t border-slate-100 pt-3 text-xs italic text-slate-500">
      {text}
    </p>
  );
}
