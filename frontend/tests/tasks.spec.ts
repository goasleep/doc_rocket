import { expect, test } from "@playwright/test"

test.describe("Task Center", () => {
  test.beforeEach(async ({ page }) => {
    // Login first
    await page.goto("/login")
    await page.fill('input[name="username"]', "admin@example.com")
    await page.fill('input[name="password"]', "changethis")
    await page.click('button[type="submit"]')
    await page.waitForURL("/")
  })

  test("task center page is accessible at /tasks", async ({ page }) => {
    await page.goto("/tasks")
    await expect(page.getByText("任务中心")).toBeVisible()
    await expect(page.getByRole("table")).toBeVisible()
  })

  test("page shows task table headers", async ({ page }) => {
    await page.goto("/tasks")
    await expect(page.getByRole("columnheader", { name: "类型" })).toBeVisible()
    await expect(page.getByRole("columnheader", { name: "来源" })).toBeVisible()
    await expect(page.getByRole("columnheader", { name: "状态" })).toBeVisible()
  })

  test("sidebar shows 任务中心 navigation item", async ({ page }) => {
    await page.goto("/")
    await expect(page.getByRole("link", { name: "任务中心" })).toBeVisible()
  })

  test("article detail page has 任务历史 tab", async ({ page }) => {
    // Navigate to articles list
    await page.goto("/articles")
    const firstArticle = page.locator("table tbody tr").first()
    const articleLink = firstArticle.getByRole("link").first()
    if (await articleLink.isVisible()) {
      await articleLink.click()
      await expect(page.getByRole("tab", { name: /任务历史/ })).toBeVisible()
    }
  })

  test("任务历史 tab timeline starts with 入库 node", async ({ page }) => {
    await page.goto("/articles")
    const firstArticle = page.locator("table tbody tr").first()
    const articleLink = firstArticle.getByRole("link").first()
    if (await articleLink.isVisible()) {
      await articleLink.click()
      await page.getByRole("tab", { name: /任务历史/ }).click()
      await expect(page.getByText("入库")).toBeVisible()
    }
  })
})
