# Workflow Usage Examples

Practical examples demonstrating common workflow patterns and use cases.

## Example 1: Simple Comparison Analysis

```bash
# Start workflow
run_id=$(python scripts/run_workflow.py "Compare Q1 and Q2 sales by region")
echo "Started: $run_id"

# Poll for completion
while true; do
  info=$(python scripts/get_workflow_info.py "$run_id")
  status=$(echo "$info" | jq -r '.status')

  if [ "$status" = "success" ]; then
    echo "$info" | jq -r '.output.summary'
    break
  elif [ "$status" = "interrupted" ]; then
    msg=$(echo "$info" | jq -r '.msg')
    echo "Interrupted: $msg"
    read -p "Provide input: " user_input
    python scripts/resume_workflow.py "$user_input" "$run_id"
  elif [ "$status" = "fail" ]; then
    echo "Error: $(echo "$info" | jq -r '.error')"
    break
  fi

  sleep 2
done
```

## Example 2: Outlier Detection with Interruption Handling

```bash
#!/bin/bash
# outlier_analysis.sh

input="Identify outlier transactions in Q3 sales data"
run_id=$(python scripts/run_workflow.py "$input")

echo "Analyzing outliers... (ID: $run_id)"

while true; do
  info=$(python scripts/get_workflow_info.py "$run_id")
  status=$(echo "$info" | jq -r '.status')

  case $status in
    success)
      echo "Analysis complete!"
      echo "Summary: $(echo "$info" | jq -r '.output.summary')"
      echo ""
      echo "Outliers found:"
      echo "$info" | jq -r '.output.details.outliers[] | "\(.id): \$.value (expected \(.expected), \(.deviation))"'
      break
      ;;

    interrupted)
      msg=$(echo "$info" | jq -r '.msg')
      echo "Need input: $msg"
      read -p "Enter time range: " time_range
      python scripts/resume_workflow.py "$time_range" "$run_id"
      ;;

    fail)
      echo "Analysis failed: $(echo "$info" | jq -r '.error')"
      exit 1
      ;;

    processing)
      echo "Still processing..."
      sleep 3
      ;;
  esac
done
```

## Example 3: Controlled Variable Analysis

```python
#!/usr/bin/env python3
# controlled_analysis.py

import subprocess
import json
import time

def run_cmd(cmd):
    """Run shell command and return output."""
    result = subprocess.run(cmd, capture_output=True, text=True, shell=True)
    return result.stdout.strip()

def main():
    # Start controlled analysis
    user_input = "Analyze price impact while controlling for seasonality and region"
    run_id = run_cmd(f"python scripts/run_workflow.py '{user_input}'")
    print(f"Started: {run_id}")

    # Poll with backoff
    interval = 2
    max_interval = 10

    while True:
        info_json = run_cmd(f"python scripts/get_workflow_info.py {run_id}")
        info = json.loads(info_json)
        status = info['status']

        if status == 'success':
            output = info['output']
            print("\n=== Analysis Results ===")
            print(f"Summary: {output['summary']}\n")

            if 'comparison' in output['details']:
                comp = output['details']['comparison']
                print("Comparison:")
                print(f"  Raw correlation: {comp.get('raw_correlation', 'N/A')}")
                print(f"  Controlled correlation: {comp.get('controlled_correlation', 'N/A')}")
                print(f"  Controlled variables: {', '.join(comp.get('controlled_variables', []))}")

            if 'controlled_analysis' in output['details']:
                ca = output['details']['controlled_analysis']
                print("\nControlled Analysis:")
                print(f"  Method: {ca.get('method', 'N/A')}")
                print(f"  R²: {ca.get('r_squared', 'N/A')}")
                print(f"  Significant factors: {', '.join(ca.get('significant_factors', []))}")

            print("\nRecommendations:")
            for i, rec in enumerate(output['details'].get('recommendation', []), 1):
                print(f"  {i}. {rec}")

            break

        elif status == 'interrupted':
            msg = info.get('msg', 'Please provide additional information')
            print(f"\nInterrupted: {msg}")
            user_input = input("Your response: ")
            run_cmd(f"python scripts/resume_workflow.py '{user_input}' {run_id}")
            print("Resuming...")

        elif status == 'fail':
            error = info.get('error', 'Unknown error')
            print(f"\nFailed: {error}")
            break

        else:
            print(f"Processing... (waiting {interval}s)")
            time.sleep(interval)
            interval = min(interval + 1, max_interval)

if __name__ == "__main__":
    main()
```

