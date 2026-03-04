# Workflow Skill - 数据分析工作流编排

完整的workflow skill实现，基于三个核心函数：`runworkflow`、`getflowinfo`、`resumeflow`。

## 目录结构

```
workflow/
├── SKILL.md                    # Skill定义和使用指南
├── scripts/                    # 可执行脚本
│   ├── workflow_mock.py        # Mock实现（含完整逻辑）
│   ├── run_workflow.py         # 启动工作流
│   ├── get_workflow_info.py    # 查询工作流状态
│   └── resume_workflow.py      # 恢复中断的工作流
└── references/                 # 参考文档
    ├── API_SPEC.md            # 完整API规范
    └── EXAMPLES.md            # 使用示例
```

## 快速开始

### 1. 测试Mock实现

```bash
cd scripts/
python workflow_mock.py
```

### 2. 启动工作流

```bash
python scripts/run_workflow.py "Compare Q1 and Q2 sales"
# 返回: mock_1234567890123
```

### 3. 查询状态

```bash
python scripts/get_workflow_info.py mock_1234567890123
```

### 4. 恢复工作流

```bash
python scripts/resume_workflow.py "Q1 2024" mock_1234567890123
```

## 核心函数

### runworkflow(user_input: str) -> str

启动新的工作流分析。

**参数:**
- `user_input`: 自然语言描述的分析任务

**返回:**
- `run_id`: 工作流唯一标识符

**示例:**
```python
run_id = runworkflow("Compare Q1 and Q2 sales by region")
```

### getflowinfo(run_id: str) -> dict

查询工作流状态和结果。

**参数:**
- `run_id`: 工作流标识符

**返回:**
```json
{
  "status": "success|interrupted|processing|fail",
  "output": {...},  // status=success时
  "msg": "...",      // status=interrupted时
  "error": "..."     // status=fail时
}
```

### resumeflow(user_input: str, run_id: str) -> None

恢复被中断的工作流。

**参数:**
- `user_input`: 补充的用户输入
- `run_id`: 要恢复的工作流ID

## 支持的分析类型

### 1. 数据对比分析 (Comparison)

**关键词:** compare, vs, 对比, 比较

**示例:**
```bash
python scripts/run_workflow.py "Compare Q1 vs Q2 sales by region"
```

**输出:**
- 期间对比（QoQ, YoY）
- 区域/品类/渠道对比
- 增长率分析

### 2. 离群点检测 (Outlier Detection)

**关键词:** outlier, anomaly, 异常, 离群

**示例:**
```bash
python scripts/run_workflow.py "Identify outliers in Q3 sales data"
```

**输出:**
- IQR方法离群点
- Z-score异常值
- 异常原因标注

### 3. 控制变量分析 (Controlled Analysis)

**关键词:** control, impact, 控制, 影响

**示例:**
```bash
python scripts/run_workflow.py "Analyze price impact controlling for seasonality"
```

**输出:**
- 原始相关性
- 控制后净影响
- 显著性因子

## Mock实现特性

### 随机场景生成

- 70%概率直接成功
- 30%概率需要中断（请求补充信息）
- 自动生成合理的分析结果

### 持久化存储

- 工作流状态保存到 `~/.nanobot/workspace/workflow_mock/`
- JSON格式，便于调试
- 支持跨会话查询

### 状态转换

```
processing → success (40%概率/轮询)
processing → interrupted (初始30%概率)
interrupted → success (调用resumeflow后)
```

## 集成到Nanobot

### 方式1: 通过exec工具

```bash
# 在nanobot中
exec("python ~/nanobot/skills/workflow/scripts/run_workflow.py 'Compare Q1 Q2 sales'")
```

### 方式2: 作为Python模块导入

```python
import sys
sys.path.append("~/nanobot/skills/workflow/scripts")

from workflow_mock import runworkflow, getflowinfo, resumeflow

run_id = runworkflow("Analyze sales data")
info = getflowinfo(run_id)
```

## 典型使用流程

### 简单场景（无中断）

```bash
# 1. 启动
run_id=$(python scripts/run_workflow.py "Analyze Q3 sales")

# 2. 轮询
while true; do
  info=$(python scripts/get_workflow_info.py $run_id)
  status=$(echo $info | jq -r '.status')

  if [ "$status" = "success" ]; then
    echo $info | jq -r '.output.summary'
    break
  fi

  sleep 2
done
```

### 复杂场景（处理中断）

```bash
run_id=$(python scripts/run_workflow.py "Analyze sales")

while true; do
  info=$(python scripts/get_workflow_info.py $run_id)
  status=$(echo $info | jq -r '.status')

  if [ "$status" = "interrupted" ]; then
    msg=$(echo $info | jq -r '.msg')
    echo "需要输入: $msg"
    read -p "请补充: " input
    python scripts/resume_workflow.py "$input" $run_id
  elif [ "$status" = "success" ]; then
    echo $info | jq -r '.output.summary'
    break
  fi

  sleep 2
done
```

## 测试结果

所有脚本已测试通过：

✅ `workflow_mock.py` - Mock实现正常工作
✅ `run_workflow.py` - 成功启动工作流
✅ `get_workflow_info.py` - 正确返回状态信息
✅ `resume_workflow.py` - 可以恢复中断的工作流

## 接入真实后端

### 步骤1: 创建真实实现

```python
# external_workflow.py
def runworkflow(user_input: str) -> str:
    # 调用真实API
    response = requests.post("http://your-api/run", json={"input": user_input})
    return response.json()["run_id"]

def getflowinfo(run_id: str) -> dict:
    response = requests.get(f"http://your-api/run/{run_id}")
    return response.json()

def resumeflow(user_input: str, run_id: str) -> None:
    requests.post(f"http://your-api/run/{run_id}/resume", json={"input": user_input})
```

### 步骤2: 修改scripts引用

在每个脚本顶部，将:
```python
from workflow_mock import runworkflow, getflowinfo, resumeflow
```

改为:
```python
from external_workflow import runworkflow, getflowinfo, resumeflow
```

## 文档

- **SKILL.md**: Skill使用指南（AI视角）
- **API_SPEC.md**: 完整API规范和数据结构
- **EXAMPLES.md**: 详细使用示例和模式

## 注意事项

1. **Mock仅供开发测试**: 生产环境需接入真实后端
2. **状态一致性**: 确保getflowinfo返回的状态与实际一致
3. **中断超时**: 默认1小时，可在workflow_mock.py中配置
4. **并发安全**: 不同run_id的调用是线程安全的

## 未来扩展

- [ ] 支持批量工作流执行
- [ ] 添加工作流模板系统
- [ ] 实现工作流可视化
- [ ] 支持工作流编排（DAG）
- [ ] 添加性能监控和日志

## 作者

基于nanobot skill-creator模板创建
文档参考用户提供的工作流集成指南
