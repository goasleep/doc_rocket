import { Link as RouterLink, useRouterState } from "@tanstack/react-router"
import { ChevronRight, type LucideIcon } from "lucide-react"

import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "@/components/ui/collapsible"
import {
  SidebarGroup,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
  SidebarMenuSub,
  SidebarMenuSubButton,
  SidebarMenuSubItem,
  useSidebar,
} from "@/components/ui/sidebar"

export type MenuItem = {
  icon: LucideIcon
  title: string
  path: string
}

export type MenuGroup = {
  id: string
  title?: string
  icon: LucideIcon
  items: MenuItem[]
}

interface MenuGroupsProps {
  groups: MenuGroup[]
}

function isItemActive(item: MenuItem, currentPath: string): boolean {
  if (item.path === "/") {
    return currentPath === "/"
  }
  return currentPath.startsWith(item.path)
}

function isGroupActive(group: MenuGroup, currentPath: string): boolean {
  return group.items.some((item) => isItemActive(item, currentPath))
}

export function MenuGroups({ groups }: MenuGroupsProps) {
  const { isMobile, setOpenMobile } = useSidebar()
  const router = useRouterState()
  const currentPath = router.location.pathname

  const handleMenuClick = () => {
    if (isMobile) {
      setOpenMobile(false)
    }
  }

  return (
    <>
      {groups.map((group) => {
        const groupActive = isGroupActive(group, currentPath)

        // Dashboard 只有一个项目，直接显示
        if (group.items.length === 1 && group.id === "dashboard") {
          const item = group.items[0]
          const isActive = isItemActive(item, currentPath)

          return (
            <SidebarGroup key={group.id}>
              <SidebarMenu>
                <SidebarMenuItem>
                  <SidebarMenuButton
                    tooltip={item.title}
                    isActive={isActive}
                    asChild
                  >
                    <RouterLink to={item.path} onClick={handleMenuClick}>
                      <item.icon />
                      <span>{item.title}</span>
                    </RouterLink>
                  </SidebarMenuButton>
                </SidebarMenuItem>
              </SidebarMenu>
            </SidebarGroup>
          )
        }

        // 可折叠的菜单组
        return (
          <SidebarGroup key={group.id}>
            <Collapsible
              defaultOpen={groupActive}
              className="group/collapsible"
            >
              <SidebarMenu>
                <SidebarMenuItem>
                  <CollapsibleTrigger asChild>
                    <SidebarMenuButton
                      tooltip={group.title}
                      isActive={groupActive}
                    >
                      <group.icon />
                      <span>{group.title}</span>
                      <ChevronRight className="ml-auto transition-transform group-data-[state=open]/collapsible:rotate-90" />
                    </SidebarMenuButton>
                  </CollapsibleTrigger>
                  <CollapsibleContent>
                    <SidebarMenuSub>
                      {group.items.map((item) => {
                        const isActive = isItemActive(item, currentPath)

                        return (
                          <SidebarMenuSubItem key={item.title}>
                            <SidebarMenuSubButton isActive={isActive} asChild>
                              <RouterLink
                                to={item.path}
                                onClick={handleMenuClick}
                              >
                                <item.icon />
                                <span>{item.title}</span>
                              </RouterLink>
                            </SidebarMenuSubButton>
                          </SidebarMenuSubItem>
                        )
                      })}
                    </SidebarMenuSub>
                  </CollapsibleContent>
                </SidebarMenuItem>
              </SidebarMenu>
            </Collapsible>
          </SidebarGroup>
        )
      })}
    </>
  )
}
