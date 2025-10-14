#!/bin/bash

################################################################################
# push_to_git.sh - Simplified Git Push Script for App Migrator
#
# Purpose: Easy automated Git push with smart defaults
# Version: 3.0.0
# Date: October 12, 2025
# Author: MiniMax Agent
#
# Usage: 
#   ./push_to_git.sh                    # Auto-commit with smart message
#   ./push_to_git.sh "commit message"   # Custom commit message
#   ./push_to_git.sh "message" v1.0.0   # Custom message with tag
################################################################################

set -e  # Exit on error

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
REMOTE="origin"
BRANCH="main"
REPO_URL="git@github.com:rogerboy38/app_migrator.git"

################################################################################
# Simplified Functions
################################################################################

print_status() {
    echo -e "${BLUE}➤${NC} $1"
}

print_success() {
    echo -e "${GREEN}✓${NC} $1"
}

print_error() {
    echo -e "${RED}✗${NC} $1"
}

check_requirements() {
    if [ ! -d ".git" ]; then
        print_error "Not a git repository"
        exit 1
    fi

    # Set git config if missing
    if ! git config user.name > /dev/null; then
        git config user.name "Git User"
    fi
    if ! git config user.email > /dev/null; then
        git config user.email "user@example.com"
    fi

    # Add remote if missing
    if ! git remote get-url "$REMOTE" > /dev/null 2>&1; then
        git remote add "$REMOTE" "$REPO_URL"
    fi
}

auto_commit_message() {
    local changed_files=$(git status --porcelain | wc -l)
    local modified_files=$(git diff --name-only | head -5 | tr '\n' ',' | sed 's/,/, /g')
    
    if [ -n "$1" ]; then
        echo "$1"
    else
        echo "Update: ${modified_files%, } and $((changed_files - 1)) other files"
    fi
}

sync_with_remote() {
    print_status "Syncing with remote..."
    git fetch "$REMOTE"
    
    # Check if we need to pull
    if git status | grep -q "behind"; then
        print_status "Pulling latest changes..."
        git pull --rebase "$REMOTE" "$BRANCH"
    fi
}

simple_push() {
    local commit_msg="$1"
    local tag_name="$2"
    
    print_status "Starting Git push process..."
    
    # Check requirements
    check_requirements
    
    # Sync with remote first
    sync_with_remote
    
    # Show changes
    print_status "Changes to be committed:"
    git status --short
    
    # Stage all changes
    if [ -n "$(git status --porcelain)" ]; then
        git add .
        print_success "All changes staged"
        
        # Commit
        git commit -m "$commit_msg"
        print_success "Changes committed: $commit_msg"
    else
        print_status "No changes to commit"
    fi
    
    # Create tag if specified
    if [ -n "$tag_name" ]; then
        git tag -a "$tag_name" -m "Release $tag_name"
        print_success "Tag created: $tag_name"
    fi
    
    # Push everything
    print_status "Pushing to $REMOTE/$BRANCH..."
    git push "$REMOTE" "$BRANCH"
    
    # Push tag if created
    if [ -n "$tag_name" ]; then
        git push "$REMOTE" "$tag_name"
    fi
    
    # Show summary
    echo ""
    print_success "Push completed successfully!"
    print_success "Branch: $BRANCH"
    print_success "Commit: $(git log -1 --pretty=format:'%h')"
    [ -n "$tag_name" ] && print_success "Tag: $tag_name"
    echo -e "View repo: ${BLUE}https://github.com/rogerboy38/app_migrator${NC}"
}

################################################################################
# Main Execution
################################################################################

main() {
    # Generate commit message
    COMMIT_MSG=$(auto_commit_message "$1")
    TAG_NAME="$2"
    
    # Show header
    echo -e "${BLUE}App Migrator - Quick Git Push${NC}"
    echo "========================================"
    
    # Execute push
    simple_push "$COMMIT_MSG" "$TAG_NAME"
}

# Run main function
main "$@"
