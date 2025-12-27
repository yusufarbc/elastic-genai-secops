# Threat Hunting Mastery

## Scenario: Ransomware Simulation

This scenario guides you through detecting and responding to a simulated ransomware attack.

### 1. Simulation
- Use the `infrastructure/scripts` to trigger a safe ransomware simulation (e.g., bulk file encryption in a test directory).

### 2. Detection
- **Query**: Use KQL in Kibana Discover:
  ```kql
  event.action: "file_create" and file.extension: "encrypted"
  ```
- **Analyze**: Look for high-frequency file modifications within a short time window.

### 3. Response
- Isolate the affected host using the EDR capabilities (if configured).
- Use the GenAI insights to understand the specific strain and recommended cleanup steps.
