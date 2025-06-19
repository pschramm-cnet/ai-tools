#!/usr/bin/env python3
"""
Extract GitHub PR comments from URL and format them for Copilot
Usage: python pr_to_copilot.py <PR_URL_OR_NUMBER> [--user USERNAME] [--repo REPO]
"""

import json
import subprocess
import sys
import argparse
import re
from pathlib import Path
from urllib.parse import urlparse

def parse_pr_url(input_str):
    """Parse GitHub PR URL or number to extract repo, PR number, and review ID"""
    # URL pattern: https://github.com/owner/repo/pull/123#pullrequestreview-456
    url_pattern = r'https://github\.com/([^/]+/[^/]+)/pull/(\d+)'
    review_pattern = r'pullrequestreview-(\d+)'
    
    if input_str.isdigit():
        # Just a PR number
        return None, input_str, None
    
    url_match = re.search(url_pattern, input_str)
    if url_match:
        repo = url_match.group(1)
        pr_number = url_match.group(2)
        
        # Check for review ID
        review_match = re.search(review_pattern, input_str)
        review_id = review_match.group(1) if review_match else None
        
        return repo, pr_number, review_id
    
    raise ValueError("Invalid input. Provide either a GitHub PR URL or PR number.")

def run_gh_command(cmd):
    """Run a GitHub CLI command and return JSON output"""
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, check=True)
        return json.loads(result.stdout) if result.stdout.strip() else {}
    except subprocess.CalledProcessError as e:
        print(f"Error running command: {cmd}")
        print(f"Error: {e.stderr}")
        return {}

def run_gh_api(endpoint):
    """Run a GitHub API call and return JSON output"""
    try:
        result = subprocess.run(f"gh api {endpoint}", shell=True, capture_output=True, text=True, check=True)
        return json.loads(result.stdout) if result.stdout.strip() else {}
    except subprocess.CalledProcessError as e:
        print(f"Error calling API: {endpoint}")
        print(f"Error: {e.stderr}")
        return {}

def extract_pr_comments(pr_number, repo=None, username=None, review_id=None):
    """Extract comments from a PR, optionally filtered by user and/or review ID"""
    repo_flag = f"--repo {repo}" if repo else ""
    
    comments = []
    
    if review_id:
        # Get specific review
        print(f"Fetching specific review {review_id}...")
        review_data = run_gh_api(f"/repos/{repo}/pulls/{pr_number}/reviews/{review_id}")
        
        if review_data and review_data.get('body'):
            comments.append({
                'type': 'Specific Review',
                'author': review_data['user']['login'],
                'content': review_data['body'],
                'state': review_data['state'],
                'file': None,
                'line': None,
                'review_id': review_id
            })
        
        # Get review comments for this specific review
        review_comments = run_gh_api(f"/repos/{repo}/pulls/{pr_number}/reviews/{review_id}/comments")
        
        for comment in review_comments:
            comments.append({
                'type': 'Inline Comment',
                'author': comment['user']['login'],
                'content': comment['body'],
                'file': comment.get('path'),
                'line': comment.get('line') or comment.get('original_line'),
                'diff_side': comment.get('side'),
                'review_id': review_id
            })
    
    else:
        # Get all PR data
        pr_data = run_gh_command(f"gh pr view {pr_number} {repo_flag} --json reviews,comments,reviewThreads,title,body,author")
        
        # Add PR description as context (only if no specific user filter)
        if not username and pr_data.get('title') and pr_data.get('body'):
            comments.append({
                'type': 'PR Description',
                'author': pr_data['author']['login'],
                'content': f"**{pr_data['title']}**\n\n{pr_data['body']}",
                'file': None,
                'line': None
            })
        
        # Extract review comments
        for review in pr_data.get('reviews', []):
            if username and review['author']['login'] != username:
                continue
                
            if review['body'] and review['body'].strip():
                comments.append({
                    'type': 'Review',
                    'author': review['author']['login'],
                    'content': review['body'],
                    'state': review['state'],
                    'file': None,
                    'line': None,
                    'review_id': review.get('id')
                })
        
        # Extract general comments
        for comment in pr_data.get('comments', []):
            if username and comment['author']['login'] != username:
                continue
                
            if comment['body'] and comment['body'].strip():
                comments.append({
                    'type': 'General Comment',
                    'author': comment['author']['login'],
                    'content': comment['body'],
                    'file': None,
                    'line': None
                })
        
        # Extract inline/file comments
        for thread in pr_data.get('reviewThreads', []):
            if thread.get('comments'):
                for comment in thread['comments']:
                    if username and comment['author']['login'] != username:
                        continue
                        
                    comments.append({
                        'type': 'Inline Comment',
                        'author': comment['author']['login'],
                        'content': comment['body'],
                        'file': thread.get('path'),
                        'line': thread.get('line'),
                        'diff_side': thread.get('side')
                    })
    
    return comments

