import { expect, test } from "@playwright/test"

const randomSkillName = () =>
  `skill-${Date.now()}-${Math.random().toString(36).substring(7)}`

test("Skills page is accessible and shows correct heading", async ({
  page,
}) => {
  await page.goto("/skills")
  await expect(page.getByRole("heading", { name: "技能库" })).toBeVisible()
})

test("新建 Skill button is visible", async ({ page }) => {
  await page.goto("/skills")
  await expect(page.getByRole("button", { name: "新建 Skill" })).toBeVisible()
  await expect(
    page.getByRole("button", { name: "导入 SKILL.md" }),
  ).toBeVisible()
})

test.describe("Skills management", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto("/skills")
  })

  test("Create a new skill successfully", async ({ page }) => {
    const skillName = randomSkillName()

    await page.getByRole("button", { name: "新建 Skill" }).click()
    await page.getByLabel("名称").fill(skillName)
    await page.getByLabel("描述").fill("Test skill description")
    await page.getByLabel("内容").fill("## Test body\nSome content")
    // submit button in create dialog is labeled "创建"
    await page.getByRole("button", { name: "创建", exact: true }).click()

    await expect(page.getByText("技能已创建")).toBeVisible()
    await expect(page.getByText(skillName)).toBeVisible()
  })

  test("Import a skill from SKILL.md content", async ({ page }) => {
    const timestamp = Date.now()
    const importedSkillName = `e2e-test-imported-skill-${timestamp}`

    const skillMdContent = `---
name: ${importedSkillName}
description: E2E test import.
---
## Body
Test imported body.`

    await page.getByRole("button", { name: "导入 SKILL.md" }).click()
    await expect(page.getByText("粘贴内容")).toBeVisible()
    // use label to target the correct textarea
    await page.getByLabel("SKILL.md 内容").fill(skillMdContent)
    // exact: true to avoid matching the "URL 导入" tab button
    await page.getByRole("button", { name: "导入", exact: true }).click()

    await expect(page.getByText("技能导入成功")).toBeVisible()
  })

  test("Delete a skill", async ({ page }) => {
    const skillName = randomSkillName()

    // First create a skill
    await page.getByRole("button", { name: "新建 Skill" }).click()
    await page.getByLabel("名称").fill(skillName)
    await page.getByLabel("描述").fill("Skill to be deleted")
    await page.getByLabel("内容").fill("## Delete me")
    await page.getByRole("button", { name: "创建", exact: true }).click()
    await expect(page.getByText("技能已创建")).toBeVisible()

    // Accept the native confirm() dialog before clicking delete
    const skillRow = page.getByRole("row").filter({ hasText: skillName })
    page.once("dialog", (dialog) => dialog.accept())
    await skillRow.getByRole("button", { name: "删除" }).click()

    await expect(page.getByText("技能已删除")).toBeVisible()
  })
})
