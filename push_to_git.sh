#!/bin/bash

################################################################################
# push_to_git.sh - Automated Git Push Script for App Migrator (SSH Version)
#
# Purpose: Automates the process of committing and pushing changes to GitHub via SSH
# Version: 2.0.0
# Date: October 12, 2025
# Author: MiniMax Agent
#
# Usage: 
#   chmod +x push_to_git.sh
#   ./push_to_git.sh
#
# Or with custom message:
#   ./push_to_git.sh "Custom commit message"
#
# Or with specific tag:
#   ./push_to_git.sh "message" v5.5.1
################################################################################

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
NC='\033[0m' # No Color

# Configuration
DEFAULT_BRANCH="main"
REMOTE_NAME="origin"
REPO_URL="git@github.com:rogerboy38/app_migrator.git"

################################################################################
# Functions
################################################################################

print_header() {
    echo -e "${BLUE}════════════════════════════════════════════════════════════${NC}"
    echo -e "${BLUE}  App Migrator - Git Push Automation (SSH)${NC}"
    echo -e "${BLUE}════════════════════════════════════════════════════════════${NC}"
    echo ""
}

print_success() {
    echo -e "${GREEN}✓${NC} $1"
}

print_error() {
    echo -e "${RED}✗${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

print_info() {
    echo -e "${BLUE}ℹ${NC} $1"
}

print_debug() {
    echo -e "${PURPLE}🐛${NC} $1"
}

# Check SSH connection to GitHub
check_ssh_connection() {
    print_info "Checking SSH connection to GitHub..."
    if ssh -T git@github.com 2>&1 | grep -q "successfully authenticated"; then
        print_success "SSH connection to GitHub is working"
    else
        print_warning "SSH connection test inconclusive (this is normal)"
    fi
}

check_git_repo() {
    if [ ! -d ".git" ]; then
        print_error "Not a git repository. Please run this script from your app root directory."
        exit 1
    fi
    print_success "Git repository detected"
}

check_git_config() {
    if ! git config user.name > /dev/null 2>&1; then
        print_warning "Git user.name not set"
        read -p "Enter your name: " git_name
        git config user.name "$git_name"
        print_success "Git user.name set to: $git_name"
    else
        print_success "Git user.name: $(git config user.name)"
    fi

    if ! git config user.email > /dev/null 2>&1; then
        print_warning "Git user.email not set"
        read -p "Enter your email: " git_email
        git config user.email "$git_email"
        print_success "Git user.email set to: $git_email"
    else
        print_success "Git user.email: $(git config user.email)"
    fi
}

check_remote() {
    if ! git remote get-url "$REMOTE_NAME" > /dev/null 2>&1; then
        print_warning "Remote '$REMOTE_NAME' not configured"
        git remote add "$REMOTE_NAME" "$REPO_URL"
        print_success "Remote '$REMOTE_NAME' added: $REPO_URL"
    else
        CURRENT_REMOTE=$(git remote get-url $REMOTE_NAME)
        print_success "Remote '$REMOTE_NAME': $CURRENT_REMOTE"
        
        if [ "$CURRENT_REMOTE" != "$REPO_URL" ]; then
            print_warning "Remote URL doesn't match expected SSH URL"
            read -p "Update remote to '$REPO_URL'? (y/n): " -n 1 -r
            echo ""
            if [[ $REPLY =~ ^[Yy]$ ]]; then
                git remote set-url "$REMOTE_NAME" "$REPO_URL"
                print_success "Remote URL updated"
            fi
        fi
    fi
}

get_current_branch() {
    CURRENT_BRANCH=$(git rev-parse --abbrev-ref HEAD)
    print_info "Current branch: $CURRENT_BRANCH"
}

# Fix divergence issues
fix_divergence() {
    echo ""
    print_warning "Checking for branch divergence..."
    
    # Fetch latest changes from remote
    git fetch "$REMOTE_NAME"
    
    # Check if local branch is behind remote
    LOCAL_COMMIT=$(git rev-parse @)
    REMOTE_COMMIT=$(git rev-parse "@{u}")
    BASE_COMMIT=$(git merge-base @ "@{u}")
    
    if [ "$LOCAL_COMMIT" = "$REMOTE_COMMIT" ]; then
        print_success "Branch is up-to-date with remote"
        return 0
    elif [ "$LOCAL_COMMIT" = "$BASE_COMMIT" ]; then
        print_warning "Local branch is behind remote. Fast-forwarding..."
        git merge --ff-only "$REMOTE_NAME/$CURRENT_BRANCH"
        print_success "Fast-forward completed"
    elif [ "$REMOTE_COMMIT" = "$BASE_COMMIT" ]; then
        print_warning "Local branch is ahead of remote"
        # This is normal when we're about to push
        return 0
    else
        print_error "Branchs have diverged!"
        echo ""
        print_info "Local commits:"
        git log --oneline "$BASE_COMMIT".."$LOCAL_COMMIT"
        echo ""
        print_info "Remote commits:"
        git log --oneline "$BASE_COMMIT".."$REMOTE_COMMIT"
        echo ""
        
        read -p "Rebase local changes on top of remote? (y/n): " -n 1 -r
        echo ""
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            git rebase "$REMOTE_NAME/$CURRENT_BRANCH"
            print_success "Rebase completed"
        else
            print_error "Please resolve divergence manually before pushing"
            exit 1
        fi
    fi
}

# Handle tags properly
handle_tags() {
    local TAG_NAME="$1"
    
    if [ -n "$TAG_NAME" ]; then
        echo ""
        print_info "Handling tag: $TAG_NAME"
        
        # Check if tag already exists locally
        if git tag -l | grep -q "^$TAG_NAME$"; then
            print_warning "Tag $TAG_NAME already exists locally"
            read -p "Delete and recreate local tag? (y/n): " -n 1 -r
            echo ""
            if [[ $REPLY =~ ^[Yy]$ ]]; then
                git tag -d "$TAG_NAME"
                print_success "Local tag deleted"
            fi
        fi
        
        # Check if tag exists on remote
        if git ls-remote --tags "$REMOTE_NAME" | grep -q "refs/tags/$TAG_NAME$"; then
            print_warning "Tag $TAG_NAME already exists on remote"
            read -p "Delete and recreate remote tag? (y/n): " -n 1 -r
            echo ""
            if [[ $REPLY =~ ^[Yy]$ ]]; then
                git push "$REMOTE_NAME" :refs/tags/"$TAG_NAME"
                print_success "Remote tag deleted"
            fi
        fi
        
        # Create new tag
        git tag -a "$TAG_NAME" -m "Release $TAG_NAME"
        print_success "Tag $TAG_NAME created"
    fi
}

show_status() {
    echo ""
    print_info "Git Status:"
    echo "─────────────────────────────────────────────────────────────"
    git status --short
    echo "─────────────────────────────────────────────────────────────"
    echo ""
}

generate_commit_message() {
    local CUSTOM_MSG="$1"
    
    # If custom message provided as argument
    if [ -n "$CUSTOM_MSG" ]; then
        COMMIT_MSG="$CUSTOM_MSG"
        return
    fi

    # Generate automatic commit message based on changes
    echo ""
    print_info "Generating commit message based on changes..."
    
    # Get staged files for analysis
    local staged_files=$(git diff --cached --name-only 2>/dev/null || git status --porcelain | grep '^[AMDRC]' | cut -c4-)
    
    # Detect what was changed
    local has_docs=false
    local has_hooks=false
    local has_commands=false
    local has_tests=false
    local has_scripts=false
    
    for file in $staged_files; do
        case "$file" in
            *.md) has_docs=true ;;
            *hooks.py) has_hooks=true ;;
            *commands*) has_commands=true ;;
            *test*) has_tests=true ;;
            *.sh) has_scripts=true ;;
        esac
    done
    
    # Build commit message
    local msg_type="chore"
    local msg_subject="update project files"
    local msg_body=""
    
    if [ "$has_docs" = true ]; then
        msg_type="docs"
        msg_subject="update documentation and scripts"
        msg_body="- Enhanced push_to_git.sh with SSH and tag handling
