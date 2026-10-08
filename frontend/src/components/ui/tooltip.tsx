import * as TooltipPrimitive from "@radix-ui/react-tooltip";
import type { ComponentPropsWithoutRef } from "react";
export const TooltipProvider = TooltipPrimitive.Provider;
export const Tooltip = TooltipPrimitive.Root;
export const TooltipTrigger = TooltipPrimitive.Trigger;
export function TooltipContent(
  props: ComponentPropsWithoutRef<typeof TooltipPrimitive.Content>,
) {
  return (
    <TooltipPrimitive.Portal>
      <TooltipPrimitive.Content sideOffset={6} className="tooltip" {...props} />
    </TooltipPrimitive.Portal>
  );
}
