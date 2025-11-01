# Path of Diablo Archive Automation System

## 📋 Table of Contents
- [Overview](#overview)
- [System Architecture](#system-architecture)
- [Prerequisites](#prerequisites)
- [Installation & Setup](#installation--setup)
- [Configuration](#configuration)
- [Usage](#usage)
- [Archive Structure](#archive-structure)
- [Monitoring & Metadata](#monitoring--metadata)
- [Troubleshooting](#troubleshooting)
- [Maintenance](#maintenance)
- [Advanced Features](#advanced-features)

---

## 🎯 Overview

The **Archive Automation System** is a comprehensive solution for automatically creating historical snapshots of Path of Diablo ladder data. It runs monthly on the 28th day to capture end-of-month statistics and creates complete archives including:

- **HTML Pages**: Character statistics, class analysis, item distribution
- **Interactive Charts**: 28+ data visualizations and analytics
- **Historical Data**: JSON snapshots of ladder data
- **Metadata**: Quality metrics, performance analytics, system information

### Key Features
- ✅ **Automated Monthly Execution** (28th of each month)
- ✅ **Season Detection** (Active vs Post-Season handling)
- ✅ **Comprehensive Error Handling** (5 error types, 3x retry, recovery points)
- ✅ **Quality Scoring** (Data balance, completeness metrics)
- ✅ **Performance Analytics** (Processing speed, efficiency tracking)
- ✅ **Banner Injection** (5 fallback methods for historical context)
- ✅ **Chart Generation** (Isolated from live site)
- ✅ **Metadata Tracking** (400+ files, system info, historical trends)

---

## 🏗️ System Architecture

### Pipeline Overview
```
1. Season Detection    → Determine season state and archive type
2. JSON Validation     → Verify data quality and structure  
3. Folder Creation     → Generate Season/X/Month structure
4. Data Processing     → Copy ladder files, generate content
5. HTML Conversion     → Create 21+ archive pages
6. Banner Injection    → Add historical context banners
7. Final Creation      → Generate metadata and complete archive
```

### Key Components
- **`scripts/api_integration.py`**: Main automation engine (4400+ lines)
- **Error Handling Framework**: 5 error classes with retry mechanisms
- **Archive Pipeline**: 7-step orchestrated process
- **Metadata System**: Comprehensive tracking and analytics
- **Cron Integration**: Automatic monthly execution

### File Structure
```
/home/derek/Desktop/new-analytics/
├── scripts/
│   └── api_integration.py     # Main automation system
├── Season/
│   └── 13/
│       └── October/           # Example archive
│           ├── *.html         # 21+ generated pages
│           ├── charts/        # 28+ PNG charts
│           ├── sc_ladder.json # Softcore data snapshot
│           ├── hc_ladder.json # Hardcore data snapshot
│           └── archive_metadata.json # Quality & performance data
├── logs/
│   └── archive_errors.log     # Error tracking
└── recovery_points/           # Recovery states
```

---

## 🔧 Prerequisites

### System Requirements
- **OS**: Linux (tested on Ubuntu 20.04+)
- **Python**: 3.10+ 
- **Memory**: 8GB+ recommended
- **Disk Space**: 2GB+ free (archives ~120MB each)
- **Network**: Stable internet for PoD API access

### Python Dependencies
```bash
# Required packages (install via pip)
requests>=2.25.0
matplotlib>=3.5.0
pandas>=1.3.0
psutil>=5.8.0
pathlib  # Built-in Python 3.4+
```

### External Dependencies
- **Chrome/Chromium**: For chart generation (automatically handled)
- **PoD API Access**: `https://beta.pathofdiablo.com/api/*`

---

## 🚀 Installation & Setup

### 1. Clone/Download System
```bash
# Navigate to your analytics directory
cd /path/to/your/analytics/folder

# Ensure scripts directory exists
mkdir -p scripts
```

### 2. Install Python Dependencies
```bash
# Install required packages
pip3 install requests matplotlib pandas psutil

# Verify installation
python3 -c "import requests, matplotlib, pandas, psutil; print('✅ All dependencies installed')"
```

### 3. Verify System Requirements
```bash
cd /path/to/your/analytics/folder
python3 -c "
from scripts.api_integration import validate_system_requirements
result = validate_system_requirements('.')
print('✅ System ready' if result['success'] else '⚠️ Issues detected')
"
```

### 4. Test Archive Generation
```bash
# Test with a small archive
python3 -c "
from scripts.api_integration import generate_archive
result = generate_archive(archive_type='test', season_number=13, base_path='.', force=True)
print('✅ SUCCESS' if result['success'] else f'❌ FAILED: {result.get(\"error\", \"Unknown\")}')
"
```

---

## ⚙️ Configuration

### Basic Configuration
The system is designed to work out-of-the-box with minimal configuration. Key parameters:

```python
# Default settings (modify in api_integration.py if needed)
TARGET_DAY = 28              # Day of month to run
MAX_RETRIES = 3              # Network retry attempts
RETRY_DELAY = 2.0            # Seconds between retries
BACKUP_DELAY = 5.0           # Exponential backoff multiplier
```

### Advanced Configuration

#### Custom Archive Types
```python
# Monthly archives (default)
generate_archive(archive_type="monthly", season_number=13)

# Final season archives
generate_archive(archive_type="final", season_number=13)

# Test archives (for development)
generate_archive(archive_type="test", season_number=13, force=True)
```

#### Path Configuration
```python
# Custom base path
generate_archive(base_path="/custom/path/to/analytics")

# The system will create:
# /custom/path/to/analytics/Season/X/Month/
```

---

## 🎮 Usage

### Manual Archive Generation

#### Create Monthly Archive
```bash
cd /path/to/your/analytics/folder
python3 -c "
from scripts.api_integration import generate_archive
result = generate_archive(archive_type='monthly')
print(f'Archive created: {result[\"archive_path\"]}' if result['success'] else f'Error: {result[\"error\"]}')
"
```

#### Force Archive Creation
```bash
# Override safety checks (use with caution)
python3 -c "
from scripts.api_integration import generate_archive
result = generate_archive(archive_type='monthly', force=True)
"
```

#### Generate for Specific Season
```bash
python3 -c "
from scripts.api_integration import generate_archive
result = generate_archive(archive_type='monthly', season_number=12)
"
```

### Automated Monthly Execution

#### Setup Cron Job
```bash
# Generate cron job configuration
python3 -c "
from scripts.api_integration import setup_monthly_cron
result = setup_monthly_cron(
    target_day=28,
    base_path='/path/to/your/analytics/folder'
)
print(result['cron_command'])
"

# Add to crontab (example output):
# 0 2 28 * * cd /path/to/analytics && python3 -c "from scripts.api_integration import auto_monthly_archive; auto_monthly_archive()"
```

#### Manual Cron Setup
```bash
# Edit crontab
crontab -e

# Add line (runs at 2 AM on 28th of each month):
0 2 28 * * cd /home/derek/Desktop/new-analytics && /usr/bin/python3 -c "from scripts.api_integration import auto_monthly_archive; auto_monthly_archive(target_day=28, base_path='/home/derek/Desktop/new-analytics')"
```

### Testing Automation
```bash
# Test monthly automation (dry run)
python3 -c "
from scripts.api_integration import auto_monthly_archive
result = auto_monthly_archive(target_day=1, dry_run=True)  # Use day=1 to trigger test
print(result['message'])
"
```

---

## 📁 Archive Structure

### Generated Archive Layout
```
Season/13/October/
├── index.html                 # Archive index page
├── sc_ladder.json            # Softcore ladder snapshot
├── hc_ladder.json            # Hardcore ladder snapshot
├── archive_metadata.json     # Quality & performance metrics
├── home.html                 # Character statistics
├── funfacts.html             # Statistical insights
├── items.html                # Item distribution
├── mercenary.html            # Mercenary analysis
├── Barbarian.html            # Class-specific pages (7 total)
├── Druid.html
├── Amazon.html
├── Assassin.html
├── Necromancer.html
├── Paladin.html
├── Sorceress.html
├── hcBarbarian.html          # Hardcore class pages (7 total)
├── hcDruid.html
├── hcAmazon.html
├── hcAssassin.html
├── hcNecromancer.html
├── hcPaladin.html
├── hcSorceress.html
└── charts/                   # 28+ generated charts
    ├── Softcore_Barbarian_Build_Distribution.png
    ├── Softcore_Barbarian_Skill_Clusters.png
    └── ... (26+ more charts)
```

### Archive Types
- **Monthly Archives**: Created on 28th of each month
- **Final Archives**: Created at season end
- **Test Archives**: For development and validation

---

## 📊 Monitoring & Metadata

### Archive Metadata
Each archive includes comprehensive metadata in `archive_metadata.json`:

```json
{
  "archive_info": {
    "season_number": 13,
    "archive_type": "monthly",
    "created_date": "2025-11-01T07:48:31.511522",
    "processing_time_seconds": 143.05,
    "metadata_version": "2.0"
  },
  "data_quality": {
    "quality_score": 88.89,
    "balance_ratio": 0.722,
    "completeness": 1.0,
    "sc_percentage": 58.1,
    "hc_percentage": 41.9
  },
  "performance_metrics": {
    "entries_per_second": 17.5,
    "efficiency_score": 85.05,
    "processing_speed": "fast"
  },
  "system_info": {
    "platform": "Linux-5.15.0-160-generic",
    "python_version": "3.10.12",
    "cpu_count": 4,
    "memory_gb": 7.52
  },
  "content_analysis": {
    "total_files": 392,
    "html_files": 23,
    "chart_files": 349,
    "archive_size_mb": 119.42
  }
}
```

### Viewing Metadata
```bash
# View archive metadata with formatting
python3 -c "
from scripts.api_integration import view_archive_metadata
view_archive_metadata('/path/to/Season/13/October', detailed=True)
"
```

### Quality Scoring
- **Quality Score (0-100)**: Data balance and completeness
- **Efficiency Score (0-100)**: Processing performance
- **Success Rate (0-100%)**: Pipeline completion rate

---

## 🔧 Troubleshooting

### Common Issues

#### 1. Network Connectivity
```bash
# Test API connectivity
python3 -c "
import requests
try:
    response = requests.get('https://beta.pathofdiablo.com/api/stats', timeout=10)
    print(f'✅ API accessible: {response.status_code}')
except Exception as e:
    print(f'❌ API error: {e}')
"
```

#### 2. Permission Errors
```bash
# Check directory permissions
ls -la /path/to/analytics/folder

# Fix permissions if needed
chmod 755 /path/to/analytics/folder
chmod +x scripts/api_integration.py
```

#### 3. Disk Space
```bash
# Check available space
df -h /path/to/analytics/folder

# Clean old archives if needed (keep recent ones)
# Each archive is ~120MB
```

#### 4. Memory Issues
```bash
# Check memory usage during generation
python3 -c "
import psutil
memory = psutil.virtual_memory()
print(f'Memory: {memory.percent:.1f}% used, {memory.available / (1024**3):.1f}GB available')
"
```

### Error Logs
```bash
# View error logs
tail -n 50 logs/archive_errors.log

# Monitor real-time
tail -f logs/archive_errors.log
```

### Recovery Points
```bash
# View recovery points
ls -la recovery_points/

# Recovery points are created at each pipeline stage
# Format: {stage}_{timestamp}.json
```

### Test Error Handling
```bash
# Test the error handling system
python3 -c "
from scripts.api_integration import test_error_handling_system
result = test_error_handling_system('/path/to/analytics')
print(f'Error handling: {result[\"success_rate\"]:.1f}% success rate')
"
```

---

## 🔄 Maintenance

### Regular Maintenance Tasks

#### 1. Monitor Disk Usage
```bash
# Check archive sizes
du -sh Season/*/
# Typical size: ~120MB per archive
```

#### 2. Clean Old Logs
```bash
# Rotate error logs (keep last 1000 lines)
tail -n 1000 logs/archive_errors.log > logs/archive_errors.log.tmp
mv logs/archive_errors.log.tmp logs/archive_errors.log
```

#### 3. Verify Cron Jobs
```bash
# List active cron jobs
crontab -l

# Test cron job manually
python3 -c "
from scripts.api_integration import auto_monthly_archive
result = auto_monthly_archive(target_day=1, dry_run=True)
print(result['message'])
"
```

#### 4. Update Dependencies
```bash
# Update Python packages
pip3 install --upgrade requests matplotlib pandas psutil

# Verify updates
python3 -c "
from scripts.api_integration import validate_system_requirements
result = validate_system_requirements('.')
print('✅ System updated' if result['success'] else '⚠️ Issues detected')
"
```

### Archive Cleanup
```bash
# Example: Keep only last 6 months of archives
# (Manual cleanup - adjust paths as needed)
find Season/ -name "*" -type d -mtime +180 -exec rm -rf {} \;
```

---

## 🚀 Advanced Features

### Custom Archive Generation
```python
# Generate archive with custom parameters
from scripts.api_integration import generate_archive

result = generate_archive(
    archive_type="monthly",     # monthly, final, test
    season_number=13,           # Specific season
    base_path="/custom/path",   # Custom location
    force=True                  # Override safety checks
)
```

### Error Handling Testing
```python
# Test comprehensive error handling
from scripts.api_integration import test_error_handling_system

result = test_error_handling_system("/path/to/analytics")
print(f"Error handling success rate: {result['success_rate']:.1f}%")
```

### Metadata Analysis
```python
# View detailed archive metadata
from scripts.api_integration import view_archive_metadata

view_archive_metadata("/path/to/Season/13/October", detailed=True)
```

### Recovery Operations
```python
# Create manual recovery point
from scripts.api_integration import create_recovery_point

result = create_recovery_point("/path/to/archive", "manual_checkpoint")
```

### Network Function Enhancement
```python
# Enhanced API calls with retry logic
from scripts.api_integration import fetch_server_stats

stats = fetch_server_stats()  # Automatic 3x retry with backoff
```

---

## 📞 Support & Resources

### System Information
- **Version**: 2.0 (Enhanced with comprehensive error handling)
- **Compatibility**: Python 3.10+, Linux
- **Dependencies**: requests, matplotlib, pandas, psutil
- **API Endpoint**: `https://beta.pathofdiablo.com/api/`

### Performance Benchmarks
- **Processing Speed**: 15-20 characters/second
- **Archive Size**: ~120MB (392 files)
- **Generation Time**: 140-150 seconds
- **Quality Score**: 85-90/100 typical
- **Success Rate**: 100% with error handling

### Quick Reference Commands
```bash
# Generate test archive
python3 -c "from scripts.api_integration import generate_archive; generate_archive(archive_type='test', force=True)"

# View last archive metadata
python3 -c "from scripts.api_integration import view_archive_metadata; view_archive_metadata('Season/13/November')"

# Test system requirements
python3 -c "from scripts.api_integration import validate_system_requirements; validate_system_requirements('.')"

# Test error handling
python3 -c "from scripts.api_integration import test_error_handling_system; test_error_handling_system('.')"
```

---

## 🎉 Conclusion

The Archive Automation System provides a comprehensive, reliable solution for preserving Path of Diablo ladder history. With its robust error handling, detailed metadata tracking, and automated monthly execution, it ensures consistent, high-quality archives with minimal manual intervention.

**Key Benefits:**
- ✅ **Automated**: Runs monthly without intervention
- ✅ **Reliable**: 100% error handling test success rate
- ✅ **Comprehensive**: 21+ pages, 28+ charts, full metadata
- ✅ **Quality**: Built-in scoring and performance metrics
- ✅ **Maintainable**: Detailed logging and recovery capabilities

For questions or issues, refer to the troubleshooting section or examine the detailed error logs in `logs/archive_errors.log`.

**System Status: Production Ready** 🚀