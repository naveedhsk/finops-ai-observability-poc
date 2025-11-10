#!/bin/bash

# Quick GitHub Push Script
# Usage: ./push-to-github.sh YOUR_GITHUB_USERNAME

if [ -z "$1" ]; then
    echo "❌ Error: Please provide your GitHub username"
    echo "Usage: ./push-to-github.sh YOUR_GITHUB_USERNAME"
    exit 1
fi

USERNAME=$1
REPO_NAME="finops-ai-observability-poc"

echo "🚀 Pushing to GitHub..."
echo "Repository: https://github.com/$USERNAME/$REPO_NAME"
echo ""

# Add all files
git add .

# Commit
git commit -m "Initial commit: FinOps AI Observability POC - ML-powered AWS cost anomaly detection"

# Add remote (will fail if already exists, that's okay)
git remote add origin https://github.com/$USERNAME/$REPO_NAME.git 2>/dev/null || true

# Set main branch
git branch -M main

# Push
echo ""
echo "📤 Pushing to GitHub..."
git push -u origin main

echo ""
echo "✅ Done!"
echo "🌐 View at: https://github.com/$USERNAME/$REPO_NAME"
echo ""
echo "💡 Next steps:"
echo "   1. Go to https://github.com/$USERNAME/$REPO_NAME"
echo "   2. Verify everything looks good"
echo "   3. Post on LinkedIn with the link!"
echo ""
