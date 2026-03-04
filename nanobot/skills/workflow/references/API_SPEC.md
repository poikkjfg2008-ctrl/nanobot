# Workflow API Specification

Complete reference for workflow data structures and API contracts.

## Function Signatures

### runworkflow(user_input: str) -> str

**Input:**
- `user_input` (string, required): Natural language description of the analysis task

**Returns:**
- `run_id` (string): Unique identifier for this workflow execution

**Example:**
```python
run_id = runworkflow("Compare Q1 and Q2 sales by region")
# Returns: "mock_1234567890123"
```

---

### getflowinfo(run_id: str) -> dict

**Input:**
- `run_id` (string, required): Workflow identifier

**Returns:** Dictionary with the following structure

#### Complete Response Schema

```json
{
  "runId": "string (required) - Workflow identifier",
  "status": "string (required) - processing|interrupted|success|fail",
  "workflowType": "string (optional) - comparison|outlier_detection|controlled_analysis|general",
  "userInput": "string (optional) - Original user input",

  "nodes": {
    "node_id": {
      "input": {...},
      "output": {...},
      "status": "pending|processing|success|interrupted|fail",
      "costMs": 123,
      "nodeType": "start|flow|condition|end"
    }
  },

  "steps": ["node_id_1", "node_id_2", "..."],

  "costMs": 1000,

  "createdAt": "2026-03-03T12:00:00",

  // When status = success
  "output": {
    "summary": "Human-readable conclusion",
    "details": {
      "comparison": {...},
      "outliers": [...],
      "controlled_analysis": {...},
      "recommendation": [...]
    }
  },

  // When status = interrupted
  "lastInterruptedNodeId": "node_id",
  "checkpointExpireTimestamp": 1736000000000,
  "msg": "请补充分析的时间范围（例如：Q1、Q2、或具体月份）",

  // When status = fail
  "error": "Error message describing what went wrong"
}
```

#### Status Values

| Status | Description | Next Action |
|--------|-------------|-------------|
| `processing` | Workflow is actively running | Continue polling after interval |
| `interrupted` | Workflow needs user input | Call `resumeflow(user_input, run_id)` |
| `success` | Workflow completed successfully | Extract `output` field |
| `fail` | Workflow encountered error | Display `error` message |

#### Node Status Values

| Status | Description |
|--------|-------------|
| `pending` | Node has not started |
| `processing` | Node is currently executing |
| `success` | Node completed successfully |
| `interrupted` | Node was interrupted (awaiting input) |
| `fail` | Node encountered an error |

#### Node Types

| Type | Description |
|------|-------------|
| `start` | Workflow entry point |
| `flow` | Standard processing node |
| `condition` | Branching logic node |
| `end` | Workflow termination point |

---

### resumeflow(user_input: str, run_id: str) -> None

**Input:**
- `user_input` (string, required): Additional information to resume workflow
- `run_id` (string, required): Workflow identifier to resume

**Returns:** None (void)

**Prerequisites:**
- Workflow must be in `interrupted` status
- `run_id` must be valid
- Must resume before `checkpointExpireTimestamp`

**Example:**
```python
resumeflow("Q1 2024", "mock_1234567890123")
# Workflow resumes and continues processing
```

---

## Output Structure Details

### Comparison Analysis Output

```json
{
  "summary": "基于对比分析，Q2相比Q1增长15%，主要来自华东区域。",
  "details": {
    "comparison": {
      "period1": "Q1",
      "period2": "Q2",
      "change_rate": "+15%",
      "regions": {
        "华东": "+22%",
        "华南": "+8%",
        "华北": "+12%"
      }
    },
    "outliers": [...],
    "controlled_analysis": {...},
    "recommendation": [
      "加大华东区域投入",
      "调查华南区域增长缓慢原因"
    ]
  }
}
```

### Outlier Detection Output

```json
{
  "summary": "在数据集中识别出5个异常值，主要集中在A品类和B渠道。",
  "details": {
    "comparison": {},
    "outliers": [
      {
        "id": 1,
        "value": 98000,
        "expected": 45000,
        "deviation": "4.1σ",
        "reason": "Promotional event"
      },
      {
        "id": 2,
        "value": 12000,
        "expected": 38000,
        "deviation": "-3.5σ",
        "reason": "Stockout"
      }
    ],
    "controlled_analysis": {},
    "recommendation": [
      "验证促销活动效果",
      "补货B渠道"
    ]
  }
}
```

### Controlled Variable Analysis Output

```json
{
  "summary": "通过控制变量分析，发现价格调整对销量影响显著（-12%），但地区因素控制后影响为-8%。",
  "details": {
    "comparison": {
      "raw_correlation": "-12%",
      "controlled_correlation": "-8%",
      "controlled_variables": ["region", "season", "channel"]
    },
    "outliers": [],
    "controlled_analysis": {
      "method": "multiple_regression",
      "r_squared": 0.87,
      "significant_factors": ["price", "promotion", "season"]
    },
    "recommendation": [
      "价格调整需谨慎，综合考虑地区因素",
      "加强促销活动配合"
    ]
  }
}
```

---

## Error Codes

| Error | Description | Recovery |
|-------|-------------|----------|
| `Workflow not found` | Invalid run_id | Verify run_id or start new workflow |
| `Workflow not interrupted` | Cannot resume non-interrupted workflow | Check status first with getflowinfo |
| `Checkpoint expired` | Too long since interruption | Start new workflow |
| `Invalid input` | Missing or malformed parameters | Provide valid input |
| `Backend error` | Internal workflow service error | Retry or escalate |

---

## Performance Characteristics

### Expected Latency

| Operation | Typical | Max |
|-----------|---------|-----|
| runworkflow | 100-500ms | 2s |
| getflowinfo | 50-200ms | 1s |
| resumeflow | 100-500ms | 2s |

### Polling Recommendations

- **Initial interval**: 2 seconds
- **Backoff strategy**: Increase by 1s every 10 polls, max 10s
- **Timeout**: 5 minutes for most workflows
- **Long-running workflows**: May take up to 30 minutes for complex analyses

### Idempotency

- `runworkflow`: Safe to retry on same input
- `getflowinfo`: Always idempotent
- `resumeflow`: NOT idempotent - only call once per interruption

---

## Implementation Notes

### Thread Safety

All functions are thread-safe and can be called concurrently with different run_ids.

### Persistence

Workflow state is persisted to disk and survives process restarts:
- Location: `~/.nanobot/workspace/workflow_mock/`
- Format: JSON files named `{run_id}.json`
- Cleanup: Manual deletion required

### Mock vs Real Backend

Switch between mock and real backend via environment variable:

```bash
# Mock (default)
export WORKFLOW_BACKEND=mock

# Real backend
export WORKFLOW_BACKEND=external
export WORKFLOW_EXTERNAL_MODULE=external_workflow
export WORKFLOW_EXTERNAL_RUN_FUNC=runworkflow
export WORKFLOW_EXTERNAL_INFO_FUNC=getflowinfo
export WORKFLOW_EXTERNAL_RESUME_FUNC=resumeflow
```

### Checkpoint Expiration

Interrupted workflows expire after 1 hour by default. Configure via:

```python
checkpoint_expire_hours = 1  # Default
```
