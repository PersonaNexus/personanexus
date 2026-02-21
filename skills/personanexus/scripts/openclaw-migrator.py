#!/usr/bin/env python3
"""
OpenClaw Team Migrator - Convert existing OpenClaw agents to personanexus YAML

This script analyzes the current OpenClaw setup and generates a complete
personanexus team configuration, preserving existing personalities and
adding systematic governance based on observed collaboration patterns.
"""

import json
import yaml
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict

@dataclass
class AgentPersonality:
    """Structured representation of an OpenClaw agent personality."""
    agent_name: str
    agent_role: str
    personality_traits: Dict[str, float]
    personality_profile: Dict[str, Any]
    domain_expertise: List[str]
    behavioral_settings: Dict[str, Any]
    system_prompt: str

@dataclass 
class TaskPattern:
    """Represents a workflow pattern extracted from TASKBOARD.md"""
    task_id: str
    title: str
    owner: str
    priority: str
    status: str
    created: str
    notes: str

class OpenClawTeamMigrator:
    """Converts OpenClaw multi-agent setup to personanexus team configuration."""
    
    def __init__(self, openclaw_root: str = None):
        """Initialize with OpenClaw installation path."""
        self.openclaw_root = Path(openclaw_root or os.path.expanduser("~/.openclaw"))
        self.workspace = Path.cwd()  # Current workspace
        
    def load_personality(self, personality_file: str = None) -> AgentPersonality:
        """Load current agent personality from personality.json"""
        if personality_file:
            personality_path = Path(personality_file)
        else:
            personality_path = self.openclaw_root / "personality.json"
            
        if not personality_path.exists():
            raise FileNotFoundError(f"Personality file not found: {personality_path}")
            
        with open(personality_path, 'r') as f:
            data = json.load(f)
            
        return AgentPersonality(
            agent_name=data.get("agent_name", "Unknown"),
            agent_role=data.get("agent_role", "assistant"),
            personality_traits=data.get("personality_traits", {}),
            personality_profile=data.get("personality_profile", {}),
            domain_expertise=data.get("domain_expertise", []),
            behavioral_settings=data.get("behavioral_settings", {}),
            system_prompt=data.get("system_prompt", "")
        )
    
    def analyze_taskboard(self) -> List[TaskPattern]:
        """Extract workflow patterns from TASKBOARD.md"""
        taskboard_path = self.workspace / "shared" / "TASKBOARD.md"
        if not taskboard_path.exists():
            print(f"Warning: TASKBOARD.md not found at {taskboard_path}")
            return []
            
        patterns = []
        with open(taskboard_path, 'r') as f:
            content = f.read()
            
        # Extract tasks from markdown table format
        # | T-034 | Portfolio Dashboard v2 — real data | Forge | P1 | todo | 02-17 | 02-17 | Generator script + real CSV + baked prices |
        task_pattern = re.compile(r'\| (T-\d+) \| ([^|]+) \| ([^|]+) \| ([^|]+) \| ([^|]+) \| ([^|]+) \| [^|]+ \| ([^|]+) \|')
        
        for match in task_pattern.finditer(content):
            task_id, title, owner, priority, status, created, notes = match.groups()
            patterns.append(TaskPattern(
                task_id=task_id.strip(),
                title=title.strip(), 
                owner=owner.strip(),
                priority=priority.strip(),
                status=status.strip(),
                created=created.strip(),
                notes=notes.strip()
            ))
            
        return patterns
    
    def infer_team_composition(self, current_agent: AgentPersonality, task_patterns: List[TaskPattern]) -> Dict[str, Any]:
        """Infer team composition from task patterns and current agent."""
        
        # Extract unique owners from task patterns
        agents_from_tasks = set(pattern.owner for pattern in task_patterns if pattern.owner not in ['', 'Owner'])
        
        # Common multi-agent team patterns (customize based on your setup)
        team_agents = {}
        
        # Always include the current agent
        current_name = current_agent.agent_name.lower()
        team_agents[current_name] = {
            "role": current_agent.agent_role,
            "authority_level": 3,  # Default authority level
            "expertise_domains": current_agent.domain_expertise,
            "personality_summary": self._extract_personality_summary(current_agent),
            "current_personality": current_agent
        }
        
        # Infer other common agents based on task patterns
        if any(pattern for pattern in task_patterns if any(keyword in pattern.title.lower() 
               for keyword in ['research', 'analysis', 'data'])):
            if 'researcher' not in team_agents:
                team_agents['researcher'] = {
                    "role": "research_coordinator",
                    "authority_level": 4,
                    "expertise_domains": ["research", "data_gathering", "methodology"],
                    "personality_summary": {"thoroughness": 0.90, "curiosity": 0.85}
                }
                
        if any(pattern for pattern in task_patterns if any(keyword in pattern.title.lower()
               for keyword in ['analysis', 'statistical', 'data', 'metrics'])):
            if 'analyst' not in team_agents:
                team_agents['analyst'] = {
                    "role": "data_analyst", 
                    "authority_level": 3,
                    "expertise_domains": ["data_analysis", "statistics", "reporting"],
                    "personality_summary": {"analytical_precision": 0.88, "attention_to_detail": 0.85}
                }
                
        if any(pattern for pattern in task_patterns if any(keyword in pattern.title.lower()
               for keyword in ['development', 'implementation', 'deploy', 'code'])):
            if 'developer' not in team_agents:
                team_agents['developer'] = {
                    "role": "software_developer",
                    "authority_level": 3,
                    "expertise_domains": ["software_development", "deployment", "testing"],
                    "personality_summary": {"technical_rigor": 0.90, "problem_solving": 0.85}
                }
                
        if any(pattern for pattern in task_patterns if any(keyword in pattern.title.lower()
               for keyword in ['documentation', 'communication', 'writing', 'content'])):
            if 'communicator' not in team_agents:
                team_agents['communicator'] = {
                    "role": "content_specialist",
                    "authority_level": 2,
                    "expertise_domains": ["writing", "documentation", "communication"],
                    "personality_summary": {"clarity_focus": 0.88, "creativity": 0.80}
                }
        
        return team_agents
    
    def _extract_personality_summary(self, agent: AgentPersonality) -> Dict[str, float]:
        """Extract key personality traits for summary."""
        traits = agent.personality_traits
        if not traits:
            return {"balanced_approach": 0.75}
            
        # Extract most distinctive traits
        summary = {}
        if traits.get('rigor', 0) > 0.8:
            summary['technical_rigor'] = traits['rigor']
        if traits.get('creativity', 0) > 0.7:
            summary['creativity'] = traits['creativity']  
        if traits.get('empathy', 0) > 0.7:
            summary['empathy'] = traits['empathy']
        if traits.get('directness', 0) > 0.7:
            summary['directness'] = traits['directness']
            
        return summary if summary else {"balanced_approach": 0.75}
    
    def extract_workflow_patterns(self, task_patterns: List[TaskPattern]) -> Dict[str, Any]:
        """Extract common workflow patterns from completed tasks."""
        
        # Group tasks by type/pattern
        research_tasks = [t for t in task_patterns if any(keyword in t.title.lower() 
                         for keyword in ['research', 'analysis', 'data', 'market'])]
        
        development_tasks = [t for t in task_patterns if any(keyword in t.title.lower()
                            for keyword in ['dashboard', 'tool', 'cli', 'implementation', 'deploy'])]
        
        communication_tasks = [t for t in task_patterns if any(keyword in t.title.lower()
                              for keyword in ['documentation', 'briefing', 'communication', 'post'])]
        
        # Analyze completion patterns
        completed_tasks = [t for t in task_patterns if t.status in ['done', 'completed']]
        
        # Extract common workflow: Research → Analysis → Implementation → Communication
        workflow_patterns = {
            "research_to_implementation": {
                "description": "Comprehensive research → analysis → implementation → communication",
                "estimated_duration": "4-8 hours",
                "success_rate": len(completed_tasks) / len(task_patterns) if task_patterns else 0,
                "stages": [
                    {
                        "stage": "research_phase",
                        "primary_agent": "atlas",
                        "objective": "Gather comprehensive data with source validation"
                    },
                    {
                        "stage": "analysis_phase", 
                        "primary_agent": "annie",
                        "objective": "Statistical analysis and insight extraction"
                    },
                    {
                        "stage": "implementation_phase",
                        "primary_agent": "forge", 
                        "objective": "Build/deploy solution based on research and analysis"
                    },
                    {
                        "stage": "communication_phase",
                        "primary_agent": "ink",
                        "objective": "Create comprehensive documentation and stakeholder communication"
                    }
                ]
            }
        }
        
        return workflow_patterns
    
    def generate_team_yaml(self, 
                          current_agent: AgentPersonality,
                          task_patterns: List[TaskPattern],
                          team_name: str = "openclaw-core",
                          output_path: str = None) -> str:
        """Generate complete personanexus team YAML configuration."""
        
        team_composition = self.infer_team_composition(current_agent, task_patterns)
        workflow_patterns = self.extract_workflow_patterns(task_patterns)
        
        # Build team configuration
        team_config = {
            "schema_version": "2.0",
            "team": {
                "metadata": {
                    "id": f"team_{team_name}_001",
                    "name": f"OpenClaw {team_name.title()} Multi-Agent Team", 
                    "description": "Production team converted from OpenClaw multi-agent setup",
                    "version": "1.0.0",
                    "created_at": datetime.now(timezone.utc).isoformat(),
                    "author": "OpenClaw Team Migrator",
                    "source": "Migrated from OpenClaw personality.json and TASKBOARD.md analysis"
                },
                "composition": {
                    "agents": {}
                },
                "workflow_patterns": workflow_patterns,
                "governance": {
                    "decision_frameworks": {
                        "research_methodology": {
                            "authority": "atlas",
                            "description": "Atlas leads research approaches and source validation"
                        },
                        "technical_architecture": {
                            "authority": "forge", 
                            "description": "Forge leads technical decisions",
                            "consultation_required": ["atlas"]
                        },
                        "data_analysis_methodology": {
                            "authority": "annie",
                            "description": "Annie owns statistical rigor and analysis approach"
                        },
                        "external_communications": {
                            "authority": "ink",
                            "description": "Ink approves external-facing content"
                        }
                    },
                    "conflict_resolution": {
                        "expertise_boundary_disputes": {
                            "strategy": "capability_matrix_lookup",
                            "fallback": "defer_to_higher_authority_level"
                        }
                    }
                },
                "performance_metrics": {
                    "team_effectiveness": [
                        {
                            "metric": "workflow_completion_rate",
                            "target": "> 0.90",
                            "measurement": "successful_workflows / total_attempted_workflows"
                        },
                        {
                            "metric": "handoff_success_rate", 
                            "target": "> 0.95",
                            "measurement": "acknowledged_handoffs / total_handoff_attempts"
                        }
                    ]
                }
            }
        }
        
        # Add agent configurations
        for agent_name, agent_info in team_composition.items():
            agent_config = {
                "agent_id": f"agt_{agent_name}_001",
                "role": agent_info["role"],
                "authority_level": agent_info["authority_level"],
                "expertise_domains": agent_info["expertise_domains"],
                "personality_summary": agent_info["personality_summary"]
            }
            
            # Add detailed personality if this is the current agent
            if agent_name == current_agent.agent_name.lower():
                agent_config["personality_traits"] = current_agent.personality_traits
                agent_config["personality_profile"] = current_agent.personality_profile
                agent_config["behavioral_settings"] = current_agent.behavioral_settings
                
            team_config["team"]["composition"]["agents"][agent_name] = agent_config
        
        # Convert to YAML
        yaml_content = yaml.dump(team_config, default_flow_style=False, sort_keys=False, width=100)
        
        # Add header comment
        header = f"""# OpenClaw Team Configuration - Generated {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
# Converted from OpenClaw personality.json and TASKBOARD.md analysis
# 
# This team configuration preserves existing agent personalities and adds
# systematic governance based on observed collaboration patterns.
# 
# Usage:
#   personanexus compile openclaw-core-team.yaml --target openclaw
#   personanexus analyze openclaw-core-team.yaml --performance-data shared/

"""
        
        final_yaml = header + yaml_content
        
        # Save to file if output path specified
        if output_path:
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            with open(output_path, 'w') as f:
                f.write(final_yaml)
            print(f"✅ Team configuration written to: {output_path}")
            
        return final_yaml

