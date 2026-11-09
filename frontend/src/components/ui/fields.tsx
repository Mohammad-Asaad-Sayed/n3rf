import type { ComponentProps } from "react";
import { cn } from "../../lib/cn";

type InputProps = ComponentProps<"input">;
type SelectProps = ComponentProps<"select">;
type TextareaProps = ComponentProps<"textarea">;

export function Input({ className, ...props }: InputProps) {
  return <input className={cn("form-control", className)} {...props} />;
}

export function Select({ className, ...props }: SelectProps) {
  return <select className={cn("form-control", className)} {...props} />;
}

export function Textarea({ className, ...props }: TextareaProps) {
  return <textarea className={cn("form-control", className)} {...props} />;
}
