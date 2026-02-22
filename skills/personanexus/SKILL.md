# PersonaNexus Skill - Multi-Agent Team Management

Manage, analyze, and optimize multi-agent team configurations using the personanexus framework. Transform OpenClaw's existing multi-agent coordination into systematic team orchestration with performance analytics.

## What This Skill Provides

**Team Configuration Management:**
- Convert existing OpenClaw agents → standardized team YAML
- Generate team configurations from current personality.json files
- Create reusable workflow patterns based on task history

**Team Performance Analytics:**
- Analyze collaboration patterns from TASKBOARD.md history
- Identify workflow bottlenecks and optimization opportunities
- Generate performance reports and improvement recommendations

**Cross-Platform Integration:**
- Compile team configs for CrewAI, LangGraph, AutoGen
- Export team definitions for external orchestration platforms
- Maintain consistent agent identities across multiple frameworks

## Quick Start

### Generate Team Config from Current Agents
```bash
# Convert existing OpenClaw agents to personanexus YAML
python scripts/openclaw-migrator.py \
  --personality ~/.openclaw/personality.json \
  --team-name "openclaw-core" \
  --agents atlas,annie,forge,ink \
  --output team-configs/openclaw-core-team.yaml
```

### Analyze Team Performance (Planned)
```bash
# Analyze collaboration effectiveness from task history
python scripts/team-analyzer.py \
  --taskboard shared/TASKBOARD.md \
  --timespan 30d \
  --output analytics/team-performance-report.md
```

### Generate Workflow Patterns (Planned)
```bash
# Extract successful workflow patterns from completed tasks
python scripts/workflow-extractor.py \
  --taskboard shared/TASKBOARD.md \
  --status-files shared/status/ \
  --output workflows/extracted-patterns.yaml
```

### Optimize Team Configuration (Planned)
```bash
# Generate optimization recommendations based on performance data
python scripts/team-optimizer.py \
  --team-config team-configs/openclaw-core-team.yaml \
  --performance-data analytics/team-performance-report.json \
  --output recommendations/optimization-suggestions.md
```

## Core Scripts

### 1. OpenClaw Team Migrator (`openclaw-migrator.py`)
**Purpose:** Convert existing OpenClaw agent configurations to personanexus YAML format

**Input:** 
- `~/.openclaw/personality.json` (current agent personality)
- Shared workspace data (status files, task history)

**Output:**
- Complete team YAML with agents, governance, workflows
- Preserves existing personality traits and expertise domains
- Adds team-level governance based on observed collaboration patterns

**Example Usage:**
```bash
# Generate team config for current OpenClaw setup
python scripts/openclaw-migrator.py \
  --scan-agents \
  --include-workflows \
  --output team-configs/openclaw-production-team.yaml

# Result: Complete team YAML ready for personanexus framework
```

### 2. Team Performance Analyzer (`team-analyzer.py`) — Planned
**Purpose:** Analyze multi-agent collaboration effectiveness from OpenClaw operational data

**Data Sources:**
- `shared/TASKBOARD.md` - Task assignments, completion rates, handoff patterns
- `shared/status/*.json` - Agent activity and status updates  
- `~/.openclaw/logs/` - Detailed execution and communication logs
- `memory/*.md` - Decision history and context

**Analytics Generated:**
- **Collaboration Score** - Overall team effectiveness (0-100)
- **Handoff Analysis** - Success rates and failure patterns between agents
- **Workflow Efficiency** - Time-to-completion by workflow type
- **Resource Utilization** - Agent workload distribution and bottlenecks
- **Decision Quality** - Correlation between decisions and outcomes

**Example Usage:**
```bash
# Comprehensive team analysis
python scripts/team-analyzer.py \
  --data-sources shared/ \
  --timespan 60d \
  --include-predictions \
  --output analytics/comprehensive-team-analysis.html

# Results: Interactive dashboard showing team performance metrics
```

### 3. Workflow Pattern Extractor (`workflow-extractor.py`) — Planned
**Purpose:** Learn successful workflow patterns from completed OpenClaw tasks

**Pattern Recognition:**
- **Sequential Patterns** - Atlas → Annie → Forge → Ink workflows
- **Parallel Patterns** - Multiple agents working simultaneously  
- **Conditional Patterns** - Workflow branches based on outcomes
- **Exception Patterns** - How team handles failures and conflicts

**Example Usage:**
```bash
# Extract patterns from successful tasks
python scripts/workflow-extractor.py \
  --filter-by-success-rate ">0.8" \
  --min-pattern-frequency 3 \
  --output workflows/proven-patterns.yaml

# Generate new workflow templates
python scripts/workflow-extractor.py \
  --create-templates \
  --complexity-levels "simple,standard,complex" \
  --output workflows/templates/
```

### 4. Team Optimizer (`team-optimizer.py`) — Planned
**Purpose:** Generate data-driven recommendations for improving team performance

**Optimization Areas:**
- **Personality Adjustments** - Trait modifications for better collaboration
- **Authority Rebalancing** - Optimal decision-making hierarchies
- **Workflow Improvements** - Process optimizations based on bottleneck analysis
- **Resource Allocation** - Better distribution of tasks based on agent strengths

**Example Usage:**
```bash
# Generate optimization recommendations
python scripts/team-optimizer.py \
  --current-config team-configs/openclaw-core-team.yaml \
  --performance-baseline analytics/last-30d-performance.json \
  --optimization-target "collaboration_score>85" \
  --output recommendations/q1-2026-optimizations.md
```

## Integration with OpenClaw