def main():
    """Command-line interface for the OpenClaw team migrator."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Convert OpenClaw setup to personanexus team configuration")
    parser.add_argument("--personality", help="Path to personality.json file")  
    parser.add_argument("--team-name", default="openclaw-core", help="Name for the generated team")
    parser.add_argument("--output", help="Output path for team YAML file")
    parser.add_argument("--openclaw-root", help="Path to OpenClaw installation")
    
    args = parser.parse_args()
    
    try:
        # Initialize migrator
        migrator = OpenClawTeamMigrator(args.openclaw_root)
        
        # Load current agent personality  
        print("📋 Loading agent personality...")
        current_agent = migrator.load_personality(args.personality)
        print(f"✅ Loaded personality for: {current_agent.agent_name}")
        
        # Analyze task patterns
        print("📊 Analyzing task patterns from TASKBOARD.md...")
        task_patterns = migrator.analyze_taskboard() 
        print(f"✅ Found {len(task_patterns)} tasks for analysis")
        
        # Generate team configuration
        print("🎭 Generating team configuration...")
        output_path = args.output or f"team-configs/{args.team_name}-team.yaml"
        team_yaml = migrator.generate_team_yaml(
            current_agent=current_agent,
            task_patterns=task_patterns,
            team_name=args.team_name,
            output_path=output_path
        )
        
        print(f"""
🎉 OpenClaw team migration complete!

📁 Generated: {output_path}
👥 Team: {args.team_name} 
🤖 Agents: {len(task_patterns)} task patterns analyzed
🎯 Ready for personanexus framework

Next steps:
1. Review the generated team configuration
2. Test with: personanexus validate {output_path}  
3. Compile for other platforms: personanexus compile {output_path} --target crewai
4. Analyze performance: personanexus analyze {output_path}
        """)
        
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        return 1
        
    return 0

if __name__ == "__main__":
    exit(main())