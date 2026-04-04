import {
  BarChart3,
  BookOpen,
  Bot,
  FileText,
  Globe,
  Home,
  KeyRound,
  LayoutDashboard,
  ListTodo,
  Rss,
  Scale,
  Settings,
  Shield,
  Sparkles,
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
import { type MenuGroup, MenuGroups } from "./MenuGroups"
import { User } from "./User"

const menuGroups: MenuGroup[] = [
  {
    id: "dashboard",
    icon: LayoutDashboard,
    items: [{ icon: Home, title: "Dashboard", path: "/" }],
  },
  {
    id: "content",
    title: "内容管理",
    icon: BookOpen,
    items: [
      { icon: Rss, title: "订阅源", path: "/sources" },
      { icon: UploadCloud, title: "手动投稿", path: "/submit" },
      { icon: BookOpen, title: "文章库", path: "/articles" },
      { icon: Globe, title: "外部参考", path: "/external-references" },
    ],
  },
  {
    id: "ai",
    title: "智能分析",
    icon: Sparkles,
    items: [
      { icon: BarChart3, title: "知识洞察", path: "/insights" },
      { icon: KeyRound, title: "模型配置", path: "/llm-models" },
      { icon: Bot, title: "Agent 配置", path: "/agents" },
      { icon: Zap, title: "技能库", path: "/skills" },
      { icon: Scale, title: "评分标准", path: "/rubrics" },
    ],
  },
  {
    id: "workflow",
    title: "工作流",
    icon: Workflow,
    items: [
      { icon: Workflow, title: "工作流", path: "/workflow" },
      { icon: ListTodo, title: "任务中心", path: "/tasks" },
      { icon: FileText, title: "仿写稿件", path: "/drafts" },
    ],
  },
  {
    id: "system",
    title: "系统",
    icon: Settings,
    items: [
      { icon: Settings, title: "用户设置", path: "/settings" },
      { icon: Shield, title: "系统设置", path: "/system-settings" },
    ],
  },
]

const adminGroup: MenuGroup = {
  id: "admin",
  title: "管理",
  icon: Users,
  items: [{ icon: Users, title: "Admin", path: "/admin" }],
}

export function AppSidebar() {
  const { user: currentUser } = useAuth()

  const groups = currentUser?.is_superuser
    ? [...menuGroups, adminGroup]
    : menuGroups

  return (
    <Sidebar collapsible="icon">
      <SidebarHeader className="px-4 py-6 group-data-[collapsible=icon]:px-0 group-data-[collapsible=icon]:items-center">
        <Logo variant="responsive" />
      </SidebarHeader>
      <SidebarContent>
        <MenuGroups groups={groups} />
      </SidebarContent>
      <SidebarFooter>
        <SidebarAppearance />
        <User user={currentUser} />
      </SidebarFooter>
    </Sidebar>
  )
}

export default AppSidebar
