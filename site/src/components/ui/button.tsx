import type { ButtonHTMLAttributes } from "react";

type ButtonProps = ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: "default" | "primary" | "ghost";
};

export function Button({ variant = "default", ...props }: ButtonProps) {
  return (
    <button
      className={`ui-button ui-button-md ui-button-${variant}`}
      {...props}
    />
  );
}