def format_prompt(comments, pr_number, repo, username=None, review_id=None):
    """Format comments into a Copilot prompt"""
    
    prompt = f"""# Code Review Fixes for PR #{pr_number}

Repository: {repo}
PR: https://github.com/{repo}/pull/{pr_number}
"""
    
    if username:
        prompt += f"Reviewer: @{username}\n"
    
    if review_id:
        prompt += f"Review ID: {review_id}\n"
        prompt += f"Review Link: https://github.com/{repo}/pull/{pr_number}#pullrequestreview-{review_id}\n"
    
    prompt += "\nI need help addressing the following review comments and implementing the requested changes:\n\n"
    
    # Group comments by type
    review_comments = [c for c in comments if c['type'] in ['Review', 'Specific Review'] and c.get('state') in ['CHANGES_REQUESTED', 'COMMENTED', 'APPROVED']]
    inline_comments = [c for c in comments if c['type'] == 'Inline Comment']
    general_comments = [c for c in comments if c['type'] == 'General Comment']
    
    # Add review comments
    if review_comments:
        prompt += "## 🔍 Review Comments\n\n"
        for comment in review_comments:
            state_emoji = "🔴" if comment.get('state') == 'CHANGES_REQUESTED' else "💬"
            prompt += f"{state_emoji} **@{comment['author']}** ({comment.get('state', 'COMMENTED')}):\n"
            if comment.get('review_id'):
                prompt += f"*Review ID: {comment['review_id']}*\n\n"
            prompt += f"{comment['content']}\n\n---\n\n"
    
    # Add inline comments
    if inline_comments:
        prompt += "## 📝 Inline Code Comments\n\n"
        for comment in inline_comments:
            file_info = f" in `{comment['file']}`" if comment['file'] else ""
            line_info = f" (line {comment['line']})" if comment['line'] else ""
            prompt += f"📍 **@{comment['author']}**{file_info}{line_info}:\n"
            prompt += f"{comment['content']}\n\n---\n\n"
    
    # Add general comments
    if general_comments:
        prompt += "## 💬 General Comments\n\n"
        for comment in general_comments:
            prompt += f"**@{comment['author']}**:\n"
            prompt += f"{comment['content']}\n\n---\n\n"
    
    # Add instructions
    prompt += f"""## 🎯 What I Need Help With

Please help me address these review comments systematically:

1. **Analyze** each comment and identify the specific issues raised
2. **Prioritize** the changes needed (critical bugs → improvements → style)  
3. **Implement** specific code changes to address each concern
4. **Explain** how each change addresses the reviewer's feedback

**Working Mode Instructions:**
- Use **Edit Mode** for direct file modifications across multiple files
- Use **@workspace** to understand the full codebase context
- Start with the most critical issues first
- Make changes incrementally and explain each one

## Context:
- PR Link: https://github.com/{repo}/pull/{pr_number}
- Repository: {repo}
"""
    
    if username:
        prompt += f"- Comments filtered by: @{username}\n"
    
    if review_id:
        prompt += f"- Specific review: https://github.com/{repo}/pull/{pr_number}#pullrequestreview-{review_id}\n"
    
    prompt += """
Focus on actionable changes I can implement immediately. If any comment is unclear, please ask for clarification on what specific change is needed.

Let's work through these systematically, starting with the most critical issues.
"""
    
    return prompt

