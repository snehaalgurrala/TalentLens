import { MoreHorizontal } from "lucide-react"

import { Button } from "@/components/ui/button"
import {
  Dialog,
  DialogClose,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip"
import { Row, Section } from "../_components/section"

function OverlaysSection() {
  return (
    <Section
      id="overlays"
      title="Overlays"
      description="Dialog, Tooltip, and Dropdown Menu keep Radix's built-in data-state animations rather than layering Framer Motion, for accessible focus/exit handling."
    >
      <Row label="Dialog">
        <Dialog>
          <DialogTrigger asChild>
            <Button variant="outline">Open dialog</Button>
          </DialogTrigger>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Reject candidate</DialogTitle>
              <DialogDescription>
                This moves the candidate to the Rejected stage and notifies
                the hiring manager.
              </DialogDescription>
            </DialogHeader>
            <DialogFooter>
              <DialogClose asChild>
                <Button variant="outline">Cancel</Button>
              </DialogClose>
              <Button variant="danger">Reject</Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </Row>

      <Row label="Tooltip">
        <Tooltip>
          <TooltipTrigger asChild>
            <Button variant="outline">Hover me</Button>
          </TooltipTrigger>
          <TooltipContent>Match score based on JD similarity</TooltipContent>
        </Tooltip>
      </Row>

      <Row label="Dropdown menu">
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button variant="outline" size="icon" aria-label="More actions">
              <MoreHorizontal />
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent>
            <DropdownMenuItem>View profile</DropdownMenuItem>
            <DropdownMenuItem>Send message</DropdownMenuItem>
            <DropdownMenuSeparator />
            <DropdownMenuItem variant="destructive">
              Reject candidate
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </Row>
    </Section>
  )
}

export { OverlaysSection }
