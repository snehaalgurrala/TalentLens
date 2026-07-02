"use client"

import * as React from "react"

import { Checkbox } from "@/components/ui/checkbox"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { PasswordInput } from "@/components/ui/password-input"
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group"
import { SearchInput } from "@/components/ui/search-input"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { Switch } from "@/components/ui/switch"
import { Textarea } from "@/components/ui/textarea"
import { Row, Section } from "../_components/section"

function FormControlsSection() {
  const [search, setSearch] = React.useState("")

  return (
    <Section
      id="form-controls"
      title="Form controls"
      description="Text, Password, Search, Textarea, Select, Checkbox, Radio, Switch — all themed via the --input token for WCAG-compliant borders."
    >
      <Row label="Text">
        <div className="flex w-64 flex-col gap-1.5">
          <Label htmlFor="sg-text">Full name</Label>
          <Input id="sg-text" placeholder="Jane Doe" />
        </div>
      </Row>

      <Row label="Password">
        <div className="flex w-64 flex-col gap-1.5">
          <Label htmlFor="sg-password">Password</Label>
          <PasswordInput id="sg-password" placeholder="••••••••" />
        </div>
      </Row>

      <Row label="Search">
        <div className="w-64">
          <SearchInput
            placeholder="Search candidates..."
            value={search}
            onChange={(event) => setSearch(event.target.value)}
            onClear={() => setSearch("")}
          />
        </div>
      </Row>

      <Row label="Textarea">
        <div className="flex w-64 flex-col gap-1.5">
          <Label htmlFor="sg-textarea">Notes</Label>
          <Textarea id="sg-textarea" placeholder="Add a note..." />
        </div>
      </Row>

      <Row label="Select">
        <Select defaultValue="active">
          <SelectTrigger className="w-48">
            <SelectValue placeholder="Status" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="active">Active</SelectItem>
            <SelectItem value="pending">Pending</SelectItem>
            <SelectItem value="rejected">Rejected</SelectItem>
          </SelectContent>
        </Select>
      </Row>

      <Row label="Checkbox">
        <div className="flex items-center gap-2">
          <Checkbox id="sg-checkbox" defaultChecked />
          <Label htmlFor="sg-checkbox">Email notifications</Label>
        </div>
      </Row>

      <Row label="Radio">
        <RadioGroup defaultValue="remote" className="flex flex-row gap-4">
          <div className="flex items-center gap-2">
            <RadioGroupItem value="remote" id="sg-radio-remote" />
            <Label htmlFor="sg-radio-remote">Remote</Label>
          </div>
          <div className="flex items-center gap-2">
            <RadioGroupItem value="onsite" id="sg-radio-onsite" />
            <Label htmlFor="sg-radio-onsite">Onsite</Label>
          </div>
        </RadioGroup>
      </Row>

      <Row label="Switch">
        <div className="flex items-center gap-2">
          <Switch id="sg-switch" defaultChecked />
          <Label htmlFor="sg-switch">Auto-rank candidates</Label>
        </div>
      </Row>
    </Section>
  )
}

export { FormControlsSection }