## Example 4: Batch Processing Multiple Analyses

```python
#!/usr/bin/env python3
# batch_analysis.py

import subprocess
import json
from concurrent.futures import ThreadPoolExecutor, as_completed

def start_workflow(input_text):
    """Start a workflow and return run_id."""
    cmd = f"python scripts/run_workflow.py '{input_text}'"
    result = subprocess.run(cmd, capture_output=True, text=True, shell=True)
    return result.stdout.strip()

def get_workflow_status(run_id):
    """Get workflow status."""
    cmd = f"python scripts/get_workflow_info.py {run_id}"
    result = subprocess.run(cmd, capture_output=True, text=True, shell=True)
    return json.loads(result.stdout)

def run_analysis(analysis_config):
    """Run a single analysis to completion."""
    name = analysis_config['name']
    input_text = analysis_config['input']

    print(f"[{name}] Starting...")

    # Start workflow
    run_id = start_workflow(input_text)
    print(f"[{name}] Started: {run_id}")

    # Poll for completion
    while True:
        info = get_workflow_status(run_id)
        status = info['status']

        if status == 'success':
            print(f"[{name}] Complete!")
            return {
                'name': name,
                'run_id': run_id,
                'status': 'success',
                'summary': info['output']['summary']
            }

        elif status == 'fail':
            print(f"[{name}] Failed: {info.get('error', 'Unknown')}")
            return {
                'name': name,
                'run_id': run_id,
                'status': 'fail',
                'error': info.get('error')
            }

def main():
    analyses = [
        {
            'name': 'Q1-Q2 Comparison',
            'input': 'Compare Q1 and Q2 sales by region and category'
        },
        {
            'name': 'Outlier Detection',
            'input': 'Identify outlier transactions in Q3'
        },
        {
            'name': 'Price Impact Analysis',
            'input': 'Analyze price impact controlling for seasonality'
        }
    ]

    print("=== Batch Analysis ===\n")

    # Run in parallel
    with ThreadPoolExecutor(max_workers=3) as executor:
        futures = {executor.submit(run_analysis, config): config['name']
                   for config in analyses}

        results = []
        for future in as_completed(futures):
            name = futures[future]
            try:
                result = future.result()
                results.append(result)
            except Exception as e:
                print(f"[{name}] Error: {e}")
                results.append({'name': name, 'status': 'error', 'error': str(e)})

    # Summary
    print("\n=== Batch Summary ===")
    for result in results:
        status_icon = "✓" if result['status'] == 'success' else "✗"
        print(f"{status_icon} {result['name']}: {result['status']}")
        if 'summary' in result:
            print(f"  {result['summary']}")
        if 'error' in result:
            print(f"  Error: {result['error']}")

if __name__ == "__main__":
    main()
```

## Example 5: Interactive CLI Tool

