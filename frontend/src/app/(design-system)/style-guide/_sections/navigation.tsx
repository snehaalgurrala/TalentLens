import {
  Breadcrumb,
  BreadcrumbItem,
  BreadcrumbLink,
  BreadcrumbList,
  BreadcrumbPage,
  BreadcrumbSeparator,
} from "@/components/ui/breadcrumb"
import {
  Pagination,
  PaginationContent,
  PaginationEllipsis,
  PaginationItem,
  PaginationLink,
  PaginationNext,
  PaginationPrevious,
} from "@/components/ui/pagination"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Row, Section } from "../_components/section"

function NavigationSection() {
  return (
    <Section
      id="navigation"
      title="Navigation"
      description="Tabs, Pagination, and Breadcrumbs — keyboard-navigable with aria-current on the active page."
    >
      <Row label="Tabs">
        <Tabs defaultValue="overview" className="w-full max-w-md">
          <TabsList>
            <TabsTrigger value="overview">Overview</TabsTrigger>
            <TabsTrigger value="resume">Resume</TabsTrigger>
            <TabsTrigger value="scoring">Scoring</TabsTrigger>
          </TabsList>
          <TabsContent value="overview" className="pt-3 text-sm text-muted-foreground">
            Candidate overview content.
          </TabsContent>
          <TabsContent value="resume" className="pt-3 text-sm text-muted-foreground">
            Parsed resume content.
          </TabsContent>
          <TabsContent value="scoring" className="pt-3 text-sm text-muted-foreground">
            Scoring breakdown content.
          </TabsContent>
        </Tabs>
      </Row>

      <Row label="Pagination">
        <Pagination>
          <PaginationContent>
            <PaginationItem>
              <PaginationPrevious href="#" />
            </PaginationItem>
            <PaginationItem>
              <PaginationLink href="#">1</PaginationLink>
            </PaginationItem>
            <PaginationItem>
              <PaginationLink href="#" isActive>
                2
              </PaginationLink>
            </PaginationItem>
            <PaginationItem>
              <PaginationLink href="#">3</PaginationLink>
            </PaginationItem>
            <PaginationItem>
              <PaginationEllipsis />
            </PaginationItem>
            <PaginationItem>
              <PaginationNext href="#" />
            </PaginationItem>
          </PaginationContent>
        </Pagination>
      </Row>

      <Row label="Breadcrumb">
        <Breadcrumb>
          <BreadcrumbList>
            <BreadcrumbItem>
              <BreadcrumbLink href="#">Campaigns</BreadcrumbLink>
            </BreadcrumbItem>
            <BreadcrumbSeparator />
            <BreadcrumbItem>
              <BreadcrumbLink href="#">Senior Frontend Engineer</BreadcrumbLink>
            </BreadcrumbItem>
            <BreadcrumbSeparator />
            <BreadcrumbItem>
              <BreadcrumbPage>Candidates</BreadcrumbPage>
            </BreadcrumbItem>
          </BreadcrumbList>
        </Breadcrumb>
      </Row>
    </Section>
  )
}

export { NavigationSection }
