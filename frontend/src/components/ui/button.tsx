import * as React from "react";
import { Slot } from "@radix-ui/react-slot";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils";

const variants = cva("button", {
  variants: {
    variant: {
      primary: "primary",
      secondary: "",
      ghost: "ghost",
      destructive: "danger",
    },
    size: { sm: "", md: "", icon: "icon" },
  },
  defaultVariants: { variant: "secondary", size: "md" },
});
export interface ButtonProps
  extends
    React.ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof variants> {
  asChild?: boolean;
}
export const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant, size, asChild = false, ...props }, ref) => {
    const Component = asChild ? Slot : "button";
    return (
      <Component
        ref={ref}
        className={cn(variants({ variant, size }), className)}
        {...props}
      />
    );
  },
);
Button.displayName = "Button";