```python
#!/usr/bin/env python3
# workflow_cli.py

import subprocess
import json
import sys

class WorkflowCLI:
    def __init__(self):
        self.current_run_id = None

    def run(self, user_input):
        """Start a new workflow."""
        cmd = f"python scripts/run_workflow.py '{user_input}'"
        result = subprocess.run(cmd, capture_output=True, text=True, shell=True)
        self.current_run_id = result.stdout.strip()
        print(f"✓ Workflow started: {self.current_run_id}")
        return self.current_run_id

    def status(self):
        """Check current workflow status."""
        if not self.current_run_id:
            print("No active workflow. Use 'run' command first.")
            return

        cmd = f"python scripts/get_workflow_info.py {self.current_run_id}"
        result = subprocess.run(cmd, capture_output=True, text=True, shell=True)
        info = json.loads(result.stdout)

        print(f"\nWorkflow: {self.current_run_id}")
        print(f"Status: {info['status']}")

        if info['status'] == 'processing':
            nodes = info.get('nodes', {})
            completed = sum(1 for n in nodes.values() if n['status'] == 'success')
            total = len(nodes)
            print(f"Progress: {completed}/{total} nodes complete")

        elif info['status'] == 'interrupted':
            print(f"Message: {info.get('msg', 'No message')}")
            print(f"Expires: {info.get('checkpointExpireTimestamp', 'N/A')}")

        elif info['status'] == 'success':
            print(f"\nSummary: {info['output']['summary']}")

        elif info['status'] == 'fail':
            print(f"Error: {info.get('error', 'Unknown error')}")

    def resume(self, user_input):
        """Resume interrupted workflow."""
        if not self.current_run_id:
            print("No active workflow to resume.")
            return

        cmd = f"python scripts/resume_workflow.py '{user_input}' {self.current_run_id}"
        subprocess.run(cmd, shell=True)
        print(f"✓ Workflow resumed")

    def wait(self, interval=2):
        """Wait for workflow completion."""
        if not self.current_run_id:
            print("No active workflow.")
            return

        print("Waiting for completion...")

        while True:
            cmd = f"python scripts/get_workflow_info.py {self.current_run_id}"
            result = subprocess.run(cmd, capture_output=True, text=True, shell=True)
            info = json.loads(result.stdout)

            if info['status'] in ['success', 'fail']:
                self.status()
                break

            print(f"  {info['status']}... (waiting {interval}s)")
            import time
            time.sleep(interval)

def main():
    cli = WorkflowCLI()

    if len(sys.argv) < 2:
        print("Usage: python workflow_cli.py <command> [args...]")
        print("\nCommands:")
        print("  run '<input>'        - Start new workflow")
        print("  status               - Check workflow status")
        print("  resume '<input>'     - Resume interrupted workflow")
        print("  wait [interval]      - Wait for completion (default: 2s)")
        sys.exit(1)

    command = sys.argv[1]

    if command == 'run' and len(sys.argv) > 2:
        user_input = ' '.join(sys.argv[2:])
        cli.run(user_input)

    elif command == 'status':
        cli.status()

    elif command == 'resume' and len(sys.argv) > 2:
        user_input = ' '.join(sys.argv[2:])
        cli.resume(user_input)

    elif command == 'wait':
        interval = int(sys.argv[2]) if len(sys.argv) > 2 else 2
        cli.wait(interval)

    else:
        print(f"Unknown command: {command}")
        sys.exit(1)

if __name__ == "__main__":
    main()
```

## Example 6: Integration with Nanobot

```python
# In your nanobot tool or skill:

from pathlib import Path
import subprocess

def run_workflow_analysis(user_input: str) -> str:
    """Execute workflow and return results."""
    script_path = Path.home() / "nanobot/skills/workflow/scripts/run_workflow.py"

    # Start workflow
    result = subprocess.run(
        f"python {script_path} '{user_input}'",
        capture_output=True,
        text=True,
        shell=True
    )

    if result.returncode != 0:
        return f"Error starting workflow: {result.stderr}"

    run_id = result.stdout.strip()

    # Poll for completion
    max_polls = 30  # 30 * 2s = 1 minute timeout
    for i in range(max_polls):
        info_result = subprocess.run(
            f"python {script_path.parent}/get_workflow_info.py {run_id}",
            capture_output=True,
            text=True,
            shell=True
        )

        import json
        info = json.loads(info_result.stdout)

        if info['status'] == 'success':
            return info['output']['summary']

        elif info['status'] == 'interrupted':
            return f"Workflow interrupted: {info['msg']}"

        elif info['status'] == 'fail':
            return f"Workflow failed: {info.get('error', 'Unknown error')}"

        import time
        time.sleep(2)

    return "Workflow timeout"
```
