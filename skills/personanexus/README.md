# 🎭 PersonaNexus OpenClaw Skill

**Transform your OpenClaw multi-agent setup into systematic team orchestration with performance analytics.**

## ⚠️ Important: Examples vs. Real Implementation

**This skill contains EXAMPLE configurations only.** All team configurations, personality traits, task patterns, and workflow examples are **fictional demonstrations** of the framework capabilities.

### 🔒 Privacy & Security
- **No real agent data is included** in this repository
- **Your actual personality.json data stays private** on your system  
- **Migration script reads your data locally** but doesn't store or transmit it
- **Generated team configs are for your use only** - not shared or committed

### 🎯 How It Works
1. **Framework provides the structure** - YAML schemas, governance patterns, analytics
2. **Migration script reads YOUR data** - personality.json, TASKBOARD.md, etc.
3. **Generates YOUR team config** - preserves your agents' actual personalities
4. **You control the output** - review, modify, and use as needed

---

## 🚀 Quick Start

### Install the Skill
```bash
# Copy skill to OpenClaw skills directory
cp -r personanexus /path/to/openclaw/skills/

# Or create symlink for development
ln -s $(pwd)/personanexus /path/to/openclaw/skills/personanexus
```

### Generate Your Team Configuration
```bash
# Convert your actual OpenClaw setup to personanexus format
python3 scripts/openclaw-migrator.py \
  --personality ~/.openclaw/personality.json \
  --team-name "my-team" \
  --output my-team-config.yaml
```

### Analyze Your Team Performance
```bash  
# Analyze collaboration patterns from your task history
python3 scripts/team-analyzer.py \
  --taskboard shared/TASKBOARD.md \
  --timespan 30d \
  --output analytics/team-performance.md
```

## 📁 What's Included

### **EXAMPLE Files (Generic/Fictional)**
```
examples/
├── example-team.yaml          # Fictional team for demonstration
└── workflow-patterns/         # Generic workflow templates
```
**Note:** These are educational examples. Your real team config will be different.

### **Scripts (Work with YOUR Data)**
```
scripts/
├── openclaw-migrator.py       # Reads YOUR personality.json
├── team-analyzer.py           # Analyzes YOUR task history  
├── workflow-extractor.py      # Learns from YOUR completed tasks
└── team-optimizer.py          # Optimizes YOUR team performance
```

### **Templates (Customizable)**
```
templates/
├── team-template.yaml         # Base template for any team
├── workflow-patterns/         # Common patterns you can adapt
└── cross-platform/            # Export to CrewAI, LangGraph, etc.
```

## 🔧 Core Capabilities

### **1. Team Configuration Management**
- **Convert existing OpenClaw agents** → systematic team YAML
- **Preserve personality traits** from your personality.json
- **Add governance frameworks** based on observed collaboration
- **Generate reusable workflow patterns** from your task history

### **2. Performance Analytics**
- **Collaboration effectiveness** - How well do your agents work together?
- **Workflow bottlenecks** - Where do tasks get stuck?
- **Handoff success rates** - Are agent transitions smooth?
- **Resource utilization** - Is work distributed fairly?

### **3. Cross-Platform Integration**  
- **Export to CrewAI** - Use your team config in CrewAI workflows
- **LangGraph compatibility** - Generate LangGraph agent definitions
- **AutoGen support** - Create AutoGen assistant configurations
- **Maintain consistency** across all platforms

### **4. Continuous Optimization**
- **Learn from task history** - Which workflows succeed most often?
- **Identify improvement opportunities** - Data-driven recommendations
- **Track performance over time** - Are optimizations working?
- **Suggest team adjustments** - Better personality configurations

## 🎯 Example Workflow

### Step 1: Generate Your Team Config
```bash
# This reads YOUR actual data (not the examples in this repo)
python3 scripts/openclaw-migrator.py \
  --personality ~/.openclaw/personality.json \
  --team-name "production-team" \
  --output configs/my-production-team.yaml

# Result: Team config with YOUR agents' real personalities
```

### Step 2: Analyze Current Performance
```bash
# This analyzes YOUR task completion patterns
python3 scripts/team-analyzer.py \
  --taskboard shared/TASKBOARD.md \
  --timespan 60d \
  --include-predictions \
  --output analytics/current-performance.json

# Result: Report on how YOUR team actually collaborates
```

