# GitHub Actions Workflows for Archive Automation

This directory contains automated workflows for managing the Path of Diablo analytics system.

## Workflow Files

### 📅 `monthly-archive.yml` - Automated Monthly Archives
**Schedule**: 28th of every month at 2:00 AM UTC  
**Purpose**: Creates monthly archives automatically at the end of each month

**Features**:
- Runs automatically on the 28th of each month
- Creates archive in `Season/{current}/November/` (or appropriate month)
- Generates complete archive with all charts and pages
- Can be triggered manually if needed
- Commits and pushes results automatically

**Usage**: Fully automated, no manual intervention required

---

### 🔧 `manual-archive.yml` - Manual Archive Creation
**Trigger**: Manual workflow dispatch only  
**Purpose**: Create archives on-demand with full control

**Features**:
- Choose archive type: `monthly` or `final`
- Option to force creation (ignore season freeze)
- Manual trigger with parameters
- Detailed logging and verification
- Safe failure handling

**Usage**: 
1. Go to Actions tab in GitHub
2. Select "Manual Archive Creation"
3. Choose archive type and force option
4. Run workflow

---

### 🛡️ `daily-update-protected.yml` - Smart Daily Updates  
**Schedule**: Every day at 8:00 AM UTC  
**Purpose**: Daily page updates with season freeze protection

**Features**:
- Checks season status before running
- Automatically skips when season is frozen (expected behavior)
- Updates both SC and HC pages when season is active
- Graceful failure when ladder is frozen
- Detailed status reporting

**Usage**: Fully automated, will fail gracefully during season transitions

---

### ⚡ `force-update.yml` - Emergency Force Updates
**Trigger**: Manual workflow dispatch only  
**Purpose**: Force page updates even when season is frozen

**Features**:
- Bypasses all season freeze protection
- Choose update mode: `both`, `softcore`, or `hardcore`
- Choose page type: `all`, `home`, `funfacts`, `items`, `mercenaries`, or `class`
- Reason field for logging why force update was needed
- Should be used sparingly

**Usage**:
1. Go to Actions tab in GitHub  
2. Select "Force Page Update"
3. Choose mode, page type, and provide reason
4. Run workflow (use only when necessary)

---

### 📊 `daily-ladder-fetch.yml` - Daily Data Collection
**Schedule**: Every day at 6:00 AM UTC  
**Purpose**: Fetch fresh ladder data from Path of Diablo API

**Features**:
- Downloads latest SC and HC ladder data
- Runs before other daily processes
- Updates JSON files in repository
- Existing workflow (unchanged)

---

### 🚀 `update-and-deploy.yml` & `static.yml` - Deployment
**Purpose**: Deploy pages to GitHub Pages

**Features**:
- Builds and deploys website
- Handles static asset deployment
- Existing workflows (unchanged)

---

## Workflow Dependencies

```
daily-ladder-fetch.yml (6:00 AM)
        ↓
daily-update-protected.yml (8:00 AM)
        ↓
[Page updates or graceful skip]

monthly-archive.yml (28th of month, 2:00 AM)
        ↓
[Creates monthly archive]

manual-archive.yml (manual only)
        ↓
[On-demand archive creation]

force-update.yml (emergency manual only)
        ↓
[Force updates bypassing protections]
```

## Expected Behavior During Season Transitions

1. **Normal Season Operation**:
   - `daily-ladder-fetch.yml`: ✅ Fetches new data daily
   - `daily-update-protected.yml`: ✅ Updates pages daily
   - `monthly-archive.yml`: ✅ Creates archives monthly

2. **Season Freeze Period**:
   - `daily-ladder-fetch.yml`: ✅ Still fetches (may get unchanged data)
   - `daily-update-protected.yml`: ⏭️ Skips gracefully (logs reason)
   - `monthly-archive.yml`: ⏭️ May skip or fail (expected)
   - `manual-archive.yml`: ✅ Can force with `--force` flag
   - `force-update.yml`: ✅ Always works (emergency use)

## Manual Intervention Required

- **When archives fail**: Use `manual-archive.yml` with force option
- **When pages need immediate update during freeze**: Use `force-update.yml`
- **For testing**: All workflows can be triggered manually

## Security Notes

All workflows use `GITHUB_TOKEN` for authentication and have `contents: write` permissions to commit generated files back to the repository.