## ADDED Requirements

### Requirement: Agent list page displays token consumption cards
The system SHALL display token consumption statistics on the Agent management page (`/agents`), showing today's and yesterday's total token usage across all agents, with breakdown by agent if space permits.

#### Scenario: Agent page shows today's token usage
- **WHEN** user navigates to the Agent management page
- **THEN** a card displays "今日 Token 消耗" with the total tokens consumed today

#### Scenario: Agent page shows yesterday's comparison
- **WHEN** user views the Agent management page
- **THEN** a card displays "昨日 Token 消耗" allowing comparison with today's usage

#### Scenario: Token stats refresh on page load
- **WHEN** the Agent page loads
- **THEN** it fetches fresh token usage data from `/api/v1/token-usage/agents` endpoint

### Requirement: Article detail page displays token usage breakdown
The system SHALL display token consumption details on the Article detail page, showing total tokens consumed for this article and breakdown by operation (refine, analyze, rewrite).

#### Scenario: Article detail shows total token consumption
- **WHEN** user views an article's detail page
- **THEN** a section displays "Token 消耗总计" with the sum of all operations

#### Scenario: Article detail shows operation breakdown
- **WHEN** user views an article's detail page
- **THEN** a list shows each operation type (精修、分析) with its token consumption

#### Scenario: Article detail shows model information
- **WHEN** user views the token breakdown
- **THEN** each operation displays the model name used (e.g., "kimi-k1.5", "gpt-4o")

### Requirement: Token usage components use existing design system
The system SHALL use existing UI components from the project's component library (shadcn/ui patterns) for displaying token statistics, including Cards, Badges, and Data Tables.

#### Scenario: Token stats use Card component
- **WHEN** token usage is displayed
- **THEN** it uses the Card component with appropriate header and content styling

#### Scenario: Token numbers are formatted for readability
- **WHEN** large token numbers are displayed
- **THEN** they are formatted with thousand separators (e.g., "15,234" instead of "15234")

### Requirement: Token usage data fetches via TanStack Query
The system SHALL use TanStack Query (React Query) for fetching token usage data, with appropriate caching, loading states, and error handling.

#### Scenario: Token stats show loading state
- **WHEN** token usage data is being fetched
- **THEN** a loading skeleton or spinner is displayed

#### Scenario: Token stats handle fetch errors gracefully
- **WHEN** the token usage API returns an error
- **THEN** an error message is displayed and a retry option is available

### Requirement: Chrome DevTools validates frontend implementation
The system SHALL be validated using Chrome DevTools MCP for accessibility, performance, and responsive design testing of token usage UI components.

#### Scenario: Token usage cards pass accessibility audit
- **WHEN** Chrome DevTools Lighthouse accessibility audit runs on Agent page
- **THEN** it passes with no critical accessibility violations

#### Scenario: Token usage components are responsive
- **WHEN** Chrome DevTools device emulation tests mobile viewport
- **THEN** token usage cards stack properly and remain readable

### Requirement: Token usage trend charts
The system SHALL provide interactive charts for visualizing token consumption trends over time, including line charts for daily trends and bar charts for agent/model comparisons.

#### Scenario: Agent page displays 7-day token trend chart
- **WHEN** user views the Agent management page
- **THEN** a line chart displays daily token consumption for the past 7 days

#### Scenario: Chart shows agent breakdown by color
- **WHEN** viewing the token trend chart
- **THEN** each agent is represented by a different colored line with a legend

#### Scenario: Chart supports time range selection
- **WHEN** user selects a different time range (7d/30d/90d)
- **THEN** the chart updates to show data for the selected period

#### Scenario: Article detail shows operation distribution pie chart
- **WHEN** user views an article's detail page
- **THEN** a pie or donut chart shows the proportion of tokens consumed by each operation (refine/analyze/rewrite)

#### Scenario: Charts use consistent color scheme
- **WHEN** charts are displayed
- **THEN** they use the application's design system colors (Tailwind palette)

#### Scenario: Charts are interactive with tooltips
- **WHEN** user hovers over chart data points
- **THEN** a tooltip displays the exact date, agent/model name, and token count
