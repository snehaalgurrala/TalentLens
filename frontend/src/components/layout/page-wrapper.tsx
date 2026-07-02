import * as React from "react"

import { cn } from "@/lib/utils"
import { Container, type ContainerProps } from "@/components/layout/container"
import { Stack } from "@/components/layout/stack"

export interface PageWrapperProps extends React.ComponentProps<"main"> {
  title?: string
  description?: string
  actions?: React.ReactNode
  breadcrumbs?: React.ReactNode
  containerSize?: ContainerProps["size"]
}

function PageWrapper({
  title,
  description,
  actions,
  breadcrumbs,
  containerSize = "xl",
  className,
  children,
  ...props
}: PageWrapperProps) {
  return (
    <main data-slot="page-wrapper" className={cn("py-6 sm:py-8", className)} {...props}>
      <Container size={containerSize}>
        <Stack gap="lg">
          {breadcrumbs}
          {(title || description || actions) && (
            <Stack
              direction="row"
              align="start"
              justify="between"
              gap="md"
              className="flex-wrap"
            >
              <Stack gap="xs">
                {title && <h1 className="text-h2 text-foreground">{title}</h1>}
                {description && (
                  <p className="text-body text-muted-foreground">
                    {description}
                  </p>
                )}
              </Stack>
              {actions && (
                <div className="flex shrink-0 items-center gap-2">
                  {actions}
                </div>
              )}
            </Stack>
          )}
          {children}
        </Stack>
      </Container>
    </main>
  )
}

export { PageWrapper }