### Step 3: Optimize Team Configuration
```bash
# This suggests improvements based on YOUR data
python3 scripts/team-optimizer.py \
  --current-config configs/my-production-team.yaml \
  --performance-data analytics/current-performance.json \
  --optimization-target "collaboration_score>90" \
  --output recommendations/q1-improvements.md

# Result: Specific suggestions for YOUR team
```

### Step 4: Export to Other Platforms
```bash
# Use your team config with other frameworks
python3 scripts/team-compiler.py \
  --input configs/my-production-team.yaml \
  --target crewai \
  --output exports/crewai-deployment/

# Result: YOUR team running on CrewAI
```

## 🛡️ Privacy & Data Handling

### **What Stays Private:**
- ✅ Your actual personality.json contents
- ✅ Your TASKBOARD.md task history  
- ✅ Your agent status files and logs
- ✅ Your team performance data
- ✅ Generated team configurations

### **What's Public (Examples Only):**
- ✅ Framework scripts and templates
- ✅ Generic example team configurations
- ✅ Fictional workflow patterns
- ✅ Educational documentation

### **Data Flow:**
```
Your Private Data → Migration Script → Your Team Config
        ↑                ↑                    ↑
   (stays local)   (runs locally)      (your property)

Public Examples ← Framework Documentation ← Generic Templates
        ↑                ↑                    ↑
  (educational)    (how-to guides)        (starting points)
```

## 📊 Success Metrics

### **Team Performance Improvements**
- **Collaboration Score Increase** - Measure team effectiveness over time
- **Task Completion Rate** - Are workflows completing successfully?
- **Handoff Success Rate** - Smooth transitions between agents
- **Average Workflow Duration** - Getting faster at completing work

### **OpenClaw Integration Quality**  
- **Data Integration Accuracy** - Correctly reads your existing setup
- **Zero Disruption** - Existing workflows continue unchanged
- **Value Addition** - Provides insights you didn't have before

## 🔄 Maintenance & Updates

### **Skill Updates**
- **Framework improvements** - Better analysis algorithms, new export targets
- **Template updates** - New workflow patterns, optimization strategies
- **Bug fixes** - Issues reported by the community

### **Your Data Updates**
- **Automatic adaptation** - Skill learns from your evolving task patterns  
- **Configuration drift detection** - Alerts when team config gets outdated
- **Performance trend tracking** - Long-term team effectiveness measurement

## 🤝 Contributing

### **Safe Ways to Contribute:**
- ✅ **Improve framework scripts** - Better analysis algorithms
- ✅ **Add new workflow templates** - Generic patterns others can use
- ✅ **Enhance documentation** - Clearer setup instructions
- ✅ **Report bugs** - Issues with the framework (not your data)

### **What NOT to Contribute:**
- ❌ Your actual team configurations
- ❌ Real personality data or task history
- ❌ Performance reports from your system  
- ❌ Any organization-specific information

## 📚 Documentation

- **[SKILL.md](SKILL.md)** - Complete skill specification and usage guide
- **[Integration Analysis](../../OPENCLAW_INTEGRATION.md)** - How this integrates with OpenClaw
- **[Competitive Analysis](../../COMPETITIVE_ANALYSIS.md)** - vs. CrewAI, LangGraph, AutoGen
- **[Examples](examples/)** - Fictional team configurations for learning

## 🆘 Support

### **Getting Help:**
1. **Check the examples** - See how fictional teams are configured
2. **Read the documentation** - Comprehensive guides available  
3. **Test with sample data** - Use the examples to understand the framework
4. **File issues** - Report bugs or request features (no personal data)

### **Common Questions:**
**Q: Are these real agent configurations?**  
A: No, all examples are fictional demonstrations. Your real config is generated from your data.

**Q: Will this change my existing OpenClaw setup?**  
A: No, the skill only reads your data and generates new configs. Existing agents unchanged.

**Q: Can I share my generated team config?**  
A: That's your choice, but be aware it contains your agent personalities and task patterns.

**Q: How do I customize the governance frameworks?**  
A: Edit the generated YAML file to match your team's decision-making preferences.

---

**Remember: This is a framework for managing YOUR multi-agent teams. The examples are educational - your real value comes from applying it to YOUR OpenClaw setup with YOUR agents and YOUR data.**