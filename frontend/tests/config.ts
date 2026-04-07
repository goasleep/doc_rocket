import path from "node:path"
import { fileURLToPath } from "node:url"
import dotenv from "dotenv"

const __filename = fileURLToPath(import.meta.url)
const __dirname = path.dirname(__filename)

dotenv.config({ path: path.join(__dirname, "../../.env") })

function getEnvVar(name: string): string {
  const value = process.env[name]
  if (value) {
    return value
  }
  // Fallback defaults for the project template so tests can run inside
  // containers where the root .env file is not mounted.
  if (name === "FIRST_SUPERUSER") return "admin@example.com"
  if (name === "FIRST_SUPERUSER_PASSWORD") return "changethis"
  throw new Error(`Environment variable ${name} is undefined`)
}

export const firstSuperuser = getEnvVar("FIRST_SUPERUSER")
export const firstSuperuserPassword = getEnvVar("FIRST_SUPERUSER_PASSWORD")
