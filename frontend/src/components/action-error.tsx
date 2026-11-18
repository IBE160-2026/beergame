import { cn } from "@/lib/utils";

/**
 * The inline line beside an action that failed (UX-DR59): «Det ble ikke lagret. Prøv igjen.» or
 * the action's own wording. `role="alert"` announces it at once; focus stays on the action's
 * button, which stays active (EXPERIENCE.md → Accessibility Floor → Order and action results).
 */
export function ActionError({ message, className }: { message?: string; className?: string }) {
  if (!message) return null;
  return (
    <p role="alert" className={cn("text-body-phone text-restordre", className)}>
      {message}
    </p>
  );
}
