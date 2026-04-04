## ADDED Requirements

### Requirement: ImageAgent class implementation
The system SHALL provide an ImageAgent class that generates images based on article content.

#### Scenario: ImageAgent initialization
- **WHEN** the system initializes ImageAgent with an AgentConfig
- **THEN** ImageAgent SHALL load the configured image generation provider

#### Scenario: Generate image from content
- **WHEN** ImageAgent receives an article content and image requirements
- **THEN** ImageAgent SHALL analyze the content and generate optimized prompts
- **AND** call the image generation provider to create images
- **AND** upload generated images to OSS storage
- **AND** return image metadata including URL and prompt

### Requirement: Image generation provider interface
The system SHALL define an abstract ImageGenerator interface with a placeholder implementation.

#### Scenario: Provider interface definition
- **WHEN** a new image service needs to be integrated
- **THEN** the developer SHALL implement the ImageGenerator interface with `generate(prompt: str) -> bytes` method

#### Scenario: Placeholder provider behavior
- **WHEN** ImageAgent uses the placeholder provider
- **THEN** it SHALL return a mock image URL for testing purposes
- **AND** log a warning that no real image service is configured

### Requirement: Image prompt optimization
The system SHALL optimize user content into effective image generation prompts.

#### Scenario: Chinese to English prompt translation
- **WHEN** article content is in Chinese
- **THEN** ImageAgent SHALL translate key concepts into English prompts
- **AND** add style modifiers for better image quality

#### Scenario: Content analysis for image relevance
- **WHEN** generating prompts from article content
- **THEN** ImageAgent SHALL identify key visual concepts and scenes
- **AND** exclude abstract or non-visual content from prompts

### Requirement: Image storage integration
The system SHALL integrate with Qiniu OSS for image storage.

#### Scenario: Upload generated image
- **WHEN** an image is successfully generated
- **THEN** ImageAgent SHALL upload the image bytes to Qiniu OSS
- **AND** return the public URL

#### Scenario: Handle upload failure
- **WHEN** OSS upload fails
- **THEN** ImageAgent SHALL retry up to 3 times
- **AND** return an error if all retries fail
