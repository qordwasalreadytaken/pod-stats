#!/bin/bash

# Archive System Setup Script for pod-stats
# Run this script to ensure all necessary directories and files are in place

echo "🔧 Setting up archive automation system..."

# Create necessary directories
echo "📁 Creating required directories..."
mkdir -p Season
mkdir -p recovery_points
mkdir -p charts
mkdir -p armory/font
mkdir -p css
mkdir -p js

# Create placeholder for avqest.ttf font if it doesn't exist
if [ ! -f armory/font/avqest.ttf ]; then
    echo "📝 Creating font placeholder..."
    touch armory/font/avqest.ttf
    echo "⚠️  Note: You may need to add the actual avqest.ttf font file"
fi

# Create archive config if it doesn't exist
if [ ! -f archive_config.json ]; then
    echo "⚙️  Creating default archive configuration..."
    cat > archive_config.json << 'EOF'
{
    "archive_settings": {
        "default_season": "auto-detect",
        "archive_base_path": "Season",
        "recovery_points_path": "recovery_points",
        "charts_path": "charts",
        "enable_recovery": true,
        "max_recovery_points": 10,
        "archive_compression": false
    },
    "quality_thresholds": {
        "min_characters": 100,
        "min_charts": 10,
        "min_pages": 5,
        "max_errors": 0
    },
    "automation": {
        "monthly_day": 28,
        "force_on_manual": false,
        "skip_frozen_seasons": true
    }
}
EOF
fi

# Verify key script files exist
echo "🔍 Verifying script files..."
REQUIRED_FILES=(
    "scripts/api_integration.py"
    "scripts/generate_pages.py"
    "scripts/modules/shared_utils.py"
    "scripts/modules/class_pages.py"
    "scripts/modules/home_page.py"
)

MISSING_FILES=()
for file in "${REQUIRED_FILES[@]}"; do
    if [ ! -f "$file" ]; then
        MISSING_FILES+=("$file")
    fi
done

if [ ${#MISSING_FILES[@]} -eq 0 ]; then
    echo "✅ All required script files found"
else
    echo "❌ Missing required files:"
    for file in "${MISSING_FILES[@]}"; do
        echo "   - $file"
    done
    echo "⚠️  Please ensure all files are copied from the main analytics directory"
fi

# Verify workflow files exist
echo "🔍 Verifying GitHub Actions workflows..."
WORKFLOW_FILES=(
    ".github/workflows/monthly-archive.yml"
    ".github/workflows/manual-archive.yml"
    ".github/workflows/daily-update-protected.yml"
    ".github/workflows/force-update.yml"
)

MISSING_WORKFLOWS=()
for workflow in "${WORKFLOW_FILES[@]}"; do
    if [ ! -f "$workflow" ]; then
        MISSING_WORKFLOWS+=("$workflow")
    fi
done

if [ ${#MISSING_WORKFLOWS[@]} -eq 0 ]; then
    echo "✅ All workflow files found"
else
    echo "❌ Missing workflow files:"
    for workflow in "${MISSING_WORKFLOWS[@]}"; do
        echo "   - $workflow"
    done
fi

# Check Python requirements
if [ -f "scripts/requirements.txt" ]; then
    echo "📦 Python requirements file found"
    echo "💡 Install requirements with: pip install -r scripts/requirements.txt"
else
    echo "⚠️  Python requirements file not found"
fi

echo ""
echo "🎉 Archive system setup complete!"
echo ""
echo "📋 Next steps:"
echo "1. Install Python dependencies: pip install -r scripts/requirements.txt"
echo "2. Test the system: cd scripts && python api_integration.py test"
echo "3. Check workflows in GitHub Actions tab"
echo "4. Review .github/workflows/README.md for detailed information"
echo ""
echo "🔧 Manual commands available:"
echo "   Monthly archive: python scripts/api_integration.py archive monthly"
echo "   Final archive:   python scripts/api_integration.py archive final --force"
echo "   Force pages:     python scripts/generate_pages.py --page all --mode sc --force"
echo "   Help:            python scripts/api_integration.py help"