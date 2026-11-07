import { cva, type VariantProps } from "class-variance-authority";
import type { ButtonHTMLAttributes } from "react";
import { cn } from "../../lib/cn";

const buttonStyles = cva("ui-button", {
  variants: {
    variant: {
      default: "ui-button-default",
      primary: "ui-button-primary",
      ghost: "ui-button-ghost",
      icon: "ui-button-icon",
    },
    size: {
      default: "ui-button-md",
      sm: "ui-button-sm",
      icon: "ui-button-icon-size",
    },
  },
  defaultVariants: { variant: "default", size: "default" },
});

type ButtonProps = ButtonHTMLAttributes<HTMLButtonElement> & VariantProps<typeof buttonStyles>;

export function Button({ className, variant, size, ...props }: ButtonProps) {
  return <button className={cn(buttonStyles({ variant, size }), className)} {...props} />;
}
