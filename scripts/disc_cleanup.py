#!/usr/bin/env python3
"""
DISC Naming Cleanup Script for PersonaNexus Framework

This script standardizes DISC-related naming conventions across the codebase
to ensure consistency in field names, documentation, and user-facing text.

Standardization Rules:
1. DISC (all caps) in user-facing text and documentation 
2. disc (lowercase) in code/field names
3. snake_case for all field names: disc_preset, disc_profile, etc.
4. Consistent preset naming: the_commander, the_analyst, etc.
"""

import re
from pathlib import Path
from typing import List, Dict, Tuple


def find_inconsistencies(root_dir: Path) -> Dict[str, List[Tuple[str, int, str]]]:
    """Find DISC naming inconsistencies across the codebase."""
    issues = {
        "mixed_case": [],
        "inconsistent_preset_names": [],
        "doc_inconsistencies": [],
    }
    
    # Patterns to check
    mixed_case_pattern = re.compile(r'\bDisc\b|\bdisc\b(?=\s+[A-Z])')
    preset_pattern = re.compile(r'disc[_-]?preset|preset[_-]?disc', re.IGNORECASE)
    
    # Files to check
    for file_path in root_dir.rglob("*.py"):
        if "/__pycache__/" in str(file_path):
            continue
            
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                
            for line_num, line in enumerate(lines, 1):
                # Check for mixed case DISC
                if mixed_case_pattern.search(line):
                    issues["mixed_case"].append((str(file_path), line_num, line.strip()))
                
                # Check preset naming patterns
                preset_matches = preset_pattern.findall(line)
                for match in preset_matches:
                    if match not in ["disc_preset", "DISC preset", "DISC presets"]:
                        issues["inconsistent_preset_names"].append((str(file_path), line_num, line.strip()))
                        
        except Exception as e:
            print(f"Error reading {file_path}: {e}")
            
    # Check documentation files
    for ext in ["*.md", "*.rst", "*.yaml", "*.yml"]:
        for file_path in root_dir.rglob(ext):
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    
                # Look for inconsistent documentation
                lines = content.split('\n')
                for line_num, line in enumerate(lines, 1):
                    # In documentation, prefer "DISC" for user-facing text
                    if re.search(r'\bdisc\b(?!\s*[_=:])', line, re.IGNORECASE) and not re.search(r'DISC', line):
                        issues["doc_inconsistencies"].append((str(file_path), line_num, line.strip()))
                        
            except Exception as e:
                print(f"Error reading {file_path}: {e}")
                
    return issues


def generate_cleanup_report(root_dir: Path) -> str:
    """Generate a comprehensive cleanup report."""
    issues = find_inconsistencies(root_dir)
    
    report = []
    report.append("# DISC Naming Cleanup Report")
    report.append(f"Generated for: {root_dir}")
    report.append("")
    
    # Summary
    total_issues = sum(len(issue_list) for issue_list in issues.values())
    report.append(f"## Summary: {total_issues} issues found")
    report.append("")
    
    # Detailed findings
    for category, issue_list in issues.items():
        if not issue_list:
            continue
            
        report.append(f"### {category.replace('_', ' ').title()} ({len(issue_list)} issues)")
        report.append("")
        
        for file_path, line_num, line_content in issue_list[:10]:  # Limit to first 10
            report.append(f"- `{file_path}:{line_num}`: {line_content}")
            
        if len(issue_list) > 10:
            report.append(f"- ... and {len(issue_list) - 10} more")
            
        report.append("")
    
    # Recommendations
    report.append("## Standardization Recommendations")
    report.append("")
    report.append("1. **User-facing text**: Use 'DISC' (all caps) in documentation, CLI help, and UI")
    report.append("2. **Code fields**: Use 'disc' (lowercase) for field names and variables")
    report.append("3. **Preset names**: Standardize on 'disc_preset' field name")
    report.append("4. **Function names**: Use snake_case consistently (get_disc_preset, list_disc_presets)")
    report.append("5. **Documentation**: Ensure consistent capitalization based on context")
    report.append("")
    
    return "\n".join(report)


def apply_automatic_fixes(root_dir: Path, dry_run: bool = True) -> List[str]:
    """Apply automatic fixes where safe to do so."""
    changes = []
    
    # Define safe replacements
    safe_replacements = {
        # In Python code comments and strings
        r'# DISC preset': '# DISC preset',  # Already correct
        r'""".*?DISC.*?"""': lambda m: m.group(0),  # Leave docstrings alone for manual review
        
        # In CLI help text - ensure DISC is capitalized
        r'"([^"]*?)disc([^"]*?)"': lambda m: f'"{m.group(1)}DISC{m.group(2)}"' if 'preset' not in m.group(0).lower() else m.group(0),
    }
    
    # Process Python files
    for file_path in root_dir.rglob("*.py"):
        if "/__pycache__/" in str(file_path):
            continue
            
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                original_content = f.read()
                
            modified_content = original_content
            file_changes = []
            
            # Apply specific fixes for CLI help text
            cli_help_pattern = re.compile(r'(help="[^"]*?)disc([^"]*?")', re.IGNORECASE)
            def fix_cli_help(match):
                if "preset" not in match.group(0).lower():
                    return f'{match.group(1)}DISC{match.group(2)}'
                return match.group(0)
                
            new_content = cli_help_pattern.sub(fix_cli_help, modified_content)
            if new_content != modified_content:
                file_changes.append("Fixed CLI help text capitalization")
                modified_content = new_content
            
            # Apply changes if any were made
            if modified_content != original_content:
                if not dry_run:
                    with open(file_path, 'w', encoding='utf-8') as f:
                        f.write(modified_content)
                        
                changes.append(f"{file_path}: {', '.join(file_changes)}")
                
        except Exception as e:
            print(f"Error processing {file_path}: {e}")
    
    return changes


def main():
    """Main cleanup function."""
    root_dir = Path(__file__).parent.parent  # personanexus root
    
    print("🔍 Analyzing DISC naming consistency...")
    
    # Generate report
    report = generate_cleanup_report(root_dir)
    
    # Save report
    report_file = root_dir / "DISC_CLEANUP_REPORT.md"
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write(report)
        
    print(f"📊 Report saved to: {report_file}")
    print()
    print("Preview:")
    print("=" * 50)
    print(report[:1000] + "..." if len(report) > 1000 else report)
    print("=" * 50)
    
    # Ask about applying fixes
    print()
    print("🔧 Available automatic fixes:")
    changes = apply_automatic_fixes(root_dir, dry_run=True)
    
    if changes:
        print(f"Would make {len(changes)} changes:")
        for change in changes[:5]:
            print(f"  - {change}")
        if len(changes) > 5:
            print(f"  - ... and {len(changes) - 5} more")
            
        print()
        apply = input("Apply these changes? [y/N]: ").lower().startswith('y')
        
        if apply:
            actual_changes = apply_automatic_fixes(root_dir, dry_run=False)
            print(f"✅ Applied {len(actual_changes)} changes")
        else:
            print("⏭️  Skipped automatic fixes")
    else:
        print("✅ No automatic fixes available - manual review recommended")
    
    print()
    print("📋 Manual review recommended for:")
    print("  - Documentation consistency in README.md")
    print("  - Schema field naming validation") 
    print("  - Example file consistency")
    print("  - Web UI component text")


if __name__ == "__main__":
    main()