### Seamless Data Integration
```python
# The skill reads existing OpenClaw data sources:
OPENCLAW_DATA_SOURCES = {
    "agent_personality": "~/.openclaw/personality.json",
    "task_history": "shared/TASKBOARD.md", 
    "agent_status": "shared/status/*.json",
    "handoff_specs": "shared/handoffs/",
    "collaboration_protocols": "shared/protocols/",
    "execution_logs": "~/.openclaw/logs/",
    "memory_context": "memory/*.md"
}
```

### Enhanced OpenClaw Capabilities
```bash
# New capabilities added to OpenClaw through this skill:
openclaw --skill personanexus team-status
openclaw --skill personanexus analyze-collaboration --days 30
openclaw --skill personanexus optimize-workflows
openclaw --skill personanexus export-team --target crewai
```

### Maintains Backward Compatibility
- ✅ Existing agents continue working unchanged
- ✅ Current TASKBOARD.md and shared workspace patterns preserved
- ✅ All existing OpenClaw commands and workflows unaffected
- ✅ Skill provides additional insights without disrupting operations

## Example Workflows

### Weekly Team Health Check
```bash
# Automated weekly team performance analysis
cron add "OpenClaw Team Health Check" \
  --schedule "0 9 * * 1" \
  --task "Analyze team performance and generate weekly report" \
  --command "openclaw --skill personanexus weekly-health-check"
```

### Workflow Optimization Cycle  
```bash
# Monthly workflow optimization
# 1. Analyze recent performance
python scripts/team-analyzer.py --timespan 30d --output monthly-performance.json

# 2. Extract successful patterns  
python scripts/workflow-extractor.py --performance-filter "good" --output new-patterns.yaml

# 3. Generate optimization recommendations
python scripts/team-optimizer.py --target "efficiency+20%" --output optimization-plan.md

# 4. Update team configuration (with approval)
# Review optimization-plan.md → Apply selected recommendations
```

### Cross-Platform Team Deployment
```bash
# Deploy OpenClaw team configuration to other platforms
# 1. Export team config
python scripts/team-compiler.py \
  --input team-configs/openclaw-core-team.yaml \
  --target crewai \
  --output crewai-deployment/

# 2. Deploy to CrewAI
cd crewai-deployment && python deploy-team.py

# 3. Monitor cross-platform performance
python scripts/cross-platform-monitor.py \
  --openclaw-metrics analytics/ \
  --crewai-metrics crewai-deployment/logs/ \
  --compare-effectiveness
```

## File Structure

```
skills/personanexus/
├── SKILL.md                          # This file
├── README.md                         # Quick setup guide
├── requirements.txt                  # Python dependencies
├── scripts/
│   ├── openclaw-migrator.py          # OpenClaw → personanexus conversion
│   ├── team-analyzer.py              # Performance analysis (planned)
│   ├── workflow-extractor.py         # Pattern recognition (planned)
│   ├── team-optimizer.py             # Optimization recommendations (planned)
│   ├── team-compiler.py              # Cross-platform compilation (planned)
│   └── utils/
│       ├── openclaw-parser.py        # Parse OpenClaw data structures
│       ├── performance-metrics.py    # Team performance calculations
│       └── visualization.py          # Generate charts and reports
├── templates/
│   ├── openclaw-team-template.yaml   # Base OpenClaw team template
│   ├── workflow-patterns/            # Common workflow templates
│   │   ├── research-to-implementation.yaml
│   │   ├── rapid-response.yaml
│   │   └── development-cycle.yaml
│   └── cross-platform/               # Templates for other platforms
│       ├── crewai-template.py
│       ├── langgraph-template.py
│       └── autogen-template.py
├── examples/
│   ├── team-configs/
│   │   ├── openclaw-core-team.yaml   # Real OpenClaw team config
│   │   └── variations/               # Alternative team structures
│   ├── analytics-reports/            # Sample performance reports
│   └── optimization-cases/           # Before/after optimization examples
└── docs/
    ├── integration-guide.md          # How to integrate with existing OpenClaw
    ├── performance-metrics.md        # Explanation of analytics
    └── troubleshooting.md            # Common issues and solutions
```

## Success Metrics

### Team Performance Improvements
- **Collaboration Score** increase (baseline vs. optimized)  
- **Task Completion Rate** improvement (successful workflows / total attempted)
- **Handoff Success Rate** increase (smooth agent transitions)
- **Average Workflow Duration** reduction (time-to-completion)

### OpenClaw Integration Quality
- **Data Integration Accuracy** (correctly parses existing OpenClaw data)
- **Backward Compatibility** (no disruption to existing workflows)  
- **User Experience** (skill provides value without complexity)
- **Performance Impact** (minimal overhead on existing OpenClaw operations)

### Adoption and Usage
- **Weekly Usage** (how often the skill is used)
- **Report Generation** (analytics reports generated and reviewed)
- **Optimization Implementation** (recommendations actually applied)
- **Cross-Platform Usage** (team configs deployed to other platforms)

## Maintenance and Updates

The skill automatically adapts to OpenClaw changes by:
- **Dynamic data source discovery** - Adapts to OpenClaw file structure changes
- **Schema evolution** - Handles updates to personality.json and TASKBOARD.md formats
- **Backward compatibility** - Maintains support for previous OpenClaw versions
- **Self-updating templates** - Improves workflow patterns based on new successful examples

Regular maintenance includes:
- **Monthly pattern updates** - Refresh workflow templates based on latest data
- **Quarterly optimization** - Review and enhance analysis algorithms
- **Cross-platform compatibility** - Keep export targets updated with latest platform versions

---

This skill transforms OpenClaw from individual agent coordination to systematic multi-agent team orchestration, providing the missing layer of team analytics and optimization without disrupting existing successful workflows.