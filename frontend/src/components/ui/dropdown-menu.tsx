import * as Dropdown from "@radix-ui/react-dropdown-menu";
import type { ComponentPropsWithoutRef } from "react";
import { cn } from "@/lib/utils";
export const DropdownMenu = Dropdown.Root;
export const DropdownMenuTrigger = Dropdown.Trigger;
export function DropdownMenuContent({
  className,
  ...props
}: ComponentPropsWithoutRef<typeof Dropdown.Content>) {
  return (
    <Dropdown.Portal>
      <Dropdown.Content
        sideOffset={6}
        align="end"
        className={cn("menu", className)}
        {...props}
      />
    </Dropdown.Portal>
  );
}
export function DropdownMenuItem({
  className,
  ...props
}: ComponentPropsWithoutRef<typeof Dropdown.Item>) {
  return <Dropdown.Item className={cn("menu-item", className)} {...props} />;
}
