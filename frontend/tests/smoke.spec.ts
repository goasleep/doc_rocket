import { expect, test } from "@playwright/test"

const TEST_URL =
  "https://www.ruanyifeng.com/blog/2024/03/weekly-issue-292.html"

test.describe("Full-stack content intelligence smoke test", () => {
  test.beforeEach(async ({ page }) => {
    // The chromium project uses storageState from auth.setup.ts,
    // so we are already logged in. Just verify the dashboard loads.
    await page.goto("/")
    await expect(
      page.getByText("Welcome back, nice to see you again!"),
    ).toBeVisible()
  })

  test("submit article URL and verify success", async ({ page }) => {
    // Navigate to submit page
    await page.getByRole("button", { name: "内容管理" }).click()
    await page.getByRole("link", { name: "手动投稿" }).click()
    await page.waitForURL("/submit")

    // Switch to URL batch tab
    await page.getByRole("tab", { name: /URL 抓取/ }).click()
    await page
      .getByRole("textbox", { name: /文章 URL 列表/ })
      .fill(TEST_URL)

    // Submit should become enabled after filling URL
    const submitBtn = page.getByRole("button", { name: /批量抓取/ })
    await expect(submitBtn).toBeEnabled()
    await submitBtn.click()

    // Verify success toast
    await expect(page.getByText(/已提交.*URL 进行抓取/)).toBeVisible()

    // Should redirect to articles page
    await page.waitForURL(/\/articles/)
    await expect(page.getByRole("heading", { name: "文章库" })).toBeVisible()

    // Wait for the newly submitted article to appear in the table
    const firstArticleLink = page.locator("table tbody tr").first().getByRole("link").first()
    await expect(firstArticleLink).toBeVisible()

    // Verify the article status shows "分析中" or "已分析".
    // The full analysis depends on async Celery + LLM which can take a while;
    // for a smoke test we verify the pipeline was triggered correctly.
    const firstStatusBadge = page
      .locator("table tbody tr")
      .first()
      .locator("td:nth-child(3)")
    await expect
      .poll(
        async () => {
          const text = await firstStatusBadge.textContent().catch(() => "")
          return text?.trim() ?? ""
        },
        {
          message: "等待文章状态变为分析中或已分析",
          intervals: [1_000, 1_000, 2_000, 2_000, 2_000],
          timeout: 15_000,
        },
      )
      .toMatch(/分析中|已分析/)
  })

  test("trigger imitation writing workflow", async ({ page }) => {
    await page.goto("/workflow")

    await expect(
      page.getByRole("heading", { name: "工作流", exact: true }),
    ).toBeVisible()
    await expect(
      page.getByText("AI 多 Agent 协作仿写，实时追踪进度"),
    ).toBeVisible()

    // Fill topic
    await page
      .getByPlaceholder(/例如：AI 会取代程序员吗？/)
      .fill("冒烟测试：AI 会取代程序员吗？")

    // Submit workflow
    const startBtn = page.getByRole("button", { name: "开始仿写" })
    await expect(startBtn).toBeEnabled()
    await startBtn.click()

    // Should redirect to workflow run detail page
    await page.waitForURL(/\/workflow\?run_id=.*/)

    // Verify run status badge/text is shown (not the combobox option)
    await expect(
      page.locator("span, div").filter({ hasText: /运行中|工作流排队中/ }).first(),
    ).toBeVisible()

    // Verify toast
    await expect(page.getByText("工作流已触发")).toBeVisible()
  })

  test("draft editor shows publish dialog and preview", async ({ page }) => {
    // This test assumes seed-smoke-draft.py has been executed beforehand
    await page.goto("/drafts")
    await expect(page.getByRole("heading", { name: "仿写稿件" })).toBeVisible()

    // Open the seeded draft
    const draftLink = page.getByRole("link", { name: "冒烟测试仿写稿件" })
    await expect(draftLink).toBeVisible()
    await draftLink.click()

    // Draft editor loads
    await expect(
      page.getByRole("button", { name: "发布到公众号" }),
    ).toBeVisible()
    await expect(page.getByRole("button", { name: "预览" })).toBeVisible()
    // "标记为已发布" button is hidden when draft.status === "approved"
    await expect(
      page.getByRole("button", { name: "标记为已发布" }),
    ).not.toBeVisible()

    // Test preview modal
    await page.getByRole("button", { name: "预览" }).click()
    await expect(
      page.getByRole("heading", { name: /微信公众号预览/ }),
    ).toBeVisible()
    await page.getByRole("button", { name: "关闭" }).click()
    await expect(
      page.getByRole("heading", { name: /微信公众号预览/ }),
    ).not.toBeVisible()

    // Mock publish API to avoid real WeChat calls
    await page.route(/.*\/api\/v1\/drafts\/.*\/publish/, async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          success: true,
          publish_id: "pub_smoke_123",
          message: "Draft published successfully to WeChat MP",
        }),
      })
    })

    // Mock cover image upload API
    await page.route(/.*\/api\/v1\/drafts\/.*\/upload-cover/, async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          cover_image_url:
            "https://example.com/smoke-test-cover.jpg",
        }),
      })
    })

    // Open publish dialog
    await page.getByRole("button", { name: "发布到公众号" }).click()
    await expect(
      page.getByRole("dialog").getByText("发布到微信公众号"),
    ).toBeVisible()
    await expect(page.getByText("排版主题", { exact: true })).toBeVisible()
    await expect(page.getByText("封面图片 *")).toBeVisible()

    // Verify theme selector exists
    await expect(page.getByRole("combobox")).toBeVisible()

    // Confirm button is disabled before cover upload
    const confirmBtn = page
      .getByRole("dialog")
      .getByRole("button", { name: "确认发布" })
    await expect(confirmBtn).toBeDisabled()

    // Upload a dummy cover image using a small 1x1 PNG
    const fileInput = page.locator('input#cover-upload')
    // 1x1 transparent PNG in base64
    const pngBase64 =
      "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
    const pngBuffer = Buffer.from(pngBase64, "base64")
    await fileInput.setInputFiles({
      name: "smoke-cover.png",
      mimeType: "image/png",
      buffer: pngBuffer,
    })

    // Wait for the mock upload response and the cover preview to appear
    await expect(
      page.locator('img[alt="封面预览"]'),
    ).toBeVisible()

    // Confirm button should now be enabled
    await expect(confirmBtn).toBeEnabled()

    // Click confirm and verify success toast
    await confirmBtn.click()
    await expect(page.getByText(/发布成功|Draft published successfully/)).toBeVisible()

    // Dialog should close after successful publish
    await expect(
      page.getByRole("dialog").getByText("发布到微信公众号"),
    ).not.toBeVisible()
  })
})
