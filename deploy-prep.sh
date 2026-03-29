#!/bin/bash

# Quick deployment script for Streamlit Cloud
# This helps you get your app ready for GitHub and Streamlit Cloud

echo "🚀 Preparing Yahoo Fantasy Pitcher Tracker for deployment..."
echo ""

# Check if git is initialized
if [ ! -d .git ]; then
    echo "📦 Initializing git repository..."
    git init
    echo "✅ Git initialized"
else
    echo "✅ Git already initialized"
fi

# Create git ignore if it doesn't exist
if [ ! -f .gitignore ]; then
    echo "⚠️  .gitignore not found (this should exist)"
fi

# Check for .env file
if [ -f ../.env ]; then
    echo "✅ Found parent .env file"
    echo "⚠️  Remember: You'll need to copy these credentials to Streamlit Cloud secrets"
else
    echo "⚠️  No .env file found - make sure you have Yahoo API credentials"
fi

# Show current status
echo ""
echo "📋 Current status:"
git status --short

echo ""
echo "📝 Next steps:"
echo "1. Review files to commit with: git status"
echo "2. Add files: git add ."
echo "3. Commit: git commit -m 'Initial commit - Yahoo Fantasy Pitcher Tracker'"
echo "4. Create GitHub repo at: https://github.com/new"
echo "5. Add remote: git remote add origin https://github.com/YOUR_USERNAME/YOUR_REPO.git"
echo "6. Push: git push -u origin main"
echo "7. Deploy at: https://share.streamlit.io"
echo ""
echo "📖 Full instructions: See DEPLOYMENT.md"
