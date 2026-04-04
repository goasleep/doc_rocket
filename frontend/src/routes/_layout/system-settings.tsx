import { createFileRoute } from "@tanstack/react-router"

import { SystemSettings } from "@/components/UserSettings/SystemSettings"

export const Route = createFileRoute("/_layout/system-settings")({
  component: SystemSettingsPage,
  head: () => ({
    meta: [
      {
        title: "System Settings - FastAPI Template",
      },
    ],
  }),
})

function SystemSettingsPage() {
  return (
    <div className="flex flex-col gap-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">System Settings</h1>
        <p className="text-muted-foreground">
          Manage system-wide configuration and API keys
        </p>
      </div>

      <SystemSettings />
    </div>
  )
}