def main():
    parser = argparse.ArgumentParser(
        description='Extract PR comments for Copilot',
        epilog="""
Examples:
  %(prog)s https://github.com/cbsi-cmg/ngcms/pull/937#pullrequestreview-2940750819 --user john-doe --chat
  %(prog)s 937 --user jane-smith --repo owner/repo --open --chat  
  %(prog)s https://github.com/owner/repo/pull/123 --no-copy
  %(prog)s 456 --repo owner/repo --output custom_prompt.md
        """,
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument('input', help='Pull request URL or number')
    parser.add_argument('--user', '-u', help='Filter comments by username')
    parser.add_argument('--repo', '-r', help='Repository (owner/name) - only needed if using PR number')
    parser.add_argument('--output', '-o', help='Output file', default=None)
    parser.add_argument('--copy', action='store_true', help='Copy to clipboard')
    parser.add_argument('--open', action='store_true', help='Open in VSCode', default=True)
    parser.add_argument('--no-copy', action='store_true', help='Skip auto-copying to clipboard')
    parser.add_argument('--chat', action='store_true', help='Try to open Copilot Chat automatically')
    
    args = parser.parse_args()
    
    try:
        # Parse input
        parsed_repo, pr_number, review_id = parse_pr_url(args.input)
        
        # Use parsed repo or provided repo
        repo = parsed_repo or args.repo
        if not repo:
            # Try to get current repo
            try:
                result = subprocess.run(['gh', 'repo', 'view', '--json', 'nameWithOwner'], 
                                     capture_output=True, text=True, check=True)
                repo_data = json.loads(result.stdout)
                repo = repo_data['nameWithOwner']
            except:
                print("Error: No repository specified and couldn't detect current repo")
                print("Use --repo owner/name or run from within a git repository")
                sys.exit(1)
        
        print(f"📋 Extracting comments from PR #{pr_number} in {repo}")
        if args.user:
            print(f"👤 Filtering by user: @{args.user}")
        if review_id:
            print(f"🔍 Focusing on review ID: {review_id}")
        
        # Extract comments
        comments = extract_pr_comments(pr_number, repo, args.user, review_id)
        
        if not comments:
            print("❌ No comments found matching the criteria")
            print("Check:")
            print(f"  - Username spelling: {args.user}")
            print(f"  - Review ID: {review_id}")
            print(f"  - Repository access permissions for: {repo}")
            sys.exit(1)
        
        # Format prompt
        prompt = format_prompt(comments, pr_number, repo, args.user, review_id)
        
        # Generate filename
        output_file = args.output or f"copilot_prompt_pr_{pr_number}"
        if args.user:
            output_file += f"_{args.user}"
        if review_id:
            output_file += f"_review_{review_id}"
        output_file += ".md"
        
        # Save to file
        Path(output_file).write_text(prompt)
        print(f"💾 Prompt saved to: {output_file}")
        
        # Copy to clipboard if requested
        if args.copy:
            try:
                import pyperclip
                pyperclip.copy(prompt)
                print("📋 Prompt copied to clipboard!")
            except ImportError:
                print("📦 Install pyperclip to use --copy: pip install pyperclip")
        
        # Open in VSCode if available and requested
        if args.open:
            try:
                # Get all files from PR diff
                all_files = []
                try:
                    result = subprocess.run(['gh', 'pr', 'diff', pr_number, '--repo', repo, '--name-only'], 
                                          capture_output=True, text=True, check=True)
                    pr_files = [f.strip() for f in result.stdout.strip().split('\n') if f.strip()]
                    
                    # Filter out non-existent files and add to list
                    for file in pr_files:
                        if Path(file).exists():
                            all_files.append(file)
                    
                    if all_files:
                        print(f"📂 Found {len(all_files)} files from PR diff")
                    else:
                        print("📂 No PR files found in current directory")
                        
                except Exception as e:
                    print(f"⚠️  Could not get PR files: {e}")
                
                # Open VSCode with all files
                vscode_files = [output_file] + all_files
                
                # For Cursor/VSCode, open with workspace context
                if all_files:
                    # Try to open in a workspace context
                    subprocess.run(['code', '.'] + vscode_files, check=True)
                    print(f"📝 Opened workspace with {len(vscode_files)} files")
                else:
                    # Fallback to just opening the prompt file
                    subprocess.run(['code', output_file], check=True)
                    print("📝 Opened prompt file in VSCode")
                
                # Auto-copy to clipboard for easy pasting into Copilot (unless disabled)
                if not args.no_copy:
                    try:
                        import pyperclip
                        pyperclip.copy(prompt)
                        print("📋 Prompt auto-copied to clipboard - paste into Copilot Chat!")
                    except ImportError:
                        print("💡 Install pyperclip for auto-clipboard: pip install pyperclip")
                
                # Try to open Copilot Chat automatically if requested
                if args.chat:
                    try:
                        # Try to trigger Copilot Chat via VSCode command
                        import time
                        time.sleep(2)  # Give VSCode time to fully open
                        
                        # Use VSCode command to open Copilot Chat
                        subprocess.run([
                            'code', '--command', 'workbench.panel.chat.view.copilot.focus'
                        ], check=False)
                        print("🤖 Attempted to open Copilot Chat automatically")
                    except Exception as e:
                        print(f"⚠️  Could not auto-open Copilot Chat: {e}")
                        print("   Manually open with Ctrl+Alt+I / Cmd+Ctrl+I")
                
                # Create a .copilot-instructions.md file for better context
                copilot_instructions = f"""# PR Review Context

This workspace contains files from PR #{pr_number} in {repo}.

## Files to Review:
{chr(10).join(f'- {file}' for file in all_files) if all_files else '- No files found in current directory'}

## Next Steps:
1. The prompt has been copied to your clipboard
2. Open Copilot Chat (Ctrl+Alt+I or Cmd+Ctrl+I)
3. Paste the prompt to start the code review process
4. Use @workspace to give Copilot full context of the codebase

## Tip:
Use "Edit Mode" in Copilot Chat for direct file modifications across multiple files.
"""
                
                copilot_file = Path(".copilot-instructions.md")
                copilot_file.write_text(copilot_instructions)
                print("📋 Created .copilot-instructions.md for workspace context")
                    
            except (subprocess.CalledProcessError, FileNotFoundError):
                print("📝 VSCode not available, prompt saved to file")
        
        print(f"\n📊 Summary:")
        print(f"  - Extracted {len(comments)} comments")
        
        comment_types = {}
        for comment in comments:
            comment_types[comment['type']] = comment_types.get(comment['type'], 0) + 1
        
        for comment_type, count in comment_types.items():
            print(f"  - {comment_type}: {count}")
        
        print(f"\n🎯 Next steps:")
        if args.open:
            print(f"1. VSCode/Cursor is now open with all relevant files")
            print(f"2. Open Copilot Chat (Ctrl+Alt+I / Cmd+Ctrl+I)")
            print(f"3. Paste the prompt (already copied to clipboard)")
            print(f"4. Use 'Edit Mode' for direct file modifications")
            print(f"\n💡 Pro tips:")
            print(f"   • Use '@workspace' for full codebase context")
            print(f"   • Check .copilot-instructions.md for workspace context")
            print(f"   • Switch to 'Agent Mode' for autonomous multi-file edits")
        else:
            print(f"1. Review the generated prompt in {output_file}")
            print(f"2. Copy-paste it into GitHub Copilot Chat in VSCode")
            print(f"3. Ask Copilot to work through the issues systematically")
            print(f"\n💡 Pro tip: Use '@workspace' in Copilot Chat for more context about your codebase")
        
    except ValueError as e:
        print(f"❌ Error: {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n⏹️  Interrupted by user")
        sys.exit(1)

if __name__ == "__main__":
    main()

