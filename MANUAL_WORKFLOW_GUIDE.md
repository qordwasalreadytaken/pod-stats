# 🚀 How to Run Manual GitHub Actions Workflows

## 🔧 **Manual Workflow Access Issue - FIXED!**

GitHub Actions requires workflows to be "discovered" before showing manual trigger buttons. I've added dummy triggers to make them discoverable.

## 📍 **How to Access Manual Workflows**

### **Step 1: Go to GitHub Actions Tab**
1. Visit your repository: `https://github.com/qordwasalreadytaken/pod-stats`
2. Click the **"Actions"** tab at the top
3. Wait a few minutes for GitHub to process the latest commit

### **Step 2: Look for Manual Workflows**
You should see these workflows in the left sidebar:

- **"Force Page Update"** - For emergency page updates
- **"Manual Archive Creation"** - For on-demand archives

### **Step 3: Run a Manual Workflow**
1. Click on the workflow name (e.g., "Force Page Update")
2. Look for a **"Run workflow"** button (usually blue button)
3. Click **"Run workflow"**
4. Fill in the parameters:

#### **Force Page Update Parameters:**
- **Update mode**: `both` (or `softcore`/`hardcore`)
- **Page type**: `all` (or specific page type)
- **Reason**: "Testing manual workflow" (or your reason)

#### **Manual Archive Creation Parameters:**
- **Archive type**: `monthly` (or `final`)
- **Force creation**: `true` (to bypass season freeze)

5. Click **"Run workflow"** to start

## ⏰ **If "Run workflow" Button Doesn't Appear**

### **Wait and Refresh**
- GitHub can take 5-10 minutes to process new workflows
- Refresh the Actions page
- Try a hard refresh (Ctrl+F5 or Cmd+Shift+R)

### **Alternative: Let Automatic Workflows Run First**
The manual workflows will become discoverable after any automatic workflow runs:
- **Daily Ladder Fetch** runs at 6:00 AM UTC
- **Daily Update Protected** runs at 8:00 AM UTC
- **Monthly Archive** runs on the 28th at 2:00 AM UTC

### **Fallback: Command Line**
If GitHub interface still doesn't show the button, you can run commands directly:

```bash
# Test the CLI locally (from your local pod-stats directory)
cd /path/to/pod-stats/scripts
python3 api_integration.py help
python3 api_integration.py test
python3 api_integration.py archive monthly --force
```

## 📋 **Expected Workflow Behavior**

### **Force Page Update**
- ✅ Bypasses season freeze protection
- ✅ Updates specific pages or all pages
- ✅ Works for SC, HC, or both modes
- ⏱️ Takes ~5-15 minutes depending on scope

### **Manual Archive Creation**
- ✅ Creates monthly or final archives
- ✅ Can force creation during season freeze
- ✅ Generates complete archive with charts and pages
- ⏱️ Takes ~15-30 minutes for full archive

## 🔍 **Troubleshooting**

### **If Workflow Fails**
1. Check the **logs** in the Actions tab
2. Look for import errors or missing dependencies
3. Try the **force update** workflow first (simpler)

### **If Import Errors Occur**
- These should be fixed now, but if they happen:
- Check that `psutil` is in requirements.txt
- Verify all functions exist in `api_integration.py`

### **If Season Freeze Issues**
- Use **force creation** option = `true`
- This bypasses all season freeze protection

## 🎯 **Quick Test Recommendation**

1. Try **"Force Page Update"** first:
   - Update mode: `both`
   - Page type: `funfacts`
   - Reason: "Testing manual workflow"

2. If that works, try **"Manual Archive Creation"**:
   - Archive type: `monthly`
   - Force creation: `true`

This will verify the entire system is working correctly! 🚀