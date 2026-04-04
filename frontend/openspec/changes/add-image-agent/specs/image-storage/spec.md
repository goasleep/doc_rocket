## ADDED Requirements

### Requirement: Generated image metadata model
The system SHALL define a GeneratedImage model to store image metadata.

#### Scenario: Image metadata structure
- **WHEN** an image is generated
- **THEN** the system SHALL store: id, prompt, url, position, created_at
- **AND** the metadata SHALL be associated with the WorkflowRun

### Requirement: WorkflowRun image extension
The system SHALL extend WorkflowRun model to support generated images.

#### Scenario: Store multiple images
- **WHEN** a workflow generates multiple images
- **THEN** WorkflowRun SHALL store them as a list of GeneratedImage objects
- **AND** the field SHALL be optional for backward compatibility

#### Scenario: Retrieve workflow images
- **WHEN** fetching a WorkflowRun
- **THEN** the response SHALL include the generated_images array
- **AND** each image SHALL have a public accessible URL
