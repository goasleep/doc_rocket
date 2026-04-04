import { createFileRoute } from '@tanstack/react-router'

export const Route = createFileRoute('/_layout/articles/$id')({
  component: RouteComponent,
})

function RouteComponent() {
  return <div>Hello "/_layout/articles/$id"!</div>
}
