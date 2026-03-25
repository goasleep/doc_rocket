import {
  BookOpen,
  Bot,
  FileText,
  Globe,
  Home,
  KeyRound,
  ListTodo,
  Rss,
  Scale,
  Settings,
  UploadCloud,
  Users,
  Workflow,
  Zap,
} from "lucide-react"

import { SidebarAppearance } from "@/components/Common/Appearance"
import { Logo } from "@/components/Common/Logo"
import {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarHeader,
} from "@/components/ui/sidebar"
import useAuth from "@/hooks/useAuth"
import { type Item, Main } from "./Main"
import { User } from "./User"

const baseItems: Item[] = [{ icon: Home, title: "Dashboard", path: "/" }]

const contentItems: Item[] = [
  { icon: Rss, title: "订阅源", path: "/sources" },
  { icon: UploadCloud, title: "手动投稿", path: "/submit" },
  { icon: BookOpen, title: "文章库", path: "/articles" },
  { icon: Globe, title: "外部参考", path: "/external-references" },
  { icon: KeyRound, title: "模型配置", path: "/llm-models" },
  { icon: Bot, title: "Agent 配置", path: "/agents" },
  { icon: Zap, title: "技能库", path: "/skills" },
  { icon: Scale, title: "评分标准", path: "/rubrics" },
  { icon: Workflow, title: "工作流", path: "/workflow" },
  { icon: ListTodo, title: "任务中心", path: "/tasks" },
  { icon: FileText, title: "仿写稿件", path: "/drafts" },
  { icon: Settings, title: "系统设置", path: "/settings" },
]

export function AppSidebar() {
  const { user: currentUser } = useAuth()

  const items = currentUser?.is_superuser
    ? [...baseItems, { icon: Users, title: "Admin", path: "/admin" }]
    : baseItems

  return (
    <Sidebar collapsible="icon">
      <SidebarHeader className="px-4 py-6 group-data-[collapsible=icon]:px-0 group-data-[collapsible=icon]:items-center">
        <Logo variant="responsive" />
      </SidebarHeader>
      <SidebarContent>
        <Main items={items} />
        <Main items={contentItems} />
      </SidebarContent>
      <SidebarFooter>
        <SidebarAppearance />
        <User user={currentUser} />
      </SidebarFooter>
    </Sidebar>
  )
}

export default AppSidebar