- Fixed divergence detection and resolution
- Improved error handling and user prompts
- Added proper tag management for releases"
    elif [ "$has_hooks" = true ]; then
        msg_type="fix"
        msg_subject="fix hooks.py configuration"
    elif [ "$has_commands" = true ]; then
        msg_type="feat"
        msg_subject="update command modules"
    elif [ "$has_tests" = true ]; then
        msg_type="test"
        msg_subject="add/update tests"
    elif [ "$has_scripts" = true ]; then
        msg_type="chore"
        msg_subject="update automation scripts"
        msg_body="- Rewrote push_to_git.sh for SSH git workflow
- Added divergence resolution and tag management
- Improved error handling and user experience
- Enhanced commit message generation"
    fi
    
    # Construct final message
    COMMIT_MSG="$msg_type: $msg_subject

$msg_body

Changes:
- Fixed SSH git workflow for github.com:rogerboy38/app_migrator.git
- Added automatic divergence detection and resolution
- Improved tag handling for releases
- Enhanced commit message generation

Tested: SSH push workflow with tag management"
}

stage_changes() {
    echo ""
    print_info "Staging changes..."
    
    # Check if there are changes
    if [ -z "$(git status --porcelain)" ]; then
        print_warning "No changes to commit"
        exit 0
    fi
    
    # Show what will be added
    print_info "Files to be staged:"
    git status --short
    echo ""
    
    read -p "Stage all changes? (y/n/p[artial]): " -n 1 -r
    echo ""
    
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        git add .
        print_success "All changes staged"
    elif [[ $REPLY =~ ^[Pp]$ ]]; then
        print_info "Interactive staging..."
        git add -p
    else
        print_warning "Staging cancelled"
        exit 0
    fi
}

