import { expect, test } from "@playwright/test"

const randomConfigName = () =>
  `e2e-model-${Date.now()}-${Math.random().toString(36).substring(7)}`

test("LLM Models page is accessible and shows correct heading", async ({
  page,
}) => {
  await page.goto("/llm-models")
  await expect(page.getByRole("heading", { name: "模型配置" })).toBeVisible()
})

test("新建配置 button is visible for superuser", async ({ page }) => {
  await page.goto("/llm-models")
  await expect(page.getByRole("button", { name: "新建配置" })).toBeVisible()
})

test("Sidebar shows 模型配置 link", async ({ page }) => {
  await page.goto("/")
  await expect(page.getByRole("link", { name: "模型配置" })).toBeVisible()
})

test.describe("LLM model config management", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto("/llm-models")
  })

  test("Create a Kimi model config", async ({ page }) => {
    const configName = randomConfigName()

    await page.getByRole("button", { name: "新建配置" }).click()
    await expect(page.getByRole("dialog")).toBeVisible()

    await page.getByLabel("配置名称").fill(configName)
    // Provider type defaults to Kimi — leave as-is
    await page.getByLabel("模型 ID").fill("moonshot-v1-32k")
    await page.getByLabel("API Key").fill("sk-test-e2e-kimi-key")
    await page.getByRole("button", { name: "保存" }).click()

    await expect(page.getByText("模型配置已创建")).toBeVisible()
    await expect(page.getByText(configName)).toBeVisible()
  })

  test("Create an OpenAI-compatible model config", async ({ page }) => {
    const configName = randomConfigName()

    await page.getByRole("button", { name: "新建配置" }).click()
    await expect(page.getByRole("dialog")).toBeVisible()

    await page.getByLabel("配置名称").fill(configName)

    // Switch to openai_compatible
    await page.getByRole("combobox").first().click()
    await page.getByRole("option", { name: "OpenAI 兼容格式" }).click()

    // Base URL should now be visible
    await page.getByLabel("Base URL").fill("https://api.groq.com/openai/v1")
    await page.getByLabel("模型 ID").fill("mixtral-8x7b-32768")
    await page.getByLabel("API Key").fill("gsk_test_key")
    await page.getByRole("button", { name: "保存" }).click()

    await expect(page.getByText("模型配置已创建")).toBeVisible()
    await expect(page.getByText(configName)).toBeVisible()
  })

  test("Edit a model config", async ({ page }) => {
    const configName = randomConfigName()

    // Create first
    await page.getByRole("button", { name: "新建配置" }).click()
    await page.getByLabel("配置名称").fill(configName)
    await page.getByLabel("模型 ID").fill("moonshot-v1-8k")
    await page.getByLabel("API Key").fill("sk-edit-test-key")
    await page.getByRole("button", { name: "保存" }).click()
    await expect(page.getByText("模型配置已创建")).toBeVisible()

    // Edit the row
    const row = page.getByRole("row").filter({ hasText: configName })
    await row.getByRole("button").first().click() // edit icon

    await expect(page.getByRole("dialog")).toBeVisible()
    await page.getByLabel("模型 ID").fill("moonshot-v1-32k")
    await page.getByRole("button", { name: "保存" }).click()

    await expect(page.getByText("模型配置已更新")).toBeVisible()
  })

  test("Delete a model config", async ({ page }) => {
    const configName = randomConfigName()

    // Create first
    await page.getByRole("button", { name: "新建配置" }).click()
    await page.getByLabel("配置名称").fill(configName)
    await page.getByLabel("模型 ID").fill("moonshot-v1-32k")
    await page.getByLabel("API Key").fill("sk-delete-test-key")
    await page.getByRole("button", { name: "保存" }).click()
    await expect(page.getByText("模型配置已创建")).toBeVisible()

    // Delete — accept native confirm dialog
    const row = page.getByRole("row").filter({ hasText: configName })
    page.once("dialog", (dialog) => dialog.accept())
    await row.getByRole("button").last().click() // trash icon

    await expect(page.getByText("模型配置已删除")).toBeVisible()
    await expect(page.getByText(configName)).not.toBeVisible()
  })

  test("API key is masked in the table", async ({ page }) => {
    const configName = randomConfigName()
    const secretKey = "sk-super-secret-api-key-1234567890"

    await page.getByRole("button", { name: "新建配置" }).click()
    await page.getByLabel("配置名称").fill(configName)
    await page.getByLabel("模型 ID").fill("moonshot-v1-32k")
    await page.getByLabel("API Key").fill(secretKey)
    await page.getByRole("button", { name: "保存" }).click()
    await expect(page.getByText("模型配置已创建")).toBeVisible()

    // The full key must not be visible anywhere on the page
    await expect(page.getByText(secretKey)).not.toBeVisible()
    // But a masked version (with ***) should be shown
    const row = page.getByRole("row").filter({ hasText: configName })
    await expect(row.getByText(/\*\*\*/)).toBeVisible()
  })
})
