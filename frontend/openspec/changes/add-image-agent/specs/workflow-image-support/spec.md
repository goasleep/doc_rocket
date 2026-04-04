## ADDED Requirements

### Requirement: Frontend image display
The system SHALL display generated images in the workflow detail page.

#### Scenario: Display single image
- **WHEN** a workflow has one generated image
- **THEN** the frontend SHALL display it prominently in the workflow result section

#### Scenario: Display multiple images
- **WHEN** a workflow has multiple generated images
- **THEN** the frontend SHALL display them in a grid layout
- **AND** each image SHALL be clickable to view full size

#### Scenario: Show image metadata
- **WHEN** user clicks on an image
- **THEN** the system SHALL show a modal with the image and its generation prompt

### Requirement: Workflow list image indicator
The system SHALL indicate in the workflow list if a workflow has generated images.

#### Scenario: Image count badge
- **WHEN** viewing the workflow list
- **THEN** workflows with images SHALL display an image icon with count

### Requirement: Agent configuration support
The system SHALL support configuring ImageAgent in the agent settings page.

#### Scenario: Add ImageAgent configuration
- **WHEN** admin creates a new AgentConfig with role="image"
- **THEN** the system SHALL accept and store the configuration
- **AND** the ImageAgent SHALL be available for workflow orchestration
