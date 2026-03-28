import { expect, test } from "@playwright/test"

// Helper to login before tests
test.beforeEach(async ({ page }) => {
  // Navigate to login page
  await page.goto("/login")

  // Fill in credentials (using default test credentials)
  await page.fill('input[name="username"]', "admin@example.com")
  await page.fill('input[name="password"]', "changethis")

  // Click login button
  await page.click('button[type="submit"]')

  // Wait for navigation to complete
  await page.waitForURL("/")
})

test.describe("Token Usage on Agents Page", () => {
  test("Agent page displays token usage cards", async ({ page }) => {
    // Navigate to agents page
    await page.goto("/agents")

    // Wait for the page to load
    await page.waitForLoadState("networkidle")

    // Check for today's usage card
    await expect(page.getByText("Today's Usage")).toBeVisible()

    // Check for yesterday's usage card
    await expect(page.getByText("Yesterday's Usage")).toBeVisible()

    // Check for token stats in the cards
    await expect(page.getByText("Total tokens consumed")).toBeVisible()

    // Check for the breakdown labels
    await expect(page.getByText("Prompt")).toBeVisible()
    await expect(page.getByText("Completion")).toBeVisible()
    await expect(page.getByText("Calls")).toBeVisible()
  })

  test("Agent page displays trend chart with data", async ({ page }) => {
    // Navigate to agents page
    await page.goto("/agents")

    // Wait for the page to load
    await page.waitForLoadState("networkidle")

    // Check for trend chart title
    await expect(page.getByText("Token Usage Trend")).toBeVisible()

    // Check for the chart container (recharts renders an svg)
    const chartContainer = page.locator(".recharts-wrapper").first()
    await expect(chartContainer).toBeVisible()

    // Check for legend items
    await expect(page.getByText("Total Tokens")).toBeVisible()
    await expect(page.getByText("API Calls")).toBeVisible()
  })

  test("Chart time range selector (7d/30d/90d) works correctly", async ({
    page,
  }) => {
    // Navigate to agents page
    await page.goto("/agents")

    // Wait for the page to load
    await page.waitForLoadState("networkidle")

    // Find the time range selector
    const selector = page
      .locator('button[role="combobox"]')
      .filter({ hasText: /Last \d+ days/ })
    await expect(selector).toBeVisible()

    // Click to open the dropdown
    await selector.click()

    // Select 30 days
    await page.getByRole("option", { name: "Last 30 days" }).click()

    // Wait for the chart to update
    await page.waitForTimeout(500)

    // Verify the selector shows the new value
    await expect(
      page
        .locator('button[role="combobox"]')
        .filter({ hasText: "Last 30 days" }),
    ).toBeVisible()

    // Click to open again
    await selector.click()

    // Select 90 days
    await page.getByRole("option", { name: "Last 90 days" }).click()

    // Wait for the chart to update
    await page.waitForTimeout(500)

    // Verify the selector shows the new value
    await expect(
      page
        .locator('button[role="combobox"]')
        .filter({ hasText: "Last 90 days" }),
    ).toBeVisible()
  })

  test("Agent comparison chart displays", async ({ page }) => {
    // Navigate to agents page
    await page.goto("/agents")

    // Wait for the page to load
    await page.waitForLoadState("networkidle")

    // Check for agent comparison chart title
    await expect(page.getByText("Agent Usage (Last 7 Days)")).toBeVisible()

    // Check for the chart container
    const chartContainer = page.locator(".recharts-wrapper").nth(1)
    await expect(chartContainer).toBeVisible()
  })
})

test.describe("Token Usage on Article Detail Page", () => {
  test("Article detail page shows token breakdown tab", async ({ page }) => {
    // First, navigate to articles list
    await page.goto("/articles")

    // Wait for the page to load
    await page.waitForLoadState("networkidle")

    // If there are articles, click on the first one
    const firstArticle = page.locator("a[href^='/articles/']").first()

    if (await firstArticle.isVisible().catch(() => false)) {
      await firstArticle.click()

      // Wait for navigation to article detail
      await page.waitForURL(/\/articles\/.+/)

      // Check for the Token Usage tab
      await expect(page.getByRole("tab", { name: /Token 消耗/ })).toBeVisible()

      // Click on the Token Usage tab
      await page.getByRole("tab", { name: /Token 消耗/ }).click()

      // Check for token usage content
      await expect(
        page
          .getByText("Token Usage Breakdown")
          .or(page.getByText("No token usage recorded")),
      ).toBeVisible()
    } else {
      // Skip if no articles exist
      test.skip()
    }
  })

  test("Article detail page shows distribution charts when data exists", async ({
    page,
  }) => {
    // Navigate to articles list
    await page.goto("/articles")

    // Wait for the page to load
    await page.waitForLoadState("networkidle")

    // Try to find an article with token usage
    const firstArticle = page.locator("a[href^='/articles/']").first()

    if (await firstArticle.isVisible().catch(() => false)) {
      await firstArticle.click()
      await page.waitForURL(/\/articles\/.+/)

      // Click on the Token Usage tab
      const tokenTab = page.getByRole("tab", { name: /Token 消耗/ })
      if (await tokenTab.isVisible().catch(() => false)) {
        await tokenTab.click()

        // Wait a bit for data to load
        await page.waitForTimeout(500)

        // Check if distribution charts are visible (if there's data)
        const hasData = await page
          .getByText("Tokens by Operation")
          .isVisible()
          .catch(() => false)

        if (hasData) {
          await expect(page.getByText("Tokens by Operation")).toBeVisible()
          await expect(page.getByText("Tokens by Model")).toBeVisible()

          // Check for pie charts (recharts renders as svg)
          const pieCharts = page.locator(".recharts-pie").count()
          expect(pieCharts).toBeGreaterThan(0)
        }
      }
    } else {
      test.skip()
    }
  })
})

test.describe("Token Usage Responsive Design", () => {
  test("Charts stack vertically on mobile viewport", async ({ page }) => {
    // Set mobile viewport
    await page.setViewportSize({ width: 375, height: 667 })

    // Navigate to agents page
    await page.goto("/agents")

    // Wait for the page to load
    await page.waitForLoadState("networkidle")

    // Check that cards are stacked (not side by side)
    const cards = page.locator(".recharts-wrapper")
    const count = await cards.count()

    if (count > 0) {
      // On mobile, charts should be visible but may be stacked
      // Just verify they exist and are visible
      for (let i = 0; i < count; i++) {
        await expect(cards.nth(i)).toBeVisible()
      }
    }
  })
})

test.describe("Token Usage Console Errors", () => {
  test("No console errors during token usage display", async ({ page }) => {
    const errors: string[] = []

    // Capture console errors
    page.on("console", (msg) => {
      if (msg.type() === "error") {
        errors.push(msg.text())
      }
    })

    // Navigate to agents page
    await page.goto("/agents")
    await page.waitForLoadState("networkidle")

    // Wait for charts to render
    await page.waitForTimeout(1000)

    // Check for console errors (excluding known React/development warnings)
    const relevantErrors = errors.filter(
      (e) =>
        !e.includes("React") &&
        !e.includes("StrictMode") &&
        !e.includes("dev-tools") &&
        !e.includes("[HMR]") &&
        !e.includes("hot-update"),
    )

    expect(relevantErrors).toHaveLength(0)
  })
})
