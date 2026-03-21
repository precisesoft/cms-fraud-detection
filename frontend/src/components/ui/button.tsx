"use client";

import { Button as ButtonPrimitive } from "@base-ui/react/button";
import { cva, type VariantProps } from "class-variance-authority";

import { cn } from "@/lib/utils";

const buttonVariants = cva(
  "group/button inline-flex shrink-0 items-center justify-center rounded-lg text-sm font-semibold whitespace-nowrap transition-all duration-150 outline-none select-none focus-visible:ring-2 focus-visible:ring-accent/50 active:translate-y-px disabled:pointer-events-none disabled:opacity-50 [&_svg]:pointer-events-none [&_svg]:shrink-0 [&_svg:not([class*='size-'])]:size-4",
  {
    variants: {
      variant: {
        default:
          "bg-accent text-accent-foreground neu-subtle hover:brightness-110 active:neu-pressed",
        outline:
          "border border-border/50 bg-card text-foreground neu-subtle hover:bg-muted active:neu-pressed",
        secondary:
          "bg-secondary text-secondary-foreground neu-subtle hover:bg-secondary/80 active:neu-pressed",
        ghost:
          "text-muted-foreground hover:text-foreground hover:neu-subtle active:neu-pressed",
        destructive:
          "bg-destructive/10 text-destructive neu-subtle hover:bg-destructive/20 active:neu-pressed",
        link: "text-accent underline-offset-4 hover:underline",
      },
      size: {
        default: "h-9 gap-1.5 px-3",
        xs: "h-6 gap-1 rounded-md px-2 text-xs",
        sm: "h-7 gap-1 rounded-md px-2.5 text-[0.8rem]",
        lg: "h-10 gap-1.5 px-4",
        icon: "size-9",
        "icon-xs": "size-6 rounded-md",
        "icon-sm": "size-7 rounded-md",
        "icon-lg": "size-10",
      },
    },
    defaultVariants: {
      variant: "default",
      size: "default",
    },
  },
);

function Button({
  className,
  variant = "default",
  size = "default",
  ...props
}: ButtonPrimitive.Props & VariantProps<typeof buttonVariants>) {
  return (
    <ButtonPrimitive
      data-slot="button"
      className={cn(buttonVariants({ variant, size, className }))}
      {...props}
    />
  );
}

export { Button, buttonVariants };