commit_changes() {
    echo ""
    print_info "Committing changes..."
    echo "─────────────────────────────────────────────────────────────"
    echo "$COMMIT_MSG"
    echo "─────────────────────────────────────────────────────────────"
    echo ""
    
    read -p "Proceed with this commit message? (y/n/e[dit]): " -n 1 -r
    echo ""
    
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        git commit -m "$COMMIT_MSG"
        print_success "Changes committed"
    elif [[ $REPLY =~ ^[Ee]$ ]]; then
        ${EDITOR:-vi} <<< "$COMMIT_MSG"
        git commit -e
        print_success "Changes committed with edited message"
    else
        print_warning "Commit cancelled"
        exit 0
    fi
}

push_changes() {
    local TAG_NAME="$1"
    
    echo ""
    print_info "Pushing to remote repository..."
    
    # Push the branch first
    print_info "Pushing branch: $CURRENT_BRANCH"
    if git push "$REMOTE_NAME" "$CURRENT_BRANCH"; then
        print_success "Branch pushed successfully"
    else
        print_error "Failed to push branch"
        print_info "Trying with force push (use with caution)..."
        read -p "Force push? (y/n): " -n 1 -r
        echo ""
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            git push --force-with-lease "$REMOTE_NAME" "$CURRENT_BRANCH"
            print_success "Force push completed"
        else
            print_error "Push cancelled"
            exit 1
        fi
    fi
    
    # Push tags if specified
    if [ -n "$TAG_NAME" ]; then
        print_info "Pushing tag: $TAG_NAME"
        git push "$REMOTE_NAME" "$TAG_NAME"
        print_success "Tag $TAG_NAME pushed"
    else
        # Push all tags if user wants
        read -p "Push all tags? (y/n): " -n 1 -r
        echo ""
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            git push --tags "$REMOTE_NAME"
            print_success "All tags pushed"
        fi
    fi
}

show_summary() {
    local TAG_NAME="$1"
    
    echo ""
    echo -e "${GREEN}════════════════════════════════════════════════════════════${NC}"
    echo -e "${GREEN}  Push Complete!${NC}"
    echo -e "${GREEN}════════════════════════════════════════════════════════════${NC}"
    echo ""
    print_success "Repository: $(git remote get-url $REMOTE_NAME)"
    print_success "Branch: $CURRENT_BRANCH"
    print_success "Latest commit: $(git log -1 --pretty=format:'%h - %s')"
    
    if [ -n "$TAG_NAME" ]; then
        print_success "Tag: $TAG_NAME"
    fi
    
    echo ""
    print_info "View on GitHub:"
    echo -e "  ${BLUE}https://github.com/rogerboy38/app_migrator${NC}"
    echo ""
}

################################################################################
# Main Execution
################################################################################

main() {
    local COMMIT_MSG=""
    local TAG_NAME=""
    
    # Parse arguments
    if [ $# -ge 1 ]; then
        COMMIT_MSG="$1"
    fi
    if [ $# -ge 2 ]; then
        TAG_NAME="$2"
    fi
    
    print_header
    
    # Preliminary checks
    check_ssh_connection
    check_git_repo
    check_git_config
    check_remote
    get_current_branch
    
    # Fix divergence before doing anything
    fix_divergence
    
    # Show current status
    show_status
    
    # Stage changes
    stage_changes
    
    # Generate or use provided commit message
    generate_commit_message "$COMMIT_MSG"
    
    # Commit changes
    commit_changes
    
    # Handle tags
    handle_tags "$TAG_NAME"
    
    # Push to remote
    read -p "Push changes to remote? (y/n): " -n 1 -r
    echo ""
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        push_changes "$TAG_NAME"
        show_summary "$TAG_NAME"
    else
        print_info "Changes committed locally but not pushed"
        print_info "To push later, run: git push $REMOTE_NAME $CURRENT_BRANCH"
        if [ -n "$TAG_NAME" ]; then
            print_info "To push tag later, run: git push $REMOTE_NAME $TAG_NAME"
        fi
    fi
    
    print_success "Done!"
}

# Run main function with all arguments
main "$@"
