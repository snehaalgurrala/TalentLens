import {
  BarChart3Icon,
  ClipboardCheckIcon,
  LayoutDashboardIcon,
  MegaphoneIcon,
  SettingsIcon,
  UsersIcon,
  type LucideIcon,
} from "lucide-react"

export interface NavItem {
  title: string
  href: string
  icon: LucideIcon
}

/** Primary dashboard navigation — consumed by the sidebar and mobile drawer. */
export const dashboardNavItems: NavItem[] = [
  { title: "Dashboard", href: "/dashboard", icon: LayoutDashboardIcon },
  { title: "Campaigns", href: "/campaigns", icon: MegaphoneIcon },
  { title: "Candidates", href: "/candidates", icon: UsersIcon },
  { title: "Assessments", href: "/assessments", icon: ClipboardCheckIcon },
  { title: "Analytics", href: "/analytics", icon: BarChart3Icon },
  { title: "Settings", href: "/settings", icon: SettingsIcon },
]
