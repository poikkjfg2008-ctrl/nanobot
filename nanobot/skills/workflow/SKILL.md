---
name: workflow
description: "Orchestrate data analysis workflows with runworkflow, getflowinfo, and resumeflow. Use for: (1) Starting new analysis workflows, (2) Checking workflow status and progress, (3) Resuming interrupted workflows with additional input. Ideal for multi-step data analysis tasks like comparison, outlier detection, and controlled variable analysis."
---

# Workflow Skill

Interact with the workflow orchestration system to execute, monitor, and resume data analysis workflows.

## Core Functions

### runworkflow(user_input: str) -> str
Start a new workflow execution with user's natural language input.

**Returns**: `run_id` (string) - Unique identifier for tracking this workflow

**Use when**:
- User requests data analysis (comparison, outlier detection, controlled variables)
- Starting a new multi-step analysis task
- Beginning a workflow that may require intermediate user input

### getflowinfo(run_id: str) -> dict
Query the current status, progress, and output of a workflow.

**Returns**: Dictionary with workflow state:
- `status`: "processing" | "interrupted" | "success" | "fail"
- `nodes`: Node-level progress and results
- `output`: Final results (when status=success)
- `msg`: Interruption message (when status=interrupted)
- `error`: Error details (when status=fail)

**Use when**:
- Checking workflow progress
- Retrieving analysis results
- Understanding why a workflow was interrupted

### resumeflow(user_input: str, run_id: str) -> None
Resume an interrupted workflow with additional user input.

**Use when**:
- Workflow status is "interrupted"
- User needs to provide clarification or missing parameters
- System asks for additional analysis dimensions

## Typical Workflow Patterns

### Pattern 1: Fire-and-Forget Analysis
```bash
# Start workflow
run_id=$(runworkflow "Compare Q1 and Q2 sales by region")

# Poll for completion
while true; do
  info=$(getflowinfo "$run_id")
  status=$(echo "$info" | jq -r '.status')

  if [ "$status" = "success" ]; then
    echo "$info" | jq -r '.output'
    break
  elif [ "$status" = "fail" ]; then
    echo "Error: $(echo "$info" | jq -r '.error')"
    break
  fi

  sleep 2
done
```

### Pattern 2: Interactive Workflow with Interruptions
```bash
# Start workflow
run_id=$(runworkflow "Analyze sales outliers")

# Poll and handle interruptions
while true; do
  info=$(getflowinfo "$run_id")
  status=$(echo "$info" | jq -r '.status')

  if [ "$status" = "interrupted" ]; then
    msg=$(echo "$info" | jq -r '.msg')
    echo "Workflow interrupted: $msg"

    # Get user input and resume
    read -p "Please provide: " user_input
    resumeflow "$user_input" "$run_id"
  elif [ "$status" = "success" ]; then
    echo "$info" | jq -r '.output'
    break
  elif [ "$status" = "fail" ]; then
    echo "Error: $(echo "$info" | jq -r '.error')"
    break
  fi

  sleep 2
done
```

### Pattern 3: Background Execution
```bash
# Start workflow in background
run_id=$(runworkflow "Full Q3 analysis")
echo "Workflow started: $run_id"

# Check later
info=$(getflowinfo "$run_id")
echo "$info" | jq -r '.output.summary'
```

## Common Analysis Types

### Data Comparison
- Period-over-period analysis (QoQ, YoY)
- Regional comparisons
- Category performance comparison
- Channel effectiveness analysis

**Example**: `runworkflow "Compare Q1 vs Q2 sales by region and category"`

### Outlier Detection
- IQR method for basic outliers
- Z-score for standard deviation outliers
- Isolation Forest for complex patterns

**Example**: `runworkflow "Identify outlier transactions in Q3 sales data"`

### Controlled Variable Analysis
- Fix variables (region, time, channel)
- Isolate impact of specific factors
- Attribute differences to root causes

**Example**: `runworkflow "Analyze impact of price changes while controlling for seasonality"`

## Status Handling

### processing
Workflow is still running. Continue polling.

**Action**: Wait and poll again after interval (2-5 seconds).

### interrupted
Workflow needs user input to continue.

**Action**:
1. Extract `msg` from response
2. Prompt user for required information
3. Call `resumeflow(user_input, run_id)`
4. Resume polling

### success
Workflow completed successfully.

**Action**: Extract and display `output.summary` and `output.details`.

### fail
Workflow encountered an error.

**Action**: Display `error` message to user and suggest alternatives.

## Output Structure

When `status=success`, the output contains:

```json
{
  "summary": "Human-readable conclusion",
  "details": {
    "comparison": {...},
    "outliers": [...],
    "controlled_analysis": {...},
    "recommendation": [...]
  }
}
```

## Best Practices

1. **Always save run_id**: Keep track of run_id for later queries
2. **Handle all statuses**: Don't assume success; handle interrupted and fail cases
3. **Poll with backoff**: Start with 2s interval, increase if workflow runs long
4. **Checkpoints**: Interrupted workflows have `checkpointExpireTimestamp` - resume before expiry
5. **Idempotency**: `runworkflow` can be safely retried on failure
6. **Logging**: Log `run_id`, `status`, and `costMs` for debugging

## Error Recovery

### Timeout on runworkflow
- Check if `run_id` was returned
- If yes, use `getflowinfo` to check status
- If no, retry with same input (idempotent)

### Stuck in processing
- Verify `run_id` is correct
- Check if workflow service is responsive
- May indicate backend issue - escalate

### Invalid run_id on resumeflow
- Verify run_id matches the interrupted workflow
- Check `checkpointExpireTimestamp` - may have expired
- Start new workflow if expired

## Integration with exec Tool

Use `exec` tool to call workflow scripts:

```bash
# Start workflow
exec("python scripts/run_workflow.py 'Analyze Q3 sales'")

# Check status
exec("python scripts/get_workflow_info.py <run_id>")

# Resume workflow
exec("python scripts/resume_workflow.py '<user_input>' <run_id>")
```

## Reference Documentation

- See [references/API_SPEC.md](references/API_SPEC.md) for complete data structures
- See [references/EXAMPLES.md](references/EXAMPLES.md) for detailed usage examples
