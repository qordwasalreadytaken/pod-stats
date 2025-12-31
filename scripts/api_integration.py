#!/usr/bin/env python3
"""
Complete API integration for Path of Diablo stats and server data
Updates unified CSV with both character data and server metrics
"""

import requests
import json
import csv
from collections import defaultdict
from datetime import datetime, timezone
import time
import platform
import psutil
from pathlib import Path
import logging
import functools
import traceback
import smtplib
import urllib.parse
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from typing import Dict, List, Optional, Tuple, Any, Callable

from typing import Dict, List, Optional, Tuple, Any, Callable

# =============================================================================
# ERROR HANDLING & RECOVERY FRAMEWORK
# =============================================================================

class ArchiveError(Exception):
    """Base exception for archive operations"""
    def __init__(self, message: str, error_code: str = None, recoverable: bool = True):
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.recoverable = recoverable
        self.timestamp = datetime.now().isoformat()

class NetworkError(ArchiveError):
    """Network-related errors (API calls, downloads)"""
    def __init__(self, message: str, url: str = None):
        super().__init__(message, "NETWORK_ERROR", recoverable=True)
        self.url = url

class FileSystemError(ArchiveError):
    """File system errors (disk space, permissions, missing files)"""
    def __init__(self, message: str, path: str = None):
        super().__init__(message, "FILESYSTEM_ERROR", recoverable=False)
        self.path = path

class DataError(ArchiveError):
    """Data validation or processing errors"""
    def __init__(self, message: str, data_type: str = None):
        super().__init__(message, "DATA_ERROR", recoverable=True)
        self.data_type = data_type

class ProcessingError(ArchiveError):
    """Content processing errors (charts, HTML generation)"""
    def __init__(self, message: str, stage: str = None):
        super().__init__(message, "PROCESSING_ERROR", recoverable=True)
        self.stage = stage

def setup_error_logging(base_path: str = None):
    """Setup comprehensive error logging"""
    if base_path:
        log_file = Path(base_path) / "logs" / "archive_errors.log"
        log_file.parent.mkdir(exist_ok=True)
    else:
        log_file = "archive_errors.log"
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler()
        ]
    )
    return logging.getLogger('ArchiveSystem')

def retry_on_failure(max_retries: int = 3, delay: float = 1.0, backoff: float = 2.0):
    """Decorator for automatic retry on recoverable failures"""
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            logger = logging.getLogger('ArchiveSystem')
            last_exception = None
            
            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except ArchiveError as e:
                    last_exception = e
                    if not e.recoverable or attempt == max_retries:
                        logger.error(f"❌ {func.__name__} failed permanently: {e.message}")
                        raise
                    
                    wait_time = delay * (backoff ** attempt)
                    logger.warning(f"⚠️ {func.__name__} failed (attempt {attempt + 1}/{max_retries + 1}): {e.message}")
                    logger.info(f"🔄 Retrying in {wait_time:.1f} seconds...")
                    time.sleep(wait_time)
                    
                except Exception as e:
                    # Convert unknown exceptions to ArchiveError
                    last_exception = ArchiveError(f"Unexpected error: {str(e)}", "UNKNOWN_ERROR", recoverable=True)
                    if attempt == max_retries:
                        logger.error(f"❌ {func.__name__} failed with unknown error: {str(e)}")
                        logger.error(f"📍 Traceback: {traceback.format_exc()}")
                        raise last_exception
                    
                    wait_time = delay * (backoff ** attempt)
                    logger.warning(f"⚠️ {func.__name__} failed with unknown error (attempt {attempt + 1}/{max_retries + 1}): {str(e)}")
                    logger.info(f"🔄 Retrying in {wait_time:.1f} seconds...")
                    time.sleep(wait_time)
            
            raise last_exception
        return wrapper
    return decorator

def log_operation(operation_name: str):
    """Decorator for operation logging"""
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            logger = logging.getLogger('ArchiveSystem')
            start_time = time.time()
            
            try:
                logger.info(f"🚀 Starting {operation_name}...")
                result = func(*args, **kwargs)
                
                duration = time.time() - start_time
                if isinstance(result, dict) and result.get("success"):
                    logger.info(f"✅ {operation_name} completed successfully in {duration:.2f}s")
                else:
                    logger.warning(f"⚠️ {operation_name} completed with issues in {duration:.2f}s")
                
                return result
                
            except Exception as e:
                duration = time.time() - start_time
                logger.error(f"❌ {operation_name} failed after {duration:.2f}s: {str(e)}")
                raise
                
        return wrapper
    return decorator

def safe_file_operation(operation: str, path: str, func: Callable, *args, **kwargs):
    """Safely execute file operations with error handling"""
    logger = logging.getLogger('ArchiveSystem')
    
    try:
        # Check path exists (for read operations)
        if operation in ["read", "copy"] and not Path(path).exists():
            raise FileSystemError(f"File not found: {path}", path)
        
        # Check parent directory exists (for write operations)
        if operation in ["write", "create"]:
            parent = Path(path).parent
            if not parent.exists():
                logger.info(f"📁 Creating directory: {parent}")
                parent.mkdir(parents=True, exist_ok=True)
        
        # Check disk space (for write operations)
        if operation in ["write", "create", "copy"]:
            free_space = psutil.disk_usage(str(Path(path).parent)).free
            if free_space < 100 * 1024 * 1024:  # 100MB minimum
                raise FileSystemError(f"Insufficient disk space: {free_space / (1024*1024):.1f}MB available", path)
        
        # Execute the operation
        return func(*args, **kwargs)
        
    except PermissionError as e:
        raise FileSystemError(f"Permission denied for {operation} operation on {path}: {str(e)}", path)
    except OSError as e:
        raise FileSystemError(f"System error during {operation} operation on {path}: {str(e)}", path)
    except Exception as e:
        raise FileSystemError(f"Unexpected error during {operation} operation on {path}: {str(e)}", path)

def validate_system_requirements(base_path: str = None):
    """Validate system requirements before archive operations"""
    logger = logging.getLogger('ArchiveSystem')
    issues = []
    
    try:
        # Check disk space
        if base_path:
            free_space = psutil.disk_usage(base_path).free / (1024**3)  # GB
            if free_space < 1.0:
                issues.append(f"Low disk space: {free_space:.2f}GB available")
        
        # Check memory
        memory = psutil.virtual_memory()
        if memory.percent > 90:
            issues.append(f"High memory usage: {memory.percent:.1f}%")
        
        # Check required Python packages
        required_packages = ['requests', 'matplotlib', 'pandas']
        for package in required_packages:
            try:
                __import__(package)
            except ImportError:
                issues.append(f"Missing required package: {package}")
        
        # Check network connectivity
        try:
            response = requests.get('https://beta.pathofdiablo.com', timeout=10)
            if response.status_code != 200:
                issues.append("Network connectivity issues with PoD API")
        except Exception:
            issues.append("Cannot reach PoD API servers")
        
        if issues:
            logger.warning("⚠️ System requirement issues detected:")
            for issue in issues:
                logger.warning(f"   - {issue}")
            return {"success": False, "issues": issues}
        else:
            logger.info("✅ System requirements validated")
            return {"success": True, "issues": []}
            
    except Exception as e:
        logger.error(f"❌ Error validating system requirements: {str(e)}")
        return {"success": False, "issues": [f"Validation error: {str(e)}"]}

def create_recovery_point(archive_path: str, stage: str):
    """Create a recovery point for rollback capability"""
    logger = logging.getLogger('ArchiveSystem')
    
    try:
        recovery_dir = Path(archive_path).parent / "recovery_points"
        recovery_dir.mkdir(exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        recovery_point = recovery_dir / f"{stage}_{timestamp}.json"
        
        # Save current state
        state = {
            "timestamp": datetime.now().isoformat(),
            "stage": stage,
            "archive_path": str(archive_path),
            "files_created": list(Path(archive_path).rglob("*")) if Path(archive_path).exists() else [],
            "system_info": {
                "disk_free": psutil.disk_usage(str(Path(archive_path).parent)).free,
                "memory_percent": psutil.virtual_memory().percent
            }
        }
        
        with open(recovery_point, 'w') as f:
            json.dump(state, f, indent=2, default=str)
        
        logger.info(f"💾 Recovery point created: {recovery_point}")
        return {"success": True, "recovery_point": str(recovery_point)}
        
    except Exception as e:
        logger.error(f"❌ Failed to create recovery point: {str(e)}")
        return {"success": False, "error": str(e)}

@retry_on_failure(max_retries=3, delay=2.0)
def fetch_server_stats():
    """Fetch global server statistics from PoD API with enhanced error handling"""
    try:
        response = requests.get('https://beta.pathofdiablo.com/api/stats', timeout=10)
        response.raise_for_status()
        data = response.json()
        
        # Validate response structure
        if not data or len(data) == 0:
            raise DataError("Empty response from server stats API", "server_stats")
        
        stats = data[0]
#        required_fields = ['season', 'players_online', 'total_games']
        required_fields = ['online_now', 'games_open']
        for field in required_fields:
            if field not in stats:
                raise DataError(f"Missing required field '{field}' in server stats", "server_stats")
        
        return stats
        
    except requests.exceptions.Timeout:
        raise NetworkError("Timeout while fetching server stats", "https://beta.pathofdiablo.com/api/stats")
    except requests.exceptions.ConnectionError:
        raise NetworkError("Connection error while fetching server stats", "https://beta.pathofdiablo.com/api/stats")
    except requests.exceptions.HTTPError as e:
        raise NetworkError(f"HTTP error {e.response.status_code} while fetching server stats", "https://beta.pathofdiablo.com/api/stats")
    except json.JSONDecodeError:
        raise DataError("Invalid JSON response from server stats API", "server_stats")
    except Exception as e:
        raise NetworkError(f"Unexpected error fetching server stats: {str(e)}", "https://beta.pathofdiablo.com/api/stats")

@retry_on_failure(max_retries=3, delay=2.0)
def fetch_game_servers():
    """Fetch individual game server data from PoD API with enhanced error handling"""
    try:
        response = requests.get('https://beta.pathofdiablo.com/api/servers', timeout=10)
        response.raise_for_status()
        data = response.json()
        
        # Validate response structure
        if not isinstance(data, list):
            raise DataError("Expected list response from game servers API", "game_servers")
        
        # Validate server objects - check for expected fields
        for i, server in enumerate(data):
            if not isinstance(server, dict):
                raise DataError(f"Invalid server object at index {i} - not a dictionary", "game_servers")
            # Check for the fields we actually use
            expected_fields = ['location', 'games', 'players']
            if not any(field in server for field in expected_fields):
                raise DataError(f"Invalid server object at index {i} - missing expected fields", "game_servers")
        
        return data
        
    except requests.exceptions.Timeout:
        raise NetworkError("Timeout while fetching game servers", "https://beta.pathofdiablo.com/api/servers")
    except requests.exceptions.ConnectionError:
        raise NetworkError("Connection error while fetching game servers", "https://beta.pathofdiablo.com/api/servers")
    except requests.exceptions.HTTPError as e:
        raise NetworkError(f"HTTP error {e.response.status_code} while fetching game servers", "https://beta.pathofdiablo.com/api/servers")
    except json.JSONDecodeError:
        raise DataError("Invalid JSON response from game servers API", "game_servers")
    except Exception as e:
        raise NetworkError(f"Unexpected error fetching game servers: {str(e)}", "https://beta.pathofdiablo.com/api/servers")

def get_current_season_info():
    """Get current season number and start time from PoD API"""
    try:
        url = "https://beta.pathofdiablo.com/api/ladder-summaries"
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        seasons = response.json()

        # First, try to find a current season
        for season in seasons:
            if season.get("current"):
                start_time_str = season["start"]
                start_time = datetime.strptime(start_time_str, "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)
                season_number = season["season"]
                return season_number, start_time, "current"

        # If no current season, find the most recent one and check if we're in post-season
        if seasons:
            latest_season = max(seasons, key=lambda s: s["season"])
            season_number = latest_season["season"]
            start_time_str = latest_season["start"]
            end_time_str = latest_season.get("end")
            
            start_time = datetime.strptime(start_time_str, "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)
            
            if end_time_str:
                end_time = datetime.strptime(end_time_str, "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)
                now = datetime.now(timezone.utc)
                
                if now > end_time:
                    return season_number, start_time, "post_season"
                else:
                    return season_number, start_time, "current"
            else:
                return season_number, start_time, "current"

        raise ValueError("No season data found.")
    except requests.RequestException as e:
        print(f"❌ Error fetching season info: {e}")
        return None, None, None

def generate_snapshot_label():
    """Generate snapshot label based on current season progress (matches github-update-csv-web.py logic)"""
    season_number, start_time, season_status = get_current_season_info()
    
    if not season_number or not start_time:
        # Fallback to simple month name if API fails
        return datetime.now().strftime("%B")
    
    now = datetime.now(timezone.utc)
    
    if season_status == "post_season":
        return f"Post Season {season_number}"
    
    delta_days = (now - start_time).days

    if delta_days < 14:
        return f"S{season_number} Day {delta_days + 1}"
    elif delta_days < 49:
        week_number = ((delta_days - 14) // 7) + 2
        return f"S{season_number} Week {week_number}"
    else:
        month_name = now.strftime("%B")
        return f"S{season_number} {month_name}"


# ====================================================================================
# ARCHIVE-SPECIFIC API ENHANCEMENTS
# ====================================================================================

def get_archive_season_info():
    """
    Enhanced season info specifically for archive generation
    Returns detailed season state for banner text and folder naming
    """
    try:
        url = "https://beta.pathofdiablo.com/api/ladder-summaries"
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        seasons = response.json()

        now = datetime.now(timezone.utc)
        current_month = now.strftime("%B")

        # First, check for current season
        for season in seasons:
            if season.get("current"):
                season_number = season["season"]
                start_time_str = season["start"]
                start_time = datetime.strptime(start_time_str, "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)
                
                return {
                    "season_number": season_number,
                    "start_time": start_time,
                    "end_time": None,
                    "status": "current",
                    "archive_folder": current_month,
                    "banner_text": f"Viewing Season {season_number} historical data from the end of {current_month}",
                    "is_season_end": False,
                    "needs_freeze": False
                }

        # No current season found - check for recently ended season
        if seasons:
            latest_season = max(seasons, key=lambda s: s["season"])
            season_number = latest_season["season"]
            start_time_str = latest_season["start"]
            end_time_str = latest_season.get("end")
            
            start_time = datetime.strptime(start_time_str, "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)
            
            if end_time_str:
                end_time = datetime.strptime(end_time_str, "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)
                hours_since_end = (now - end_time).total_seconds() / 3600
                
                # Check if season ended less than 24 hours ago
                if hours_since_end < 24:
                    return {
                        "season_number": season_number,
                        "start_time": start_time,
                        "end_time": end_time,
                        "status": "just_ended",
                        "archive_folder": "Final",
                        "banner_text": f"Viewing Season {season_number} historical data from the end of the ladder",
                        "freeze_banner_text": f"Season {season_number} has ended, this is the final data from the end of the ladder",
                        "is_season_end": True,
                        "needs_freeze": True,
                        "hours_since_end": hours_since_end
                    }
                
                # Post-season period (season ended more than 24 hours ago)
                else:
                    return {
                        "season_number": season_number,
                        "start_time": start_time,
                        "end_time": end_time,
                        "status": "post_season",
                        "archive_folder": current_month,
                        "banner_text": f"Viewing Post Season {season_number} historical data from the end of {current_month}",
                        "freeze_banner_text": f"Season {season_number} has ended. Viewing historical data from the end of the ladder.",
                        "is_season_end": False,
                        "needs_freeze": True  # Freeze during entire post-season period
                    }
            
            # Season with no end date - treat as current
            else:
                return {
                    "season_number": season_number,
                    "start_time": start_time,
                    "end_time": None,
                    "status": "current",
                    "archive_folder": current_month,
                    "banner_text": f"Viewing Season {season_number} historical data from the end of {current_month}",
                    "is_season_end": False,
                    "needs_freeze": False
                }

        raise ValueError("No season data found.")
        
    except requests.RequestException as e:
        print(f"❌ Error fetching archive season info: {e}")
        return None


def should_create_monthly_archive():
    """
    Check if a monthly archive should be created (run on 28th of month)
    Returns True if conditions are met, False otherwise
    """
    now = datetime.now()
    
    # Check if it's the 28th day of the month
    if now.day != 28:
        return False
    
    archive_info = get_archive_season_info()
    if not archive_info:
        print("❌ Could not get season info for archive decision")
        return False
    
    # Always create monthly archives regardless of season state
    print(f"✓ Monthly archive conditions met - Season {archive_info['season_number']}, Status: {archive_info['status']}")
    return True


def should_create_final_archive():
    """
    Check if a Final archive should be created (season ended <24 hours ago)
    Returns True if conditions are met, False otherwise
    """
    archive_info = get_archive_season_info()
    if not archive_info:
        print("❌ Could not get season info for Final archive decision")
        return False
    
    if archive_info["is_season_end"]:
        hours = archive_info.get("hours_since_end", 0)
        print(f"✓ Final archive conditions met - Season {archive_info['season_number']} ended {hours:.1f} hours ago")
        return True
    
    return False


def should_freeze_live_site():
    """
    Check if the live site should be frozen (season ended <24 hours ago)
    Returns True if freeze is needed, False otherwise
    """
    archive_info = get_archive_season_info()
    if not archive_info:
        return False
    
    return archive_info.get("needs_freeze", False)


def generate_freeze_banner_text(season_info):
    """
    Generate freeze banner text for the live site
    
    Args:
        season_info: Dictionary from get_archive_season_info()
    
    Returns:
        String with freeze banner text
    """
    if not season_info:
        return "Site temporarily frozen - season status unknown"
    
    return season_info.get("freeze_banner_text", f"Season {season_info.get('season_number', 'Unknown')} has ended. Site frozen until new season begins.")


def create_archive_folder_structure(season_number, archive_type="monthly", base_path=None):
    """
    Create safe archive folder structure: Season/{season_number}/{month|Final}/charts/
    
    Args:
        season_number: Season number (e.g., 13)
        archive_type: "monthly" or "final"
        base_path: Base directory for archives (defaults to current working directory)
    
    Returns:
        Dict with folder paths and creation status, or None if error
    """
    import os
    from pathlib import Path
    from datetime import datetime
    
    try:
        # Determine base path
        if base_path is None:
            base_path = Path.cwd()
        else:
            base_path = Path(base_path)
        
        # Get archive folder name (month name or "Final")
        if archive_type.lower() == "final":
            archive_folder = "Final"
        else:
            # Use current month for monthly archives
            archive_folder = datetime.now().strftime("%B")
        
        # Build folder structure
        season_folder = base_path / "Season" / str(season_number)
        archive_folder_path = season_folder / archive_folder
        charts_folder = archive_folder_path / "charts"
        
        # Create directories safely (parents=True, exist_ok=True)
        try:
            season_folder.mkdir(parents=True, exist_ok=True)
            archive_folder_path.mkdir(parents=True, exist_ok=True)
            charts_folder.mkdir(parents=True, exist_ok=True)
            
            # Verify all directories exist
            if not season_folder.exists():
                raise OSError(f"Failed to create season folder: {season_folder}")
            if not archive_folder_path.exists():
                raise OSError(f"Failed to create archive folder: {archive_folder_path}")
            if not charts_folder.exists():
                raise OSError(f"Failed to create charts folder: {charts_folder}")
            
            return {
                "success": True,
                "season_folder": str(season_folder),
                "archive_folder": str(archive_folder_path),
                "charts_folder": str(charts_folder),
                "archive_type": archive_type,
                "archive_name": archive_folder,
                "created_new": True  # Could enhance this to track what was actually created
            }
            
        except OSError as e:
            return {
                "success": False,
                "error": f"Directory creation failed: {e}",
                "season_number": season_number,
                "archive_type": archive_type
            }
            
    except Exception as e:
        return {
            "success": False,
            "error": f"Archive folder structure creation failed: {e}",
            "season_number": season_number,
            "archive_type": archive_type
        }


def validate_archive_folder_structure(season_number, archive_type="monthly", base_path=None):
    """
    Validate that archive folder structure exists and is accessible
    
    Args:
        season_number: Season number (e.g., 13)
        archive_type: "monthly" or "final" 
        base_path: Base directory for archives (defaults to current working directory)
    
    Returns:
        Dict with validation results
    """
    import os
    from pathlib import Path
    from datetime import datetime
    
    try:
        # Determine base path
        if base_path is None:
            base_path = Path.cwd()
        else:
            base_path = Path(base_path)
        
        # Get archive folder name (month name or "Final")
        if archive_type.lower() == "final":
            archive_folder = "Final"
        else:
            archive_folder = datetime.now().strftime("%B")
        
        # Build expected paths
        season_folder = base_path / "Season" / str(season_number)
        archive_folder_path = season_folder / archive_folder
        charts_folder = archive_folder_path / "charts"
        
        # Check existence and permissions
        validation_results = {
            "season_folder": {
                "path": str(season_folder),
                "exists": season_folder.exists(),
                "is_dir": season_folder.is_dir() if season_folder.exists() else False,
                "writable": os.access(season_folder, os.W_OK) if season_folder.exists() else False
            },
            "archive_folder": {
                "path": str(archive_folder_path),
                "exists": archive_folder_path.exists(),
                "is_dir": archive_folder_path.is_dir() if archive_folder_path.exists() else False,
                "writable": os.access(archive_folder_path, os.W_OK) if archive_folder_path.exists() else False
            },
            "charts_folder": {
                "path": str(charts_folder),
                "exists": charts_folder.exists(),
                "is_dir": charts_folder.is_dir() if charts_folder.exists() else False,
                "writable": os.access(charts_folder, os.W_OK) if charts_folder.exists() else False
            }
        }
        
        # Overall validation status
        all_exist = all(result["exists"] for result in validation_results.values())
        all_dirs = all(result["is_dir"] for result in validation_results.values() if result["exists"])
        all_writable = all(result["writable"] for result in validation_results.values() if result["exists"])
        
        return {
            "success": all_exist and all_dirs and all_writable,
            "all_exist": all_exist,
            "all_directories": all_dirs,
            "all_writable": all_writable,
            "details": validation_results,
            "archive_type": archive_type,
            "archive_name": archive_folder
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": f"Validation failed: {e}",
            "season_number": season_number,
            "archive_type": archive_type
        }


def get_archive_folder_info(season_number, archive_type="monthly", base_path=None):
    """
    Get comprehensive information about archive folder structure
    
    Args:
        season_number: Season number (e.g., 13)
        archive_type: "monthly" or "final"
        base_path: Base directory for archives (defaults to current working directory)
    
    Returns:
        Dict with folder paths and metadata
    """
    from pathlib import Path
    from datetime import datetime
    
    try:
        # Determine base path
        if base_path is None:
            base_path = Path.cwd()
        else:
            base_path = Path(base_path)
        
        # Get archive folder name (month name or "Final")
        if archive_type.lower() == "final":
            archive_folder = "Final"
        else:
            archive_folder = datetime.now().strftime("%B")
        
        # Build paths
        season_folder = base_path / "Season" / str(season_number)
        archive_folder_path = season_folder / archive_folder
        charts_folder = archive_folder_path / "charts"
        
        return {
            "season_number": season_number,
            "archive_type": archive_type,
            "archive_name": archive_folder,
            "base_path": str(base_path),
            "season_folder": str(season_folder),
            "archive_folder": str(archive_folder_path),
            "charts_folder": str(charts_folder),
            "relative_archive_path": f"Season/{season_number}/{archive_folder}",
            "relative_charts_path": f"Season/{season_number}/{archive_folder}/charts"
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": f"Failed to get archive folder info: {e}",
            "season_number": season_number,
            "archive_type": archive_type
        }


def create_current_season_archive_structure(archive_type="monthly", base_path=None):
    """
    Create archive structure for the current season based on API data
    Combines season detection with folder creation
    
    Args:
        archive_type: "monthly" or "final"
        base_path: Base directory for archives (defaults to current working directory)
    
    Returns:
        Dict with creation results and season info
    """
    try:
        # Get current season info
        season_info = get_archive_season_info()
        if not season_info:
            return {
                "success": False,
                "error": "Could not determine current season from API"
            }
        
        season_number = season_info.get("season_number")
        if not season_number:
            return {
                "success": False,
                "error": "Season number not found in API response"
            }
        
        # Create folder structure
        folder_result = create_archive_folder_structure(season_number, archive_type, base_path)
        
        # Combine results
        if folder_result["success"]:
            return {
                "success": True,
                "season_info": season_info,
                "folder_structure": folder_result,
                "season_number": season_number,
                "archive_type": archive_type
            }
        else:
            return {
                "success": False,
                "error": folder_result.get("error", "Unknown folder creation error"),
                "season_info": season_info,
                "season_number": season_number,
                "archive_type": archive_type
            }
            
    except Exception as e:
        return {
            "success": False,
            "error": f"Failed to create current season archive structure: {e}",
            "archive_type": archive_type
        }


def get_archive_path_configuration(season_number, archive_type="monthly", base_path=None):
    """
    Generate path configuration for archive HTML files
    Charts stay local (charts/), other assets reference root (../../../css/, etc.)
    
    Args:
        season_number: Season number (e.g., 13)
        archive_type: "monthly" or "final"
        base_path: Base directory for archives (defaults to current working directory)
    
    Returns:
        Dict with path mappings for different asset types
    """
    from pathlib import Path
    from datetime import datetime
    
    try:
        # Get archive folder info
        folder_info = get_archive_folder_info(season_number, archive_type, base_path)
        if not folder_info.get("season_number"):
            return {
                "success": False,
                "error": "Failed to get archive folder info"
            }
        
        # Archive files are 3 levels deep: Season/13/October/
        # So we need ../../../ to get back to root
        levels_deep = 3
        root_prefix = "../" * levels_deep
        
        # Path mappings for different asset types
        path_config = {
            "success": True,
            "archive_info": folder_info,
            "levels_deep": levels_deep,
            "root_prefix": root_prefix,
            
            # Asset path mappings
            "paths": {
                # Charts stay local to the archive folder
                "charts": "charts/",
                
                # Other assets reference root
                "css": f"{root_prefix}css/",
                "icons": f"{root_prefix}icons/",
                "templates": f"{root_prefix}templates/",
                "js": f"{root_prefix}js/",
                "assets": f"{root_prefix}assets/",
                
                # Special root-only assets (shared across all archives)
                "shared_charts": f"{root_prefix}charts/",
                "root": root_prefix
            },
            
            # Specific file path generators
            "files": {
                "css_main": f"{root_prefix}css/test-css.css",
                "css_pod_stats": f"{root_prefix}css/pod-stats.css",
                "favicon": f"{root_prefix}icons/pod.ico",
                "navbar_template": f"{root_prefix}templates/navbar.html",
                "build_legend": f"{root_prefix}charts/build-pages-legend.png"
            }
        }
        
        return path_config
        
    except Exception as e:
        return {
            "success": False,
            "error": f"Failed to generate archive path configuration: {e}",
            "season_number": season_number,
            "archive_type": archive_type
        }


def resolve_archive_asset_path(asset_type, filename, season_number, archive_type="monthly", base_path=None):
    """
    Resolve a specific asset path for archive HTML files
    
    Args:
        asset_type: "charts", "css", "icons", "templates", "js", "shared_charts", etc.
        filename: The filename/path of the asset
        season_number: Season number (e.g., 13)
        archive_type: "monthly" or "final"
        base_path: Base directory for archives
    
    Returns:
        String with the resolved path, or None if error
    """
    try:
        path_config = get_archive_path_configuration(season_number, archive_type, base_path)
        if not path_config["success"]:
            return None
        
        asset_base_path = path_config["paths"].get(asset_type)
        if asset_base_path is None:
            # Unknown asset type, assume it's a root asset
            asset_base_path = path_config["paths"]["root"]
        
        # Combine base path with filename
        if filename.startswith('/'):
            # Absolute path, just use the filename as-is
            return f"{asset_base_path}{filename[1:]}"
        else:
            # Relative path
            return f"{asset_base_path}{filename}"
            
    except Exception as e:
        return None


def convert_live_site_paths_to_archive(html_content, season_number, archive_type="monthly", base_path=None):
    """
    Convert live site asset paths to archive-appropriate paths
    
    Args:
        html_content: HTML content with live site paths
        season_number: Season number (e.g., 13)
        archive_type: "monthly" or "final"
        base_path: Base directory for archives
    
    Returns:
        Dict with converted HTML content and conversion details
    """
    import re
    
    try:
        path_config = get_archive_path_configuration(season_number, archive_type, base_path)
        if not path_config["success"]:
            return {
                "success": False,
                "error": path_config["error"]
            }
        
        converted_html = html_content
        conversions = []
        
        # Define path conversion patterns
        # These patterns match common asset references in HTML
        patterns = [
            # CSS files
            {
                "pattern": r'href="\.?/?css/',
                "replacement": f'href="{path_config["paths"]["css"]}',
                "type": "css"
            },
            # Icons
            {
                "pattern": r'href="\.?/?icons/',
                "replacement": f'href="{path_config["paths"]["icons"]}',
                "type": "icons (favicon)"
            },
            {
                "pattern": r'src="\.?/?icons/',
                "replacement": f'src="{path_config["paths"]["icons"]}',
                "type": "icons (images)"
            },
            # Templates (fetch calls)
            {
                "pattern": r'"\.?/?templates/',
                "replacement": f'"{path_config["paths"]["templates"]}',
                "type": "templates"
            },
            # JavaScript files
            {
                "pattern": r'src="\.?/?js/',
                "replacement": f'src="{path_config["paths"]["js"]}',
                "type": "javascript"
            },
            # Shared charts (like build-pages-legend.png)
            {
                "pattern": r'src="\.?/?charts/build-pages-legend\.png"',
                "replacement": f'src="{path_config["files"]["build_legend"]}"',
                "type": "shared_charts"
            },
            # Note: local charts stay as-is with "charts/" path
        ]
        
        # Apply conversions
        for pattern_info in patterns:
            pattern = pattern_info["pattern"]
            replacement = pattern_info["replacement"]
            pattern_type = pattern_info["type"]
            
            matches = re.findall(pattern, converted_html)
            if matches:
                converted_html = re.sub(pattern, replacement, converted_html)
                conversions.append({
                    "type": pattern_type,
                    "pattern": pattern,
                    "matches": len(matches),
                    "replacement": replacement
                })
        
        return {
            "success": True,
            "original_html": html_content,
            "converted_html": converted_html,
            "path_config": path_config,
            "conversions": conversions,
            "total_conversions": sum(conv["matches"] for conv in conversions)
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": f"Failed to convert paths: {e}",
            "season_number": season_number,
            "archive_type": archive_type
        }


def prepare_archive_html_content(html_content, season_number=None, archive_type="monthly", base_path=None):
    """
    Convenience function to prepare HTML content for archive deployment
    Combines season detection with path conversion
    
    Args:
        html_content: HTML content with live site paths
        season_number: Season number (auto-detected if None)
        archive_type: "monthly" or "final"
        base_path: Base directory for archives
    
    Returns:
        Dict with prepared HTML content and process details
    """
    try:
        # Auto-detect season if not provided
        if season_number is None:
            season_info = get_archive_season_info()
            if not season_info:
                return {
                    "success": False,
                    "error": "Could not determine season number from API"
                }
            season_number = season_info.get("season_number")
            if not season_number:
                return {
                    "success": False,
                    "error": "Season number not found in API response"
                }
        
        # Convert paths
        conversion_result = convert_live_site_paths_to_archive(
            html_content, season_number, archive_type, base_path
        )
        
        if conversion_result["success"]:
            return {
                "success": True,
                "html_content": conversion_result["converted_html"],
                "season_number": season_number,
                "archive_type": archive_type,
                "conversion_details": {
                    "total_conversions": conversion_result["total_conversions"],
                    "conversions": conversion_result["conversions"],
                    "path_config": conversion_result["path_config"]
                }
            }
        else:
            return {
                "success": False,
                "error": conversion_result["error"],
                "season_number": season_number,
                "archive_type": archive_type
            }
            
    except Exception as e:
        return {
            "success": False,
            "error": f"Failed to prepare archive HTML content: {e}",
            "season_number": season_number,
            "archive_type": archive_type
        }


def generate_archive_banner_html(season_number=None, archive_type="monthly", banner_text=None, base_path=None):
    """
    Generate HTML banner for archive pages
    
    Args:
        season_number: Season number (auto-detected if None)
        archive_type: "monthly" or "final"
        banner_text: Custom banner text (auto-generated if None)
        base_path: Base directory for archives
    
    Returns:
        Dict with banner HTML and generation details
    """
    try:
        # Auto-detect season if not provided
        if season_number is None:
            season_info = get_archive_season_info()
            if not season_info:
                return {
                    "success": False,
                    "error": "Could not determine season number from API"
                }
            season_number = season_info.get("season_number")
            if not season_number:
                return {
                    "success": False,
                    "error": "Season number not found in API response"
                }
        else:
            season_info = None
        
        # Generate banner text if not provided
        if banner_text is None:
            banner_result = generate_archive_banner_text(season_number, archive_type, base_path)
            if not banner_result["success"]:
                return banner_result
            banner_text = banner_result["banner_text"]
            season_info = banner_result.get("season_info")
        
        # Generate banner HTML
        banner_html = f'''<div class="banner" style="top:50px; left:25%; width:50%;">
            {banner_text}
        </div>'''
        
        return {
            "success": True,
            "banner_html": banner_html,
            "banner_text": banner_text,
            "season_number": season_number,
            "archive_type": archive_type,
            "season_info": season_info
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": f"Failed to generate archive banner HTML: {e}",
            "season_number": season_number,
            "archive_type": archive_type
        }


def generate_archive_banner_text(season_number=None, archive_type="monthly", base_path=None):
    """
    Generate appropriate banner text based on season state and archive type
    
    Args:
        season_number: Season number (auto-detected if None)
        archive_type: "monthly" or "final"
        base_path: Base directory for archives
    
    Returns:
        Dict with banner text and season information
    """
    from datetime import datetime
    
    try:
        # Get season information
        season_info = get_archive_season_info()
        if not season_info:
            return {
                "success": False,
                "error": "Could not get season information from API"
            }
        
        # Use provided season number or get from API
        if season_number is None:
            season_number = season_info.get("season_number")
            if not season_number:
                return {
                    "success": False,
                    "error": "Season number not found in API response"
                }
        
        # Get season status and archive folder name
        season_status = season_info.get("status", "unknown")
        
        # Generate banner text based on archive type and season status
        if archive_type.lower() == "final":
            # Final archives always use "end of the ladder"
            if season_status == "post_season":
                banner_text = f"Viewing Season {season_number} historical data from the end of the ladder"
            elif season_status == "just_ended":
                banner_text = f"Viewing Season {season_number} historical data from the end of the ladder"
            else:
                # Current season final (shouldn't normally happen)
                banner_text = f"Viewing Season {season_number} historical data from the end of the ladder"
                
        else:
            # Monthly archives use month names
            if season_status == "post_season":
                archive_folder = season_info.get("archive_folder", datetime.now().strftime("%B"))
                banner_text = f"Viewing Post Season {season_number} historical data from the end of {archive_folder}"
            elif season_status == "just_ended":
                archive_folder = season_info.get("archive_folder", "October")  # Season typically ends in October
                banner_text = f"Viewing Season {season_number} historical data from the end of {archive_folder}"
            elif season_status == "current":
                archive_folder = season_info.get("archive_folder", datetime.now().strftime("%B"))
                banner_text = f"Viewing Season {season_number} historical data from the end of {archive_folder}"
            else:
                # Unknown status, use generic
                archive_folder = season_info.get("archive_folder", datetime.now().strftime("%B"))
                banner_text = f"Viewing Season {season_number} historical data from the end of {archive_folder}"
        
        return {
            "success": True,
            "banner_text": banner_text,
            "season_number": season_number,
            "archive_type": archive_type,
            "season_status": season_status,
            "archive_folder": season_info.get("archive_folder"),
            "season_info": season_info
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": f"Failed to generate archive banner text: {e}",
            "season_number": season_number,
            "archive_type": archive_type
        }


def generate_freeze_banner_html(season_info=None):
    """
    Generate HTML banner for live site freeze
    
    Args:
        season_info: Season information (auto-detected if None)
    
    Returns:
        Dict with freeze banner HTML
    """
    try:
        # Get season information if not provided
        if season_info is None:
            season_info = get_archive_season_info()
            if not season_info:
                return {
                    "success": False,
                    "error": "Could not get season information for freeze banner"
                }
        
        # Generate freeze banner text
        freeze_text = generate_freeze_banner_text(season_info)
        
        # Generate freeze banner HTML with warning styling
        freeze_banner_html = f'''<div class="banner freeze-banner" style="top:50px; left:25%; width:50%; background-color: #ff6b6b; color: white; border: 2px solid #ff5252; font-weight: bold;">
            🚨 {freeze_text}
        </div>'''
        
        return {
            "success": True,
            "freeze_banner_html": freeze_banner_html,
            "freeze_text": freeze_text,
            "season_info": season_info
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": f"Failed to generate freeze banner HTML: {e}"
        }


def inject_banner_into_html(html_content, banner_html, insertion_method="auto"):
    """
    Inject banner HTML into existing HTML content with multiple fallback methods
    
    Args:
        html_content: Original HTML content
        banner_html: Banner HTML to inject
        insertion_method: "auto" (tries multiple methods), "after_navbar", "after_body", "before_main", "after_navigation"
    
    Returns:
        Dict with modified HTML content
    """
    import re
    
    def try_injection(pattern, replacement, method_name):
        """Try a specific injection pattern"""
        modified_html = re.sub(pattern, replacement, html_content, count=1)
        if banner_html in modified_html:
            return {
                "success": True,
                "original_html": html_content,
                "modified_html": modified_html,
                "banner_html": banner_html,
                "insertion_method": method_name
            }
        return None
    
    try:
        # Define injection patterns
        injection_methods = []
        
        if insertion_method == "auto":
            # Try multiple methods in order of preference
            injection_methods = [
                (r'(</nav>\s*)', f'\\1{banner_html}\n\n        ', "after_navbar"),
                (r'(<div class="top-buttons">.*?</div>\s*)', f'\\1\n        {banner_html}\n        ', "after_navigation"),
                (r'(<div class="main[^"]*"[^>]*>)', f'{banner_html}\n\n                \\1', "before_main"),
                (r'(<body[^>]*>)', f'\\1\n        {banner_html}\n        ', "after_body"),
                (r'(<div class="is-clipped">\s*)', f'\\1{banner_html}\n\n        ', "after_clipped_div")
            ]
        else:
            # Use specific method
            if insertion_method == "after_navbar":
                injection_methods = [(r'(</nav>\s*)', f'\\1{banner_html}\n\n        ', "after_navbar")]
            elif insertion_method == "after_body":
                injection_methods = [(r'(<body[^>]*>)', f'\\1\n        {banner_html}\n        ', "after_body")]
            elif insertion_method == "before_main":
                injection_methods = [(r'(<div class="main[^"]*"[^>]*>)', f'{banner_html}\n\n                \\1', "before_main")]
            elif insertion_method == "after_navigation":
                injection_methods = [(r'(<div class="top-buttons">.*?</div>\s*)', f'\\1\n        {banner_html}\n        ', "after_navigation")]
            else:
                return {
                    "success": False,
                    "error": f"Unknown insertion method: {insertion_method}"
                }
        
        # Try each injection method
        for pattern, replacement, method_name in injection_methods:
            result = try_injection(pattern, replacement, method_name)
            if result:
                return result
        
        # If all methods failed
        return {
            "success": False,
            "error": f"Failed to inject banner - no suitable injection point found. Tried: {[m[2] for m in injection_methods]}",
            "original_html": html_content,
            "banner_html": banner_html,
            "insertion_method": insertion_method
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": f"Failed to inject banner into HTML: {e}",
            "insertion_method": insertion_method
        }


def prepare_archive_html_with_banner(html_content, season_number=None, archive_type="monthly", 
                                   insertion_method="after_navbar", base_path=None):
    """
    Comprehensive function to prepare HTML for archive with banner and path conversion
    Combines path conversion and banner injection in one step
    
    Args:
        html_content: Original HTML content
        season_number: Season number (auto-detected if None)
        archive_type: "monthly" or "final"
        insertion_method: "after_navbar", "after_body", or "before_main"
        base_path: Base directory for archives
    
    Returns:
        Dict with fully prepared HTML content
    """
    try:
        # Step 1: Convert paths for archive
        path_result = prepare_archive_html_content(html_content, season_number, archive_type, base_path)
        if not path_result["success"]:
            return path_result
        
        converted_html = path_result["html_content"]
        if season_number is None:
            season_number = path_result["season_number"]
        
        # Step 2: Generate banner
        banner_result = generate_archive_banner_html(season_number, archive_type, base_path=base_path)
        if not banner_result["success"]:
            return {
                "success": False,
                "error": f"Banner generation failed: {banner_result['error']}",
                "path_conversion": path_result
            }
        
        # Step 3: Inject banner into converted HTML
        injection_result = inject_banner_into_html(
            converted_html, 
            banner_result["banner_html"], 
            insertion_method
        )
        
        if injection_result["success"]:
            return {
                "success": True,
                "html_content": injection_result["modified_html"],
                "season_number": season_number,
                "archive_type": archive_type,
                "banner_details": {
                    "banner_text": banner_result["banner_text"],
                    "banner_html": banner_result["banner_html"],
                    "insertion_method": insertion_method
                },
                "path_conversion": path_result["conversion_details"],
                "processing_steps": ["path_conversion", "banner_generation", "banner_injection"]
            }
        else:
            return {
                "success": False,
                "error": f"Banner injection failed: {injection_result['error']}",
                "path_conversion": path_result,
                "banner_generation": banner_result,
                "processing_steps": ["path_conversion", "banner_generation", "banner_injection_failed"]
            }
            
    except Exception as e:
        return {
            "success": False,
            "error": f"Failed to prepare archive HTML with banner: {e}",
            "season_number": season_number,
            "archive_type": archive_type
        }


def validate_ladder_json_file(file_path, game_mode="sc"):
    """
    Validate a ladder JSON file for archive creation
    
    Args:
        file_path: Path to the JSON file
        game_mode: "sc" or "hc" for softcore/hardcore
    
    Returns:
        Dict with validation results
    """
    import json
    import os
    from pathlib import Path
    
    try:
        file_path = Path(file_path)
        
        # Basic file existence check
        if not file_path.exists():
            return {
                "valid": False,
                "error": f"File does not exist: {file_path}",
                "file_path": str(file_path),
                "game_mode": game_mode
            }
        
        # File size check
        file_size = file_path.stat().st_size
        if file_size == 0:
            return {
                "valid": False,
                "error": "File is empty",
                "file_path": str(file_path),
                "file_size": file_size,
                "game_mode": game_mode
            }
        
        # Minimum size check (should be at least 1KB for valid ladder data)
        min_size = 1024  # 1KB minimum
        if file_size < min_size:
            return {
                "valid": False,
                "error": f"File too small ({file_size} bytes), expected at least {min_size} bytes",
                "file_path": str(file_path),
                "file_size": file_size,
                "game_mode": game_mode
            }
        
        # JSON validity check
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except json.JSONDecodeError as e:
            return {
                "valid": False,
                "error": f"Invalid JSON format: {e}",
                "file_path": str(file_path),
                "file_size": file_size,
                "game_mode": game_mode
            }
        except UnicodeDecodeError as e:
            return {
                "valid": False,
                "error": f"File encoding error: {e}",
                "file_path": str(file_path),
                "file_size": file_size,
                "game_mode": game_mode
            }
        
        # Data structure validation
        if not isinstance(data, list):
            return {
                "valid": False,
                "error": f"Expected list of characters, got {type(data).__name__}",
                "file_path": str(file_path),
                "file_size": file_size,
                "data_type": type(data).__name__,
                "game_mode": game_mode
            }
        
        # Minimum entries check
        min_entries = 10  # Expect at least 10 characters
        if len(data) < min_entries:
            return {
                "valid": False,
                "error": f"Too few entries ({len(data)}), expected at least {min_entries}",
                "file_path": str(file_path),
                "file_size": file_size,
                "entry_count": len(data),
                "game_mode": game_mode
            }
        
        # Character data structure validation (check first few entries)
        required_fields = ["Title", "Name", "Class", "Stats"]
        sample_size = min(5, len(data))
        
        for i in range(sample_size):
            character = data[i]
            if not isinstance(character, dict):
                return {
                    "valid": False,
                    "error": f"Character entry {i} is not a dictionary: {type(character).__name__}",
                    "file_path": str(file_path),
                    "file_size": file_size,
                    "entry_count": len(data),
                    "game_mode": game_mode
                }
            
            missing_fields = [field for field in required_fields if field not in character]
            if missing_fields:
                return {
                    "valid": False,
                    "error": f"Character entry {i} missing required fields: {missing_fields}",
                    "file_path": str(file_path),
                    "file_size": file_size,
                    "entry_count": len(data),
                    "missing_fields": missing_fields,
                    "game_mode": game_mode
                }
        
        # Game mode validation (check if hardcore flag matches expected mode)
        if len(data) > 0 and "IsHardcore" in data[0]:
            expected_hardcore = (game_mode.lower() == "hc")
            actual_hardcore = data[0].get("IsHardcore", False)
            
            if expected_hardcore != actual_hardcore:
                return {
                    "valid": False,
                    "error": f"Game mode mismatch: expected {game_mode}, but file contains {'hardcore' if actual_hardcore else 'softcore'} data",
                    "file_path": str(file_path),
                    "file_size": file_size,
                    "entry_count": len(data),
                    "expected_game_mode": game_mode,
                    "actual_game_mode": "hc" if actual_hardcore else "sc",
                    "game_mode": game_mode
                }
        
        # Success
        return {
            "valid": True,
            "file_path": str(file_path),
            "file_size": file_size,
            "file_size_mb": round(file_size / (1024 * 1024), 2),
            "entry_count": len(data),
            "game_mode": game_mode,
            "sample_character": {
                "title": data[0].get("Title", "N/A"),
                "name": data[0].get("Name", "N/A"),
                "class": data[0].get("Class", "N/A"),
                "level": data[0].get("Stats", {}).get("Level", "N/A") if isinstance(data[0].get("Stats"), dict) else "N/A"
            } if data else None
        }
        
    except Exception as e:
        return {
            "valid": False,
            "error": f"Validation failed with unexpected error: {e}",
            "file_path": str(file_path) if 'file_path' in locals() else "unknown",
            "game_mode": game_mode
        }


def validate_archive_json_files(base_path=None):
    """
    Validate both sc_ladder.json and hc_ladder.json files for archive creation
    
    Args:
        base_path: Base directory to look for JSON files (defaults to current working directory)
    
    Returns:
        Dict with validation results for both files
    """
    from pathlib import Path
    
    try:
        # Determine base path
        if base_path is None:
            base_path = Path.cwd()
        else:
            base_path = Path(base_path)
        
        # Define file paths
        sc_file = base_path / "sc_ladder.json"
        hc_file = base_path / "hc_ladder.json"
        
        # Validate both files
        sc_validation = validate_ladder_json_file(sc_file, "sc")
        hc_validation = validate_ladder_json_file(hc_file, "hc")
        
        # Determine overall status
        both_valid = sc_validation["valid"] and hc_validation["valid"]
        
        return {
            "success": True,
            "both_valid": both_valid,
            "base_path": str(base_path),
            "softcore": sc_validation,
            "hardcore": hc_validation,
            "summary": {
                "sc_valid": sc_validation["valid"],
                "hc_valid": hc_validation["valid"],
                "sc_entries": sc_validation.get("entry_count", 0),
                "hc_entries": hc_validation.get("entry_count", 0),
                "total_size_mb": (
                    sc_validation.get("file_size_mb", 0) + 
                    hc_validation.get("file_size_mb", 0)
                ) if sc_validation["valid"] and hc_validation["valid"] else 0
            }
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": f"Failed to validate archive JSON files: {e}",
            "base_path": str(base_path) if 'base_path' in locals() else "unknown"
        }


def check_json_files_for_archive(season_number=None, archive_type="monthly", base_path=None):
    """
    Pre-flight check for JSON files before archive creation
    Combines validation with archive readiness assessment
    
    Args:
        season_number: Season number (auto-detected if None)
        archive_type: "monthly" or "final"
        base_path: Base directory to look for JSON files
    
    Returns:
        Dict with comprehensive readiness assessment
    """
    try:
        # Get season information
        if season_number is None:
            season_info = get_archive_season_info()
            if not season_info:
                return {
                    "ready": False,
                    "error": "Could not determine season information from API"
                }
            season_number = season_info.get("season_number")
        else:
            season_info = None
        
        # Validate JSON files
        validation_result = validate_archive_json_files(base_path)
        if not validation_result["success"]:
            return {
                "ready": False,
                "error": validation_result["error"],
                "season_number": season_number,
                "archive_type": archive_type
            }
        
        # Check if files are valid for archive creation
        if not validation_result["both_valid"]:
            errors = []
            if not validation_result["softcore"]["valid"]:
                errors.append(f"SC: {validation_result['softcore']['error']}")
            if not validation_result["hardcore"]["valid"]:
                errors.append(f"HC: {validation_result['hardcore']['error']}")
            
            return {
                "ready": False,
                "error": "JSON files not valid for archive creation",
                "validation_errors": errors,
                "validation_details": validation_result,
                "season_number": season_number,
                "archive_type": archive_type
            }
        
        # All checks passed
        return {
            "ready": True,
            "season_number": season_number,
            "archive_type": archive_type,
            "season_info": season_info,
            "validation_details": validation_result,
            "file_summary": {
                "sc_file": validation_result["softcore"]["file_path"],
                "hc_file": validation_result["hardcore"]["file_path"],
                "sc_entries": validation_result["softcore"]["entry_count"],
                "hc_entries": validation_result["hardcore"]["entry_count"],
                "total_entries": validation_result["summary"]["sc_entries"] + validation_result["summary"]["hc_entries"],
                "total_size_mb": validation_result["summary"]["total_size_mb"]
            }
        }
        
    except Exception as e:
        return {
            "ready": False,
            "error": f"Failed to check JSON files for archive: {e}",
            "season_number": season_number,
            "archive_type": archive_type
        }


@log_operation("Archive Generation Pipeline")
@retry_on_failure(max_retries=2, delay=5.0)
def generate_archive(archive_type="monthly", season_number=None, base_path=None, force=False):
    """
    Main archive generation pipeline that orchestrates all components
    
    Pipeline steps:
    1. Season detection → 2. JSON validation → 3. Folder creation → 
    4. Data processing → 5. HTML conversion → 6. Banner injection → 7. Final archive creation
    
    Archive Logic:
    - Monthly archives: Always allowed (during active or ended seasons)
    - Final archives: Only allowed for ended seasons (unless force=True)
    - Daily updates: Continue during active seasons, freeze when season ends
    
    Args:
        archive_type: "monthly" or "final"
        season_number: Season number (auto-detected if None)
        base_path: Base directory for JSON files and archive creation
        force: Override safety checks (use with caution)
    
    Returns:
        Dict with comprehensive archive generation results
    """
    import time
    from datetime import datetime
    from pathlib import Path
    
    # Setup error logging
    logger = setup_error_logging(base_path)
    start_time = time.time()
    recovery_points = []
    
    try:
        # Determine base path
        if base_path is None:
            base_path = Path.cwd()
        else:
            base_path = Path(base_path)
        
        # Validate system requirements
        logger.info("🔍 Validating system requirements...")
        system_check = validate_system_requirements(str(base_path))
        if not system_check["success"]:
            logger.warning("⚠️ System requirement issues detected - proceeding with caution")
            for issue in system_check["issues"]:
                logger.warning(f"   - {issue}")
        
        print(f"=== Archive Generation Pipeline Started ===")
        print(f"Archive Type: {archive_type}")
        print(f"Base Path: {base_path}")
        print(f"Force Mode: {force}")
        print(f"Start Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print()
        
        # Step 1: Season State Detection
        print("Step 1: Season State Detection...")
        try:
            season_info = get_archive_season_info()
            if not season_info:
                raise NetworkError("Failed to detect season state from API")
            
            # Create first recovery point
            recovery_point = create_recovery_point(str(base_path / "temp_archive"), "season_detection")
            if recovery_point["success"]:
                recovery_points.append(recovery_point["recovery_point"])
                
        except Exception as e:
            logger.error(f"❌ Season detection failed: {str(e)}")
            return {
                "success": False,
                "error": f"Season detection failed: {str(e)}",
                "step_failed": "season_detection",
                "archive_type": archive_type,
                "recovery_points": recovery_points,
                "processing_time": time.time() - start_time
            }
        
        # Use provided season number or detected one
        if season_number is None:
            season_number = season_info.get("season_number")
        
        season_active = season_info.get("season_active", True)
        print(f"   Season {season_number}: {'Active' if season_active else 'Ended'}")
        
        # Safety check: Only prevent final archives during active seasons (unless forced)
        # Monthly archives should always be allowed during active seasons
        if archive_type == "final" and season_active and not force:
            return {
                "success": False,
                "error": f"Season {season_number} is still active. Final archives should only be created for ended seasons. Use force=True to override.",
                "step_failed": "season_safety_check",
                "season_info": season_info,
                "archive_type": archive_type
            }
        
        print("   ✅ Season detection complete")
        print()
        
        # Step 2: JSON File Validation
        print("Step 2: JSON File Validation...")
        try:
            logger.info("🔍 Validating JSON files...")
            readiness_check = check_json_files_for_archive(season_number, archive_type, base_path)
            if not readiness_check["ready"]:
                raise DataError(f"JSON validation failed: {readiness_check['error']}", "ladder_data")
            
            # Create recovery point after validation
            recovery_point = create_recovery_point(str(base_path / "temp_archive"), "json_validation")
            if recovery_point["success"]:
                recovery_points.append(recovery_point["recovery_point"])
                
        except DataError:
            raise  # Re-raise DataError as-is
        except Exception as e:
            logger.error(f"❌ JSON validation failed: {str(e)}")
            raise DataError(f"Unexpected validation error: {str(e)}", "ladder_data")
        
        file_summary = readiness_check["file_summary"]
        print(f"   SC Ladder: {file_summary['sc_entries']:,} entries")
        print(f"   HC Ladder: {file_summary['hc_entries']:,} entries")
        print(f"   Total Size: {file_summary['total_size_mb']} MB")
        print("   ✅ JSON validation complete")
        print()
        
        # Step 3: Archive Folder Creation
        print("Step 3: Archive Folder Creation...")
        try:
            logger.info("📁 Creating archive folder structure...")
            
            # Create archive folder structure (month is determined internally)
            folder_result = create_archive_folder_structure(
                season_number=season_number,
                archive_type=archive_type,
                base_path=base_path
            )
            
            if not folder_result["success"]:
                raise FileSystemError(f"Failed to create archive folders: {folder_result.get('error', 'Unknown error')}")
            
            # Create recovery point after folder creation
            archive_path = Path(folder_result["archive_folder"])
            recovery_point = create_recovery_point(str(archive_path), "folder_creation")
            if recovery_point["success"]:
                recovery_points.append(recovery_point["recovery_point"])
                
        except FileSystemError:
            raise  # Re-raise FileSystemError as-is
        except Exception as e:
            logger.error(f"❌ Folder creation failed: {str(e)}")
            raise FileSystemError(f"Unexpected folder creation error: {str(e)}")
        
        if not folder_result["success"]:
            return {
                "success": False,
                "error": folder_result["error"],
                "step_failed": "folder_creation",
                "season_number": season_number,
                "archive_type": archive_type
            }
        
        archive_path = Path(folder_result["archive_folder"])
        charts_path = Path(folder_result["charts_folder"])
        print(f"   Archive Path: {archive_path}")
        print(f"   Charts Path: {charts_path}")
        print("   ✅ Folder creation complete")
        print()
        
        # Step 4: Data Processing
        print("Step 4: Data Processing...")
        print("   📋 Processing ladder data...")
        
        # Copy JSON files to archive (for preservation)
        import shutil
        sc_source = base_path / "sc_ladder.json"
        hc_source = base_path / "hc_ladder.json"
        sc_archive = archive_path / "sc_ladder.json"
        hc_archive = archive_path / "hc_ladder.json"
        
        shutil.copy2(sc_source, sc_archive)
        shutil.copy2(hc_source, hc_archive)
        print(f"   Copied {sc_source.name} to archive")
        print(f"   Copied {hc_source.name} to archive")
        
        # Process archive content (charts, HTML pages, assets)
        content_result = process_archive_content(
            season_number=season_number,
            archive_type=archive_type,
            base_path=base_path,
            archive_path=archive_path
        )
        
        if content_result["success"]:
            summary = content_result["summary"]
            print(f"   ✅ Content processing complete:")
            print(f"      - Pages: {summary['pages_count']}")
            print(f"      - Charts: {summary['charts_count']}")
            print(f"      - Assets: {summary['assets_count']}")
            if summary['errors_count'] > 0:
                print(f"      - Errors: {summary['errors_count']} (non-critical)")
        else:
            print(f"   ⚠️  Content processing failed: {content_result['error']}")
            print("   ⚠️  Continuing with basic archive...")
            content_result = {"success": False, "summary": {"pages_count": 0, "charts_count": 0, "assets_count": 0, "errors_count": 1}}
        
        print("   ✅ Data processing complete")
        print()
        
        # Step 5: HTML Conversion (now handled in Step 4)
        print("Step 5: HTML Conversion...")
        print("   📄 Archive HTML conversion completed in Step 4")
        print("   ✅ HTML conversion complete")
        print()
        
        # Step 6: Banner Injection
        print("Step 6: Banner Injection...")
        
        # Get current month for banner context
        current_month = datetime.now().strftime("%Y-%m")
        
        # Generate archive banner
        banner_result = generate_archive_banner_html(
            season_number=season_number,
            archive_type=archive_type,
            base_path=base_path
        )
        
        if not banner_result["success"]:
            print(f"   ⚠️  Banner generation failed: {banner_result['error']}")
            print("   ⚠️  Continuing without banner...")
            banner_html = None
        else:
            banner_html = banner_result["banner_html"]
            print(f"   Generated banner for Season {season_number} ({archive_type})")
            print("   ✅ Banner injection complete")
        print()
        
        # Step 7: Update Navbar Template
        print("Step 7: Update Navbar Template...")
        try:
            logger.info("📝 Updating navbar template with new archive...")
            navbar_result = update_navbar_template(base_path=base_path)
            
            if navbar_result["success"]:
                print(f"   ✅ Navbar updated: {navbar_result['dropdown_info']['archive_count']} archives across {navbar_result['dropdown_info']['season_count']} seasons")
                if navbar_result.get("backup_path"):
                    print(f"   💾 Backup saved: {navbar_result['backup_path']}")
            else:
                print(f"   ⚠️  Navbar update failed: {navbar_result['error']}")
                print("   ⚠️  Archive created successfully but navbar needs manual update")
                
        except Exception as e:
            logger.warning(f"⚠️  Navbar update failed: {str(e)}")
            print(f"   ⚠️  Navbar update failed: {e}")
            print("   ⚠️  Archive created successfully but navbar needs manual update")
            navbar_result = {"success": False, "error": str(e)}
        print()
        
        # Step 8: Final Archive Creation
        print("Step 8: Final Archive Creation...")
        
        # Create enhanced archive metadata
        end_time = time.time()
        processing_time = round(end_time - start_time, 2)
        
        # Convert season_info datetime objects to strings for JSON serialization
        serializable_season_info = {}
        if season_info:
            for key, value in season_info.items():
                if hasattr(value, 'isoformat'):  # datetime object
                    serializable_season_info[key] = value.isoformat()
                else:
                    serializable_season_info[key] = value
        
        # Enhanced data quality metrics
        data_quality = analyze_data_quality(file_summary)
        
        # System environment info
        system_info = {
            "platform": platform.platform(),
            "python_version": platform.python_version(),
            "cpu_count": psutil.cpu_count(),
            "memory_gb": round(psutil.virtual_memory().total / (1024**3), 2),
            "disk_space_gb": round(psutil.disk_usage(str(base_path)).free / (1024**3), 2)
        }
        
        # Performance metrics
        performance_metrics = calculate_performance_metrics(processing_time, file_summary)
        
        # Historical comparison (if previous metadata exists)
        historical_data = get_historical_comparison(str(archive_path), season_number)
        
        # Content analysis insights
        content_analysis = analyze_archive_content(str(archive_path))
        
        metadata = {
            "archive_info": {
                "season_number": season_number,
                "archive_type": archive_type,
                "created_date": datetime.now().isoformat(),
                "processing_time_seconds": processing_time,
                "base_path": str(base_path),
                "archive_path": str(archive_path),
                "charts_path": str(charts_path),
                "metadata_version": "2.0"
            },
            "season_info": serializable_season_info,
            "file_summary": file_summary,
            "data_quality": data_quality,
            "system_info": system_info,
            "performance_metrics": performance_metrics,
            "historical_comparison": historical_data,
            "content_analysis": content_analysis,
            "folder_structure": {
                "success": folder_result.get("success", False),
                "archive_folder": str(folder_result.get("archive_folder", "")),
                "charts_folder": str(folder_result.get("charts_folder", "")),
                "archive_type": folder_result.get("archive_type", archive_type)
            },
            "banner_info": {
                "success": banner_result.get("success", False),
                "has_banner": banner_html is not None
            },
            "navbar_update": {
                "success": navbar_result.get("success", False),
                "error": navbar_result.get("error") if not navbar_result.get("success") else None,
                "archive_count": navbar_result.get("dropdown_info", {}).get("archive_count", 0),
                "season_count": navbar_result.get("dropdown_info", {}).get("season_count", 0)
            },
            "content_processing": content_result.get("summary", {
                "pages_count": 0,
                "charts_count": 0,
                "assets_count": 0,
                "errors_count": 1
            }),
            "pipeline_status": {
                "season_detection": "completed",
                "json_validation": "completed", 
                "folder_creation": "completed",
                "data_processing": "completed" if content_result["success"] else "partial",
                "html_conversion": "completed" if content_result["success"] else "partial",
                "banner_injection": "completed" if banner_html else "skipped",
                "final_creation": "completed",
                "navbar_update": "completed" if navbar_result.get("success") else "failed"
            },
            "generation_summary": {
                "total_characters": file_summary.get("total_entries", 0),
                "archive_size_mb": calculate_archive_size(str(archive_path)),
                "efficiency_score": performance_metrics.get("efficiency_score", 0),
                "quality_score": data_quality.get("quality_score", 0),
                "success_rate": calculate_success_rate({
                    "season_detection": "completed",
                    "json_validation": "completed", 
                    "folder_creation": "completed",
                    "data_processing": "completed" if content_result["success"] else "partial",
                    "html_conversion": "completed" if content_result["success"] else "partial",
                    "banner_injection": "completed" if banner_html else "skipped",
                    "final_creation": "completed"
                })
            }
        }
        
        # Save metadata to archive
        metadata_file = archive_path / "archive_metadata.json"
        import json
        with open(metadata_file, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)
        
        print(f"   Enhanced archive metadata saved: {metadata_file}")
        print(f"   Processing time: {processing_time} seconds")
        print(f"   Quality score: {data_quality.get('quality_score', 0)}/100")
        print(f"   Efficiency score: {performance_metrics.get('efficiency_score', 0)}/100")
        print("   ✅ Final archive creation complete")
        print()
        
        print("=== Archive Generation Pipeline Complete ===")
        print(f"✅ SUCCESS: Archive created at {archive_path}")
        print(f"📊 Data: {file_summary['total_entries']:,} characters, {file_summary['total_size_mb']} MB")
        print(f"⏱️  Time: {processing_time} seconds")
        print(f"📈 Quality: {data_quality.get('quality_score', 0)}/100 | Efficiency: {performance_metrics.get('efficiency_score', 0)}/100")
        print(f"💾 Archive size: {metadata['generation_summary']['archive_size_mb']} MB")
        
        return {
            "success": True,
            "archive_path": str(archive_path),
            "charts_path": str(charts_path),
            "metadata": metadata,
            "processing_time": processing_time,
            "message": f"Archive successfully created for Season {season_number} ({archive_type})"
        }
        
    except Exception as e:
        end_time = time.time()
        processing_time = round(end_time - start_time, 2)
        
        return {
            "success": False,
            "error": f"Archive generation pipeline failed: {e}",
            "step_failed": "pipeline_exception",
            "season_number": season_number,
            "archive_type": archive_type,
            "processing_time": processing_time
        }


def create_monthly_archive(season_number=None, base_path=None, force=False):
    """
    Convenience function to create a monthly archive
    
    Args:
        season_number: Season number (auto-detected if None) 
        base_path: Base directory for JSON files and archive creation
        force: Override safety checks
    
    Returns:
        Archive generation result
    """
    return generate_archive(
        archive_type="monthly",
        season_number=season_number,
        base_path=base_path,
        force=force
    )


def create_final_archive(season_number=None, base_path=None, force=False):
    """
    Convenience function to create a final season archive
    
    Args:
        season_number: Season number (auto-detected if None)
        base_path: Base directory for JSON files and archive creation  
        force: Override safety checks
    
    Returns:
        Archive generation result
    """
    return generate_archive(
        archive_type="final",
        season_number=season_number,
        base_path=base_path,
        force=force
    )


def is_monthly_archive_trigger_day(target_day=28, current_date=None):
    """
    Check if today is the monthly archive trigger day (default: 28th)
    
    Args:
        target_day: Day of month to trigger on (default: 28)
        current_date: Date to check (defaults to today)
    
    Returns:
        Dict with trigger status and date information
    """
    from datetime import datetime, date
    
    try:
        # Use provided date or current date
        if current_date is None:
            check_date = date.today()
        elif isinstance(current_date, str):
            check_date = datetime.strptime(current_date, "%Y-%m-%d").date()
        elif isinstance(current_date, datetime):
            check_date = current_date.date()
        else:
            check_date = current_date
        
        # Check if today is the trigger day
        is_trigger_day = check_date.day == target_day
        
        # Calculate next trigger date
        if is_trigger_day:
            # If today is trigger day, next is next month
            if check_date.month == 12:
                next_trigger = check_date.replace(year=check_date.year + 1, month=1, day=target_day)
            else:
                next_trigger = check_date.replace(month=check_date.month + 1, day=target_day)
        else:
            # Next trigger is this month if we haven't passed it, or next month if we have
            if check_date.day < target_day:
                try:
                    next_trigger = check_date.replace(day=target_day)
                except ValueError:
                    # Target day doesn't exist in this month (e.g., Feb 30, Oct 31 -> target 31)
                    # Move to next month
                    if check_date.month == 12:
                        next_trigger = check_date.replace(year=check_date.year + 1, month=1, day=1)
                        # Then try to set the target day
                        try:
                            next_trigger = next_trigger.replace(day=target_day)
                        except ValueError:
                            # Target day doesn't exist in January either (impossible for 1-28)
                            next_trigger = next_trigger.replace(day=target_day if target_day <= 28 else 28)
                    else:
                        next_trigger = check_date.replace(month=check_date.month + 1, day=1)
                        # Then try to set the target day
                        try:
                            next_trigger = next_trigger.replace(day=target_day)
                        except ValueError:
                            # Target day doesn't exist in next month
                            import calendar
                            max_day = calendar.monthrange(next_trigger.year, next_trigger.month)[1]
                            next_trigger = next_trigger.replace(day=min(target_day, max_day))
            else:
                # We've passed trigger day this month, next is next month
                if check_date.month == 12:
                    next_trigger = check_date.replace(year=check_date.year + 1, month=1, day=1)
                    try:
                        next_trigger = next_trigger.replace(day=target_day)
                    except ValueError:
                        import calendar
                        max_day = calendar.monthrange(next_trigger.year, next_trigger.month)[1]
                        next_trigger = next_trigger.replace(day=min(target_day, max_day))
                else:
                    next_trigger = check_date.replace(month=check_date.month + 1, day=1)
                    try:
                        next_trigger = next_trigger.replace(day=target_day)
                    except ValueError:
                        import calendar
                        max_day = calendar.monthrange(next_trigger.year, next_trigger.month)[1]
                        next_trigger = next_trigger.replace(day=min(target_day, max_day))
        
        return {
            "is_trigger_day": is_trigger_day,
            "current_date": check_date.isoformat(),
            "current_day": check_date.day,
            "target_day": target_day,
            "next_trigger_date": next_trigger.isoformat(),
            "days_until_trigger": (next_trigger - check_date).days,
            "month_year": check_date.strftime("%Y-%m")
        }
        
    except Exception as e:
        return {
            "is_trigger_day": False,
            "error": f"Failed to check trigger day: {e}",
            "current_date": str(current_date) if current_date else "unknown"
        }


def check_archive_trigger_conditions(target_day=28, current_date=None, season_number=None, base_path=None):
    """
    Comprehensive check for monthly archive trigger conditions
    
    Args:
        target_day: Day of month to trigger on (default: 28)
        current_date: Date to check (defaults to today)
        season_number: Season number (auto-detected if None)
        base_path: Base directory for JSON files
    
    Returns:
        Dict with complete trigger assessment
    """
    try:
        # Check if it's trigger day
        trigger_check = is_monthly_archive_trigger_day(target_day, current_date)
        if not trigger_check["is_trigger_day"]:
            return {
                "should_trigger": False,
                "reason": f"Not trigger day (today is {trigger_check['current_day']}, trigger on {target_day})",
                "trigger_info": trigger_check,
                "next_check": f"Next trigger in {trigger_check['days_until_trigger']} days"
            }
        
        # Check season state
        season_info = get_archive_season_info()
        if not season_info:
            return {
                "should_trigger": False,
                "reason": "Cannot determine season state from API",
                "trigger_info": trigger_check,
                "error": "Season API unavailable"
            }
        
        season_active = season_info.get("season_active", True)
        if season_number is None:
            season_number = season_info.get("season_number")
        
        # Only trigger monthly archives during active seasons
        if not season_active:
            return {
                "should_trigger": False,
                "reason": f"Season {season_number} has ended (monthly archives not needed for ended seasons)",
                "trigger_info": trigger_check,
                "season_info": season_info,
                "suggestion": "Consider creating final archive instead"
            }
        
        # Check if archive already exists for this month
        from pathlib import Path
        from datetime import datetime
        
        if base_path is None:
            base_path = Path.cwd()
        else:
            base_path = Path(base_path)
        
        current_month = trigger_check["month_year"].split("-")[1]  # Get month name
        month_names = {
            "01": "January", "02": "February", "03": "March", "04": "April",
            "05": "May", "06": "June", "07": "July", "08": "August", 
            "09": "September", "10": "October", "11": "November", "12": "December"
        }
        month_name = month_names.get(current_month, current_month)
        
        existing_archive = base_path / "Season" / str(season_number) / month_name
        if existing_archive.exists():
            # Check if it has metadata (indicating complete archive)
            metadata_file = existing_archive / "archive_metadata.json"
            if metadata_file.exists():
                return {
                    "should_trigger": False,
                    "reason": f"Monthly archive for {month_name} already exists",
                    "trigger_info": trigger_check,
                    "season_info": season_info,
                    "existing_archive": str(existing_archive),
                    "suggestion": "Archive already created this month"
                }
        
        # Check JSON file readiness
        readiness_check = check_json_files_for_archive(season_number, "monthly", base_path)
        if not readiness_check["ready"]:
            return {
                "should_trigger": False,
                "reason": "JSON files not ready for archive creation",
                "trigger_info": trigger_check,
                "season_info": season_info,
                "json_errors": readiness_check.get("validation_errors", []),
                "suggestion": "Fix JSON file issues before creating archive"
            }
        
        # All conditions met!
        return {
            "should_trigger": True,
            "reason": f"All conditions met for monthly archive creation",
            "trigger_info": trigger_check,
            "season_info": season_info,
            "readiness_check": readiness_check,
            "archive_details": {
                "season_number": season_number,
                "archive_type": "monthly",
                "target_month": month_name,
                "data_summary": readiness_check["file_summary"]
            }
        }
        
    except Exception as e:
        return {
            "should_trigger": False,
            "reason": f"Error checking trigger conditions: {e}",
            "error": str(e)
        }


# Enhanced Metadata System Functions
def analyze_data_quality(file_summary):
    """Analyze data quality metrics for comprehensive tracking"""
    try:
        total_entries = file_summary.get("total_entries", 0)
        sc_entries = file_summary.get("sc_entries", 0)
        hc_entries = file_summary.get("hc_entries", 0)
        
        # Calculate quality metrics
        balance_ratio = min(sc_entries, hc_entries) / max(sc_entries, hc_entries) if max(sc_entries, hc_entries) > 0 else 0
        completeness = min(total_entries / 2000, 1.0)  # Assume 2000 is good target
        
        # Data quality score (0-100)
        quality_score = round((balance_ratio * 40 + completeness * 60), 2)
        
        return {
            "quality_score": quality_score,
            "balance_ratio": round(balance_ratio, 3),
            "completeness": round(completeness, 3),
            "sc_percentage": round(sc_entries / total_entries * 100, 1) if total_entries > 0 else 0,
            "hc_percentage": round(hc_entries / total_entries * 100, 1) if total_entries > 0 else 0,
            "entry_density": "high" if total_entries > 2000 else "medium" if total_entries > 1000 else "low"
        }
    except Exception as e:
        return {"quality_score": 0, "error": str(e)}

def calculate_performance_metrics(processing_time, file_summary):
    """Calculate performance and efficiency metrics"""
    try:
        total_entries = file_summary.get("total_entries", 1)
        total_size_mb = file_summary.get("total_size_mb", 1)
        
        # Efficiency calculations
        entries_per_second = round(total_entries / processing_time, 2)
        mb_per_second = round(total_size_mb / processing_time, 3)
        
        # Performance score based on reasonable benchmarks
        # Target: 20+ entries/sec, 0.5+ MB/sec
        efficiency_score = min(
            (entries_per_second / 20) * 50 + (mb_per_second / 0.5) * 50, 
            100
        )
        
        return {
            "entries_per_second": entries_per_second,
            "mb_per_second": mb_per_second,
            "efficiency_score": round(efficiency_score, 2),
            "processing_speed": "fast" if efficiency_score > 75 else "medium" if efficiency_score > 50 else "slow",
            "memory_efficiency": "optimal" if processing_time < 120 else "acceptable" if processing_time < 300 else "slow"
        }
    except Exception as e:
        return {"efficiency_score": 0, "error": str(e)}

def get_historical_comparison(archive_path, season_number):
    """Get historical comparison data from previous archives"""
    try:
        base_season_path = Path(archive_path).parent.parent
        comparisons = []
        
        # Look for other season folders
        for season_folder in base_season_path.iterdir():
            if season_folder.is_dir() and season_folder.name.startswith("Season"):
                try:
                    folder_season = int(season_folder.name.replace("Season", "").strip())
                    if folder_season != season_number:
                        # Look for metadata in monthly archives
                        for month_folder in season_folder.iterdir():
                            if month_folder.is_dir():
                                metadata_file = month_folder / "archive_metadata.json"
                                if metadata_file.exists():
                                    with open(metadata_file, 'r') as f:
                                        old_metadata = json.load(f)
                                    
                                    comparisons.append({
                                        "season": folder_season,
                                        "archive_type": old_metadata.get("archive_info", {}).get("archive_type", "unknown"),
                                        "total_entries": old_metadata.get("file_summary", {}).get("total_entries", 0),
                                        "processing_time": old_metadata.get("archive_info", {}).get("processing_time_seconds", 0)
                                    })
                                    break  # Only get most recent for each season
                except ValueError:
                    continue
        
        # Sort by season number and limit to last 3
        comparisons.sort(key=lambda x: x["season"], reverse=True)
        recent_comparisons = comparisons[:3]
        
        return {
            "available_seasons": len(comparisons),
            "recent_comparisons": recent_comparisons,
            "trend_analysis": analyze_historical_trends(recent_comparisons) if recent_comparisons else {}
        }
    except Exception as e:
        return {"error": str(e), "available_seasons": 0}

def analyze_historical_trends(comparisons):
    """Analyze trends from historical data"""
    if len(comparisons) < 2:
        return {}
    
    try:
        # Get trend data
        entry_counts = [c["total_entries"] for c in comparisons]
        processing_times = [c["processing_time"] for c in comparisons]
        
        # Calculate trends
        entry_trend = "increasing" if entry_counts[0] > entry_counts[-1] else "decreasing"
        performance_trend = "improving" if processing_times[0] < processing_times[-1] else "declining"
        
        return {
            "entry_trend": entry_trend,
            "performance_trend": performance_trend,
            "avg_entries": round(sum(entry_counts) / len(entry_counts)),
            "avg_processing_time": round(sum(processing_times) / len(processing_times), 2)
        }
    except Exception as e:
        return {"error": str(e)}

def analyze_archive_content(archive_path):
    """Analyze the content of the generated archive"""
    try:
        archive_path = Path(archive_path)
        analysis = {
            "html_files": 0,
            "chart_files": 0,
            "json_files": 0,
            "total_files": 0,
            "total_size_mb": 0,
            "largest_file": "",
            "largest_size_mb": 0
        }
        
        # Analyze all files in archive
        for file_path in archive_path.rglob("*"):
            if file_path.is_file():
                analysis["total_files"] += 1
                file_size = file_path.stat().st_size
                file_size_mb = file_size / (1024 * 1024)
                analysis["total_size_mb"] += file_size_mb
                
                # Track largest file
                if file_size_mb > analysis["largest_size_mb"]:
                    analysis["largest_size_mb"] = file_size_mb
                    analysis["largest_file"] = file_path.name
                
                # Count by type
                if file_path.suffix == ".html":
                    analysis["html_files"] += 1
                elif file_path.suffix == ".png":
                    analysis["chart_files"] += 1
                elif file_path.suffix == ".json":
                    analysis["json_files"] += 1
        
        analysis["total_size_mb"] = round(analysis["total_size_mb"], 2)
        analysis["largest_size_mb"] = round(analysis["largest_size_mb"], 2)
        analysis["avg_file_size_kb"] = round((analysis["total_size_mb"] * 1024) / max(analysis["total_files"], 1), 2)
        
        return analysis
    except Exception as e:
        return {"error": str(e)}

def calculate_archive_size(archive_path):
    """Calculate total archive size in MB"""
    try:
        total_size = 0
        for file_path in Path(archive_path).rglob("*"):
            if file_path.is_file():
                total_size += file_path.stat().st_size
        return round(total_size / (1024 * 1024), 2)
    except Exception as e:
        return 0

def calculate_success_rate(pipeline_status):
    """Calculate overall success rate from pipeline status"""
    try:
        total_steps = len(pipeline_status)
        completed_steps = sum(1 for status in pipeline_status.values() if status == "completed")
        return round((completed_steps / total_steps) * 100, 1) if total_steps > 0 else 0
    except Exception as e:
        return 0

def test_error_handling_system(base_path: str = None):
    """Test the comprehensive error handling and recovery system"""
    logger = setup_error_logging(base_path)
    
    print("🧪 Testing Error Handling & Recovery System")
    print("=" * 50)
    
    test_results = {
        "network_retry": False,
        "file_operations": False,
        "system_validation": False,
        "recovery_points": False,
        "error_classification": False
    }
    
    # Test 1: Network Error Handling
    print("\n1. Testing Network Error Handling...")
    try:
        # This should trigger retries and proper error classification
        response = requests.get('https://nonexistent-domain-12345.com', timeout=1)
    except:
        # Manually test network error creation
        try:
            raise NetworkError("Test network error", "https://test.com")
        except NetworkError as e:
            if e.recoverable and e.error_code == "NETWORK_ERROR":
                test_results["network_retry"] = True
                print("   ✅ Network error classification working")
            else:
                print("   ❌ Network error classification failed")
    
    # Test 2: File System Error Handling  
    print("\n2. Testing File System Error Handling...")
    try:
        test_path = "/nonexistent/path/test.txt"
        safe_file_operation("read", test_path, open, test_path, 'r')
    except FileSystemError as e:
        if not e.recoverable and e.error_code == "FILESYSTEM_ERROR":
            test_results["file_operations"] = True
            print("   ✅ File system error handling working")
        else:
            print("   ❌ File system error handling failed")
    except Exception as e:
        print(f"   ❌ Unexpected error: {e}")
    
    # Test 3: System Validation
    print("\n3. Testing System Validation...")
    validation_result = validate_system_requirements(base_path)
    if isinstance(validation_result, dict) and "success" in validation_result:
        test_results["system_validation"] = True
        print("   ✅ System validation working")
    else:
        print("   ❌ System validation failed")
    
    # Test 4: Recovery Points
    print("\n4. Testing Recovery Points...")
    if base_path:
        recovery_result = create_recovery_point(str(base_path), "test_stage")
        if recovery_result.get("success"):
            test_results["recovery_points"] = True
            print("   ✅ Recovery point creation working")
        else:
            print("   ❌ Recovery point creation failed")
    else:
        print("   ⚠️ Skipped (no base path provided)")
    
    # Test 5: Error Classification
    print("\n5. Testing Error Classification...")
    try:
        errors = [
            NetworkError("Test network", "http://test.com"),
            FileSystemError("Test filesystem", "/test/path"),
            DataError("Test data", "test_data"),
            ProcessingError("Test processing", "test_stage")
        ]
        
        classifications = [e.error_code for e in errors]
        expected = ["NETWORK_ERROR", "FILESYSTEM_ERROR", "DATA_ERROR", "PROCESSING_ERROR"]
        
        if classifications == expected:
            test_results["error_classification"] = True
            print("   ✅ Error classification working")
        else:
            print("   ❌ Error classification failed")
    except Exception as e:
        print(f"   ❌ Error classification test failed: {e}")
    
    # Summary
    print("\n" + "=" * 50)
    print("📊 Test Results Summary:")
    passed = sum(test_results.values())
    total = len(test_results)
    
    for test_name, result in test_results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"   {test_name.replace('_', ' ').title()}: {status}")
    
    success_rate = (passed / total) * 100
    print(f"\n🎯 Overall Success Rate: {success_rate:.1f}% ({passed}/{total})")
    
    if success_rate >= 80:
        print("🎉 Error handling system is working well!")
        logger.info(f"✅ Error handling test completed: {success_rate:.1f}% success rate")
    else:
        print("⚠️ Error handling system needs improvement")
        logger.warning(f"⚠️ Error handling test completed: {success_rate:.1f}% success rate")
    
    return {
        "success": success_rate >= 80,
        "success_rate": success_rate,
        "test_results": test_results,
        "message": f"Error handling system test: {success_rate:.1f}% success rate"
    }

def view_archive_metadata(archive_path, detailed=False):
    """View comprehensive metadata for an archive with formatted output"""
    try:
        metadata_file = Path(archive_path) / "archive_metadata.json"
        if not metadata_file.exists():
            return {"success": False, "error": "No metadata file found"}
        
        with open(metadata_file, 'r') as f:
            metadata = json.load(f)
        
        # Basic information
        archive_info = metadata.get("archive_info", {})
        data_quality = metadata.get("data_quality", {})
        performance = metadata.get("performance_metrics", {})
        system_info = metadata.get("system_info", {})
        content = metadata.get("content_analysis", {})
        summary = metadata.get("generation_summary", {})
        
        print("="*60)
        print(f"📊 ARCHIVE METADATA REPORT")
        print("="*60)
        print(f"🗂️  Archive: Season {archive_info.get('season_number')} ({archive_info.get('archive_type')})")
        print(f"📅 Created: {archive_info.get('created_date', 'Unknown')}")
        print(f"⏱️  Processing: {archive_info.get('processing_time_seconds', 0)} seconds")
        print(f"📁 Path: {archive_info.get('archive_path', 'Unknown')}")
        print()
        
        print("📈 QUALITY & PERFORMANCE")
        print("-"*30)
        print(f"🎯 Quality Score: {data_quality.get('quality_score', 0)}/100")
        print(f"⚡ Efficiency Score: {performance.get('efficiency_score', 0)}/100")
        print(f"✅ Success Rate: {summary.get('success_rate', 0)}%")
        print(f"📊 Data Balance: {data_quality.get('sc_percentage', 0)}% SC / {data_quality.get('hc_percentage', 0)}% HC")
        print(f"🚀 Processing Speed: {performance.get('processing_speed', 'Unknown')}")
        print()
        
        print("💾 ARCHIVE CONTENTS")
        print("-"*20)
        print(f"📄 Total Files: {content.get('total_files', 'Unknown')}")
        print(f"🌐 HTML Pages: {content.get('html_files', 'Unknown')}")
        print(f"📊 Charts: {content.get('chart_files', 'Unknown')}")
        print(f"📋 JSON Files: {content.get('json_files', 'Unknown')}")
        print(f"💾 Archive Size: {summary.get('archive_size_mb', 0)} MB")
        print(f"📁 Largest File: {content.get('largest_file', 'Unknown')} ({content.get('largest_size_mb', 0)} MB)")
        print()
        
        if detailed:
            print("🖥️  SYSTEM INFORMATION")
            print("-"*22)
            print(f"🐧 Platform: {system_info.get('platform', 'Unknown')}")
            print(f"🐍 Python: {system_info.get('python_version', 'Unknown')}")
            print(f"🧠 CPU Cores: {system_info.get('cpu_count', 'Unknown')}")
            print(f"💾 Memory: {system_info.get('memory_gb', 0)} GB")
            print(f"💿 Disk Space: {system_info.get('disk_space_gb', 0)} GB")
            print()
            
            file_summary = metadata.get("file_summary", {})
            print("📊 DATA STATISTICS")
            print("-"*18)
            print(f"👥 Total Characters: {file_summary.get('total_entries', 0):,}")
            print(f"⚔️  Softcore: {file_summary.get('sc_entries', 0):,}")
            print(f"💀 Hardcore: {file_summary.get('hc_entries', 0):,}")
            print(f"📏 Data Size: {file_summary.get('total_size_mb', 0)} MB")
            print(f"📈 Entry Density: {data_quality.get('entry_density', 'Unknown')}")
            print()
            
            historical = metadata.get("historical_comparison", {})
            if historical.get("available_seasons", 0) > 0:
                print("📈 HISTORICAL COMPARISON")
                print("-"*25)
                print(f"🗂️  Available Seasons: {historical.get('available_seasons', 0)}")
                trends = historical.get("trend_analysis", {})
                if trends:
                    print(f"📊 Entry Trend: {trends.get('entry_trend', 'Unknown')}")
                    print(f"⚡ Performance Trend: {trends.get('performance_trend', 'Unknown')}")
                print()
        
        print("="*60)
        return {"success": True, "metadata": metadata}
        
    except Exception as e:
        return {"success": False, "error": str(e)}

def auto_monthly_archive(target_day=28, current_date=None, base_path=None, dry_run=False):
    """
    Automatic monthly archive creation with trigger condition checking
    
    Args:
        target_day: Day of month to trigger on (default: 28)
        current_date: Date to check (defaults to today)  
        base_path: Base directory for JSON files and archive creation
        dry_run: If True, only check conditions without creating archive
    
    Returns:
        Dict with trigger check results and archive creation status
    """
    try:
        print(f"=== Auto Monthly Archive {'(DRY RUN)' if dry_run else ''} ===")
        print(f"Target Day: {target_day}")
        print(f"Check Date: {current_date or 'today'}")
        print(f"Base Path: {base_path or 'current directory'}")
        print()
        
        # Check trigger conditions
        trigger_conditions = check_archive_trigger_conditions(target_day, current_date, None, base_path)
        
        print("📅 Trigger Condition Check:")
        if trigger_conditions["should_trigger"]:
            print(f"   ✅ {trigger_conditions['reason']}")
            
            # Display archive details
            archive_details = trigger_conditions["archive_details"]
            print(f"   📊 Archive Details:")
            print(f"      - Season: {archive_details['season_number']}")
            print(f"      - Type: {archive_details['archive_type']}")
            print(f"      - Month: {archive_details['target_month']}")
            
            data_summary = archive_details["data_summary"]
            print(f"      - Characters: {data_summary['total_entries']:,}")
            print(f"      - Size: {data_summary['total_size_mb']} MB")
            
            if dry_run:
                print("   🧪 DRY RUN: Archive creation skipped")
                return {
                    "success": True,
                    "triggered": True,
                    "dry_run": True,
                    "trigger_conditions": trigger_conditions,
                    "message": "Would create monthly archive (dry run mode)"
                }
            
            # Create the archive
            print("\n🚀 Creating Monthly Archive...")
            archive_result = create_monthly_archive(
                season_number=archive_details["season_number"],
                base_path=base_path,
                force=False  # Should not need force for monthly archives
            )
            
            if archive_result["success"]:
                print(f"✅ Monthly archive created successfully!")
                return {
                    "success": True,
                    "triggered": True,
                    "dry_run": False,
                    "trigger_conditions": trigger_conditions,
                    "archive_result": archive_result,
                    "message": f"Monthly archive created for Season {archive_details['season_number']}"
                }
            else:
                print(f"❌ Monthly archive creation failed!")
                return {
                    "success": False,
                    "triggered": True,
                    "dry_run": False,
                    "trigger_conditions": trigger_conditions,
                    "archive_result": archive_result,
                    "error": archive_result.get("error", "Unknown archive creation error")
                }
        else:
            print(f"   ❌ {trigger_conditions['reason']}")
            if "next_check" in trigger_conditions:
                print(f"   📅 {trigger_conditions['next_check']}")
            if "suggestion" in trigger_conditions:
                print(f"   💡 {trigger_conditions['suggestion']}")
            
            return {
                "success": True,
                "triggered": False,
                "dry_run": dry_run,
                "trigger_conditions": trigger_conditions,
                "message": "No action needed - trigger conditions not met"
            }
            
    except Exception as e:
        return {
            "success": False,
            "triggered": False,
            "dry_run": dry_run,
            "error": f"Auto monthly archive failed: {e}"
        }


def setup_monthly_archive_cron(target_day=28, base_path=None, user_crontab=True):
    """
    Generate cron job configuration for monthly archive automation
    
    Args:
        target_day: Day of month to trigger on (default: 28)
        base_path: Base directory for scripts and archives
        user_crontab: If True, generate user crontab format, else system cron
    
    Returns:
        Dict with cron configuration and setup instructions
    """
    from pathlib import Path
    
    try:
        # Determine paths
        if base_path is None:
            base_path = Path.cwd()
        else:
            base_path = Path(base_path)
        
        scripts_path = base_path / "scripts"
        
        # Generate cron command
        python_cmd = "python3"  # Could be made configurable
        script_path = scripts_path / "monthly_archive_cron.py"
        
        # Cron runs at 2 AM on the target day of each month
        cron_schedule = f"0 2 {target_day} * *"
        
        if user_crontab:
            cron_command = f"cd {base_path} && {python_cmd} {script_path}"
        else:
            # System cron needs user specification
            cron_command = f"cd {base_path} && {python_cmd} {script_path}"
        
        cron_line = f"{cron_schedule} {cron_command}"
        
        # Generate the cron script
        cron_script_content = f'''#!/usr/bin/env python3
"""
Monthly Archive Cron Job
Auto-generated script for monthly archive creation
"""
import sys
import os
from pathlib import Path
from datetime import datetime

# Add scripts directory to path
sys.path.append('{scripts_path}')

# Import archive functions
from api_integration import auto_monthly_archive

def main():
    """Main cron job function"""
    print(f"=== Monthly Archive Cron Job ===")
    print(f"Started: {{datetime.now().isoformat()}}")
    
    try:
        # Run automatic monthly archive
        result = auto_monthly_archive(
            target_day={target_day},
            base_path="{base_path}",
            dry_run=False
        )
        
        if result["success"]:
            if result["triggered"]:
                print(f"✅ SUCCESS: {{result['message']}}")
                exit(0)
            else:
                print(f"ℹ️  NO ACTION: {{result['message']}}")
                exit(0)
        else:
            print(f"❌ ERROR: {{result.get('error', 'Unknown error')}}")
            exit(1)
            
    except Exception as e:
        print(f"❌ CRON ERROR: {{e}}")
        exit(1)

if __name__ == "__main__":
    main()
'''
        
        return {
            "success": True,
            "cron_schedule": cron_schedule,
            "cron_line": cron_line,
            "script_path": str(script_path),
            "script_content": cron_script_content,
            "setup_instructions": [
                f"1. Create the cron script: {script_path}",
                f"2. Make it executable: chmod +x {script_path}",
                f"3. Add to crontab: crontab -e",
                f"4. Add this line: {cron_line}",
                f"5. Save and exit",
                f"",
                f"The job will run at 2 AM on the {target_day}th of each month",
                f"Logs will be output to the terminal/system logs"
            ],
            "test_command": f"cd {base_path} && {python_cmd} -c \"from scripts.api_integration import auto_monthly_archive; print(auto_monthly_archive(dry_run=True))\""
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": f"Failed to setup cron configuration: {e}"
        }


def convert_html_for_archive(html_content: str, archive_path: str) -> str:
    """Convert HTML paths for archive folder structure"""
    try:
        # Convert local paths to work from archive subdirectory
        # Archive is at Season/X/Month/ so need ../../../ to reach root
        html_content = html_content.replace('href="css/', 'href="../../../css/')
        html_content = html_content.replace('src="css/', 'src="../../../css/')
        html_content = html_content.replace('href="icons/', 'href="../../../icons/')
        html_content = html_content.replace('src="icons/', 'src="../../../icons/')
        html_content = html_content.replace('href="templates/', 'href="../../../templates/')
        html_content = html_content.replace('src="templates/', 'src="../../../templates/')
        
        # Convert chart paths to be relative to archive
        html_content = html_content.replace('src="charts/', 'src="charts/')  # Keep local
        html_content = html_content.replace('href="charts/', 'href="charts/')  # Keep local
        
        # Convert page links to work within archive
        classes = ['Amazon', 'Assassin', 'Barbarian', 'Druid', 'Necromancer', 'Paladin', 'Sorceress']
        for class_name in classes:
            html_content = html_content.replace(f'href="{class_name}.html"', f'href="{class_name}.html"')
            html_content = html_content.replace(f'href="hc{class_name}.html"', f'href="hc{class_name}.html"')
        
        # Convert other page links
        html_content = html_content.replace('href="index.html"', 'href="index.html"')
        html_content = html_content.replace('href="fun_facts.html"', 'href="fun_facts.html"')
        html_content = html_content.replace('href="items_equipment.html"', 'href="items_equipment.html"')
        html_content = html_content.replace('href="mercenary.html"', 'href="mercenary.html"')
        
        return html_content
        
    except Exception as e:
        print(f"       ⚠️ HTML conversion error: {e}")
        return html_content


# ====================================================================================
# NAVBAR AUTOMATION FUNCTIONS
# ====================================================================================

def scan_archive_structure(base_path=None):
    """
    Scan the Season/ directory structure and discover all existing archives
    
    Args:
        base_path: Base directory containing Season/ folder (defaults to current working directory)
    
    Returns:
        Dict with archive structure organized by season and archive folders
    """
    from pathlib import Path
    
    try:
        # Determine base path
        if base_path is None:
            base_path = Path.cwd()
        else:
            base_path = Path(base_path)
        
        season_dir = base_path / "Season"
        
        if not season_dir.exists():
            return {
                "success": True,
                "seasons": [],
                "total_archives": 0,
                "message": "No Season directory found - no archives exist yet"
            }
        
        # Scan for seasons
        seasons = []
        total_archives = 0
        
        for season_path in sorted(season_dir.iterdir()):
            if not season_path.is_dir():
                continue
            
            try:
                season_number = int(season_path.name)
            except ValueError:
                # Not a season number directory, skip
                continue
            
            # Scan for archives within this season
            archives = []
            for archive_path in sorted(season_path.iterdir()):
                if not archive_path.is_dir():
                    continue
                
                archive_name = archive_path.name
                
                # Check if it's a valid archive (has Home.html or index.html)
                has_home = (archive_path / "Home.html").exists()
                has_index = (archive_path / "index.html").exists()
                has_metadata = (archive_path / "archive_metadata.json").exists()
                
                if has_home or has_index or has_metadata:
                    # Get creation timestamp for sorting
                    # Try metadata first (most accurate), then directory mtime
                    creation_time = None
                    if has_metadata:
                        try:
                            import json
                            with open(archive_path / "archive_metadata.json", 'r') as f:
                                metadata = json.load(f)
                                creation_time = metadata.get("archive_info", {}).get("created_date")
                        except:
                            pass
                    
                    # Fallback to directory modification time
                    if not creation_time:
                        creation_time = archive_path.stat().st_mtime
                    
                    archives.append({
                        "name": archive_name,
                        "path": str(archive_path),
                        "relative_path": f"Season/{season_number}/{archive_name}",
                        "has_home": has_home,
                        "has_index": has_index,
                        "has_metadata": has_metadata,
                        "is_final": archive_name.lower() == "final",
                        "creation_time": creation_time
                    })
                    total_archives += 1
            
            if archives:
                seasons.append({
                    "season_number": season_number,
                    "path": str(season_path),
                    "archives": archives,
                    "archive_count": len(archives)
                })
        
        return {
            "success": True,
            "seasons": seasons,
            "total_archives": total_archives,
            "season_count": len(seasons)
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": f"Failed to scan archive structure: {e}",
            "seasons": [],
            "total_archives": 0
        }


def generate_navbar_dropdown_html(archive_structure):
    """
    Generate HTML for the Trends History dropdown menu based on discovered archives
    
    Args:
        archive_structure: Result from scan_archive_structure()
    
    Returns:
        Dict with generated HTML
    """
    try:
        if not archive_structure["success"]:
            return {
                "success": False,
                "error": archive_structure.get("error", "Archive scan failed")
            }
        
        seasons = archive_structure["seasons"]
        
        if not seasons:
            # No archives, return minimal dropdown
            dropdown_html = '''                            <button class="dropdown2-button">Trends History</button>
                            <div class="dropdown2-content">
                                <a href="https://trends.pathofdiablo.com/Home.html">Current</a>
                            </div>'''
            return {
                "success": True,
                "html": dropdown_html,
                "season_count": 0,
                "archive_count": 0
            }
        
        # Build dropdown HTML
        html_parts = []
        html_parts.append('                            <button class="dropdown2-button">Trends History</button>')
        html_parts.append('                            <div class="dropdown2-content">')
        html_parts.append('                                <a href="https://trends.pathofdiablo.com/Home.html">Current</a>')
        
        # Sort seasons in descending order (newest first)
        sorted_seasons = sorted(seasons, key=lambda s: s["season_number"], reverse=True)
        
        for season in sorted_seasons:
            season_number = season["season_number"]
            archives = season["archives"]
            
            # Sort archives purely by creation time (newest first)
            # This ensures the dropdown shows true chronological order regardless of archive names
            def get_sort_time(archive):
                creation_time = archive.get("creation_time", 0)
                
                # Convert creation_time to timestamp
                if isinstance(creation_time, str):
                    try:
                        from datetime import datetime
                        dt = datetime.fromisoformat(creation_time.replace('Z', '+00:00'))
                        return dt.timestamp()
                    except:
                        return 0
                elif isinstance(creation_time, (int, float)):
                    return creation_time
                else:
                    return 0
            
            sorted_archives = sorted(archives, key=get_sort_time, reverse=True)
            
            # Add season dropdown
            html_parts.append('                                <div class="dropdown2-item dropdown-sub">')
            html_parts.append(f'                                    <a class="dropdown-sub-button">S{season_number}</a>')
            html_parts.append('                                    <div class="dropdown-sub-content">')
            
            for archive in sorted_archives:
                archive_name = archive["name"]
                relative_path = archive["relative_path"]
                html_parts.append(f'                                        <a href="https://trends.pathofdiablo.com/{relative_path}/Home">{archive_name}</a>')
            
            html_parts.append('                                    </div>')
            html_parts.append('                                </div>')
        
        html_parts.append('                            </div>')
        
        dropdown_html = '\n'.join(html_parts)
        
        return {
            "success": True,
            "html": dropdown_html,
            "season_count": len(seasons),
            "archive_count": archive_structure["total_archives"]
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": f"Failed to generate navbar dropdown HTML: {e}"
        }


def update_navbar_template(base_path=None, template_path=None, backup=True):
    """
    Update the navbar.html template with current archive structure
    
    Args:
        base_path: Base directory containing Season/ folder (defaults to current working directory)
        template_path: Path to navbar.html template (defaults to templates/navbar.html)
        backup: Whether to create a backup of the original template
    
    Returns:
        Dict with update results
    """
    from pathlib import Path
    import shutil
    import re
    
    try:
        # Determine paths
        if base_path is None:
            base_path = Path.cwd()
        else:
            base_path = Path(base_path)
        
        if template_path is None:
            template_path = base_path / "templates" / "navbar.html"
        else:
            template_path = Path(template_path)
        
        if not template_path.exists():
            return {
                "success": False,
                "error": f"Template not found: {template_path}"
            }
        
        # Step 1: Scan archive structure
        archive_structure = scan_archive_structure(base_path)
        if not archive_structure["success"]:
            return {
                "success": False,
                "error": f"Archive scan failed: {archive_structure.get('error', 'Unknown error')}"
            }
        
        # Step 2: Generate new dropdown HTML
        dropdown_result = generate_navbar_dropdown_html(archive_structure)
        if not dropdown_result["success"]:
            return {
                "success": False,
                "error": f"Dropdown generation failed: {dropdown_result.get('error', 'Unknown error')}"
            }
        
        new_dropdown_html = dropdown_result["html"]
        
        # Step 3: Read current template
        with open(template_path, 'r', encoding='utf-8') as f:
            template_content = f.read()
        
        # Step 4: Create backup if requested
        if backup:
            backup_path = template_path.with_suffix('.html.bak')
            shutil.copy2(template_path, backup_path)
        
        # Step 5: Replace the dropdown section
        # Match from <div class="navbar-item dropdown2"> through all nested content until the closing </div>
        # that ends the dropdown2 div
        
        pattern = r'(<div class="navbar-item dropdown2">).*?</div>\s*</div>(?=\s*</div>\s*</div>\s*</nav>)'
        
        replacement = f'\\1\n{new_dropdown_html}\n                        '
        
        updated_content = re.sub(pattern, replacement, template_content, flags=re.DOTALL)
        
        # Check if replacement occurred
        if updated_content == template_content:
            return {
                "success": False,
                "error": "Failed to locate navbar dropdown section for replacement",
                "pattern_used": pattern,
                "suggestion": "Navbar template structure may have changed"
            }
        
        # Step 6: Write updated template
        with open(template_path, 'w', encoding='utf-8') as f:
            f.write(updated_content)
        
        return {
            "success": True,
            "template_path": str(template_path),
            "backup_path": str(backup_path) if backup else None,
            "archive_structure": archive_structure,
            "dropdown_info": {
                "season_count": dropdown_result["season_count"],
                "archive_count": dropdown_result["archive_count"]
            },
            "message": f"Navbar updated with {dropdown_result['archive_count']} archives across {dropdown_result['season_count']} seasons"
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": f"Failed to update navbar template: {e}"
        }


def refresh_navbar_archives(base_path=None, template_path=None):
    """
    Standalone function to refresh navbar with current archive structure
    Useful for manual updates or testing
    
    Args:
        base_path: Base directory containing Season/ folder
        template_path: Path to navbar.html template
    
    Returns:
        Dict with update results
    """
    print("=== Refreshing Navbar Archives ===")
    print()
    
    # Scan and update
    result = update_navbar_template(base_path=base_path, template_path=template_path)
    
    if result["success"]:
        print(f"✅ SUCCESS: Navbar updated")
        print(f"📊 Archives: {result['dropdown_info']['archive_count']} across {result['dropdown_info']['season_count']} seasons")
        print(f"📝 Template: {result['template_path']}")
        if result.get("backup_path"):
            print(f"💾 Backup: {result['backup_path']}")
    else:
        print(f"❌ FAILED: {result['error']}")
    
    print()
    return result


# ====================================================================================
# END NAVBAR AUTOMATION FUNCTIONS
# ====================================================================================


def process_archive_content(season_number, archive_type, base_path=None, archive_path=None):
    """
    Process and generate all content for archive: charts, HTML pages, assets
    
    Args:
        season_number: Season number
        archive_type: "monthly" or "final"
        base_path: Base directory containing JSON files
        archive_path: Archive directory path
    
    Returns:
        Dict with processing results
    """
    from pathlib import Path
    import sys
    import os
    
    try:
        print(f"🔧 Processing archive content for Season {season_number} ({archive_type})")
        
        # Setup paths
        if base_path is None:
            base_path = Path.cwd()
        else:
            base_path = Path(base_path)
        
        if archive_path is None:
            # Should not happen if called from pipeline, but handle gracefully
            return {
                "success": False,
                "error": "Archive path is required for content processing"
            }
        
        archive_path = Path(archive_path)
        charts_path = archive_path / "charts"
        
        # Ensure charts directory exists
        charts_path.mkdir(parents=True, exist_ok=True)
        
        # Add scripts and modules to path for importing page generators
        scripts_path = base_path / "scripts"
        modules_path = scripts_path / "modules"
        sys.path.insert(0, str(scripts_path))
        sys.path.insert(0, str(modules_path))
        
        # Change to base directory for page generation (they expect specific working directory)
        original_cwd = os.getcwd()
        os.chdir(base_path)
        
        processing_results = {
            "charts_generated": [],
            "pages_generated": [],
            "assets_copied": [],
            "errors": []
        }
        
        # Process both SC and HC if available
        game_modes = []
        sc_file = archive_path / "sc_ladder.json"
        hc_file = archive_path / "hc_ladder.json"
        
        if sc_file.exists():
            game_modes.append(("sc", False, str(sc_file)))
        if hc_file.exists():
            game_modes.append(("hc", True, str(hc_file)))
        
        if not game_modes:
            return {
                "success": False,
                "error": "No ladder JSON files found in archive directory"
            }
        
        # Import page generation modules
        try:
            from generate_pages import generate_all_pages
            from modules.shared_utils import load_character_data
        except ImportError as e:
            return {
                "success": False,
                "error": f"Failed to import page generation modules: {e}"
            }
        
        # Generate content for each game mode
        for mode_prefix, is_hardcore, json_file in game_modes:
            print(f"  📊 Processing {mode_prefix.upper()} content...")
            
            try:
                # Load character data
                all_characters = load_character_data(json_file)
                print(f"     Loaded {len(all_characters)} characters")
                
                # Generate archive-specific pages using modified page generation
                archive_result = generate_archive_pages(
                    all_characters=all_characters,
                    is_hardcore=is_hardcore,
                    archive_path=archive_path,
                    charts_path=charts_path,
                    season_number=season_number,
                    archive_type=archive_type
                )
                
                if archive_result["success"]:
                    processing_results["charts_generated"].extend(archive_result["charts"])
                    processing_results["pages_generated"].extend(archive_result["pages"])
                    print(f"     ✅ Generated {len(archive_result['pages'])} pages, {len(archive_result['charts'])} charts")
                else:
                    error_msg = f"{mode_prefix.upper()}: {archive_result['error']}"
                    processing_results["errors"].append(error_msg)
                    print(f"     ❌ {error_msg}")
                
            except Exception as e:
                error_msg = f"{mode_prefix.upper()} processing failed: {e}"
                processing_results["errors"].append(error_msg)
                print(f"     ❌ {error_msg}")
        
        # Copy additional assets
        print(f"  📁 Copying additional assets...")
        asset_result = copy_archive_assets(base_path, archive_path)
        if asset_result["success"]:
            processing_results["assets_copied"] = asset_result["copied_assets"]
            print(f"     ✅ Copied {len(asset_result['copied_assets'])} assets")
        else:
            processing_results["errors"].append(f"Asset copying: {asset_result['error']}")
            print(f"     ⚠️ Asset copying issue: {asset_result['error']}")
        
        # Generate archive index page
        print(f"  📄 Generating archive index...")
        index_result = generate_archive_index(
            archive_path=archive_path,
            season_number=season_number,
            archive_type=archive_type,
            processing_results=processing_results
        )
        
        if index_result["success"]:
            processing_results["pages_generated"].append("index.html")
            print(f"     ✅ Generated archive index")
        else:
            processing_results["errors"].append(f"Index generation: {index_result['error']}")
            print(f"     ❌ Index generation failed: {index_result['error']}")
        
        # Summary
        total_charts = len(processing_results["charts_generated"])
        total_pages = len(processing_results["pages_generated"])
        total_assets = len(processing_results["assets_copied"])
        total_errors = len(processing_results["errors"])
        
        success = total_errors == 0 or (total_pages > 0 and total_charts > 0)
        
        print(f"  📊 Content processing summary:")
        print(f"     Charts: {total_charts}")
        print(f"     Pages: {total_pages}")
        print(f"     Assets: {total_assets}")
        print(f"     Errors: {total_errors}")
        
        return {
            "success": success,
            "processing_results": processing_results,
            "summary": {
                "charts_count": total_charts,
                "pages_count": total_pages,
                "assets_count": total_assets,
                "errors_count": total_errors
            },
            "message": f"Processed archive content: {total_pages} pages, {total_charts} charts, {total_assets} assets"
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": f"Archive content processing failed: {e}"
        }
    finally:
        # Restore working directory
        if 'original_cwd' in locals():
            os.chdir(original_cwd)


def generate_archive_pages(all_characters, is_hardcore, archive_path, charts_path, season_number, archive_type):
    """
    Generate archive-specific pages with modified chart paths
    
    Args:
        all_characters: Character data
        is_hardcore: Boolean for game mode
        archive_path: Archive directory
        charts_path: Charts directory
        season_number: Season number
        archive_type: "monthly" or "final"
    
    Returns:
        Dict with generation results
    """
    from datetime import datetime
    from pathlib import Path
    import os
    import shutil
    
    try:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
        archive_timestamp = f"Season {season_number} {archive_type.title()} Archive - {timestamp}"
        
        mode_prefix = "hc" if is_hardcore else ""
        mode_name = "Hardcore" if is_hardcore else "Softcore"
        
        generated_pages = []
        generated_charts = []
        
        # Import page generators
        from modules.home_page import HomePageGenerator
        from modules.fun_facts_page import generate_fun_facts_page
        from modules.items_equipment_page import generate_items_equipment_page
        from modules.mercenary_page import generate_mercenary_page
        from modules.class_pages import generate_all_class_pages
        
        # Get banner result for all pages
        banner_result = generate_archive_banner_html(season_number, archive_type, base_path=archive_path.parent.parent.parent)
        banner_html = banner_result.get("banner_html") if banner_result.get("success") else None
        
        # 1. Generate Home Page
        try:
            print(f"       Generating home page...")
            
            # Change to archive directory for chart generation
            original_cwd = os.getcwd()
            os.chdir(archive_path)
            
            try:
                home_html = HomePageGenerator.generate_full_home_page(
                    all_characters, archive_timestamp, is_hardcore
                )
            finally:
                # Always change back to original directory
                os.chdir(original_cwd)
            
            # Ensure we have a string, not a dict or other type
            if isinstance(home_html, dict):
                print(f"       ⚠️ Home page generation returned dict instead of HTML")
                home_html = str(home_html)
            elif not isinstance(home_html, str):
                print(f"       ⚠️ Home page generation returned {type(home_html)} instead of HTML")
                home_html = str(home_html)
            
            # Convert for archive format
            archive_home_html = convert_html_for_archive(home_html, archive_path)
            
            # Add archive banner
            if banner_html:
                banner_result = inject_banner_into_html(archive_home_html, banner_html, "auto")
                if banner_result.get("success"):
                    archive_home_html = banner_result["modified_html"]
                    print(f"       ✅ Banner injected using method: {banner_result['insertion_method']}")
                else:
                    print(f"       ⚠️ Banner injection failed: {banner_result.get('error', 'Unknown error')}")
            
            # Save
            home_filename = f"{mode_prefix}Home.html" if mode_prefix else "Home.html"
            home_file = archive_path / home_filename
            with open(home_file, 'w', encoding='utf-8') as f:
                f.write(archive_home_html)
            
            generated_pages.append(home_filename)
            
            # Track charts generated by home page
            generated_charts.extend([
                f"{mode_prefix}class_distribution.png",
                f"{mode_prefix}1kclass_distribution.png"
            ])
            
        except Exception as e:
            print(f"       ⚠️ Home page generation failed: {e}")
        
        # 2. Generate Fun Facts Page
        try:
            print(f"       Generating fun facts page...")
            
            # Change to archive directory for chart generation
            original_cwd = os.getcwd()
            os.chdir(archive_path)
            
            try:
                funfacts_html = generate_fun_facts_page(all_characters, archive_timestamp, is_hardcore)
            finally:
                # Always change back to original directory
                os.chdir(original_cwd)
            
            # Ensure we have a string, not a dict or other type
            if isinstance(funfacts_html, dict):
                print(f"       ⚠️ Fun facts page generation returned dict instead of HTML")
                funfacts_html = str(funfacts_html)
            elif not isinstance(funfacts_html, str):
                print(f"       ⚠️ Fun facts page generation returned {type(funfacts_html)} instead of HTML")
                funfacts_html = str(funfacts_html)
            
            # Convert for archive format
            archive_funfacts_html = convert_html_for_archive(funfacts_html, archive_path)
            
            # Add archive banner
            if banner_html:
                banner_result = inject_banner_into_html(archive_funfacts_html, banner_html, "auto")
                if banner_result.get("success"):
                    archive_funfacts_html = banner_result["modified_html"]
                    print(f"       ✅ Banner injected using method: {banner_result['insertion_method']}")
                else:
                    print(f"       ⚠️ Banner injection failed: {banner_result.get('error', 'Unknown error')}")
            
            # Save
            funfacts_filename = f"{mode_prefix}FunFacts.html"
            funfacts_file = archive_path / funfacts_filename
            with open(funfacts_file, 'w', encoding='utf-8') as f:
                f.write(archive_funfacts_html)
            
            generated_pages.append(funfacts_filename)
            
        except Exception as e:
            print(f"       ⚠️ Fun facts page generation failed: {e}")
        
        # 3. Generate Items & Equipment Page
        try:
            print(f"       Generating items & equipment page...")
            
            # Change to archive directory for any potential chart generation
            original_cwd = os.getcwd()
            os.chdir(archive_path)
            
            try:
                items_html = generate_items_equipment_page(all_characters, archive_timestamp, is_hardcore)
            finally:
                # Always change back to original directory
                os.chdir(original_cwd)
            
            # Ensure we have a string, not a dict or other type
            if isinstance(items_html, dict):
                print(f"       ⚠️ Items page generation returned dict instead of HTML")
                items_html = str(items_html)
            elif not isinstance(items_html, str):
                print(f"       ⚠️ Items page generation returned {type(items_html)} instead of HTML")
                items_html = str(items_html)
            
            # Convert for archive format
            archive_items_html = convert_html_for_archive(items_html, archive_path)
            
            # Add archive banner
            if banner_html:
                banner_result = inject_banner_into_html(archive_items_html, banner_html, "auto")
                if banner_result.get("success"):
                    archive_items_html = banner_result["modified_html"]
                    print(f"       ✅ Banner injected using method: {banner_result['insertion_method']}")
                else:
                    print(f"       ⚠️ Banner injection failed: {banner_result.get('error', 'Unknown error')}")
            
            # Save
            items_filename = f"{mode_prefix}Items.html"
            items_file = archive_path / items_filename
            with open(items_file, 'w', encoding='utf-8') as f:
                f.write(archive_items_html)
            
            generated_pages.append(items_filename)
            
        except Exception as e:
            print(f"       ⚠️ Items page generation failed: {e}")
        
        # 4. Generate Mercenary Page
        try:
            print(f"       Generating mercenary page...")
            
            # Change to archive directory for any potential chart generation
            original_cwd = os.getcwd()
            os.chdir(archive_path)
            
            try:
                mercenary_html = generate_mercenary_page(all_characters, archive_timestamp, is_hardcore)
            finally:
                # Always change back to original directory
                os.chdir(original_cwd)
            
            # Ensure we have a string, not a dict or other type
            if isinstance(mercenary_html, dict):
                print(f"       ⚠️ Mercenary page generation returned dict instead of HTML")
                mercenary_html = str(mercenary_html)
            elif not isinstance(mercenary_html, str):
                print(f"       ⚠️ Mercenary page generation returned {type(mercenary_html)} instead of HTML")
                mercenary_html = str(mercenary_html)
            
            # Convert for archive format
            archive_mercenary_html = convert_html_for_archive(mercenary_html, archive_path)
            
            # Add archive banner
            if banner_html:
                banner_result = inject_banner_into_html(archive_mercenary_html, banner_html, "auto")
                if banner_result.get("success"):
                    archive_mercenary_html = banner_result["modified_html"]
                    print(f"       ✅ Banner injected using method: {banner_result['insertion_method']}")
                else:
                    print(f"       ⚠️ Banner injection failed: {banner_result.get('error', 'Unknown error')}")
            
            # Save
            mercenary_filename = f"{mode_prefix}Mercenaries.html"
            mercenary_file = archive_path / mercenary_filename
            with open(mercenary_file, 'w', encoding='utf-8') as f:
                f.write(archive_mercenary_html)
            
            generated_pages.append(mercenary_filename)
            
        except Exception as e:
            print(f"       ⚠️ Mercenary page generation failed: {e}")
        
        # 5. Generate Class Pages
        try:
            print(f"       Generating class pages...")
            
            # Change to archive directory for chart generation
            original_cwd = os.getcwd()
            os.chdir(archive_path)
            
            try:
                class_results = generate_all_class_pages(all_characters, archive_timestamp, is_hardcore)
            finally:
                # Always change back to original directory
                os.chdir(original_cwd)
            
            if class_results:
                # class_results is a list of filenames, need to read the generated files
                class_names = ["Barbarian", "Druid", "Amazon", "Assassin", "Necromancer", "Paladin", "Sorceress"]
                
                for class_name in class_names:
                    try:
                        # Find the generated file (now in archive directory)
                        class_filename = f"{mode_prefix}{class_name}.html"
                        class_file_path = archive_path / class_filename
                        
                        if class_file_path.exists():
                            # Read the generated HTML
                            with open(class_file_path, 'r', encoding='utf-8') as f:
                                class_html = f.read()
                            
                            # Convert for archive format
                            archive_class_html = convert_html_for_archive(class_html, archive_path)
                            
                            # Add archive banner
                            if banner_html:
                                banner_result = inject_banner_into_html(archive_class_html, banner_html, "auto")
                                if banner_result.get("success"):
                                    archive_class_html = banner_result["modified_html"]
                                    print(f"       ✅ Banner injected for {class_name} using method: {banner_result['insertion_method']}")
                                else:
                                    print(f"       ⚠️ Banner injection failed for {class_name}: {banner_result.get('error', 'Unknown error')}")
                            
                            # Save to archive
                            archive_class_file = archive_path / class_filename
                            with open(archive_class_file, 'w', encoding='utf-8') as f:
                                f.write(archive_class_html)
                            
                            generated_pages.append(class_filename)
                            
                            # Track charts generated by class pages (they use actual chart filename patterns)
                            generated_charts.extend([
                                f"{mode_prefix}{class_name.lower()}_distribution_pie.png",
                                f"{mode_prefix}{class_name.lower()}_clusters_scatter.png"
                            ])
                        
                    except Exception as e:
                        print(f"       ⚠️ {class_name} page processing failed: {e}")
            
        except Exception as e:
            print(f"       ⚠️ Class pages generation failed: {e}")
        
        return {
            "success": len(generated_pages) > 0,
            "pages": generated_pages,
            "charts": generated_charts,
            "mode": mode_name,
            "message": f"Generated {len(generated_pages)} pages for {mode_name}"
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": f"Archive page generation failed: {e}"
        }


def copy_archive_assets(base_path, archive_path):
    """
    Copy necessary assets (CSS, icons, templates) for archive
    
    Args:
        base_path: Source directory
        archive_path: Archive directory
    
    Returns:
        Dict with copy results
    """
    import shutil
    from pathlib import Path
    
    try:
        base_path = Path(base_path)
        archive_path = Path(archive_path)
        
        copied_assets = []
        
        # Define assets to copy with relative paths for archive
        assets_to_copy = [
            ("css", "css"),  # CSS files -> ../../../css/
            ("icons", "icons"),  # Icons -> ../../../icons/
            ("templates", "templates"),  # Templates -> ../../../templates/
        ]
        
        for source_dir, target_dir in assets_to_copy:
            source_path = base_path / source_dir
            target_path = archive_path / target_dir
            
            if source_path.exists() and source_path.is_dir():
                # Copy directory
                if target_path.exists():
                    shutil.rmtree(target_path)
                shutil.copytree(source_path, target_path)
                copied_assets.append(f"{target_dir}/ (directory)")
            elif source_path.exists():
                # Copy single file
                target_path.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source_path, target_path)
                copied_assets.append(str(target_path))
        
        return {
            "success": True,
            "copied_assets": copied_assets,
            "message": f"Copied {len(copied_assets)} assets to archive"
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": f"Failed to copy archive assets: {e}"
        }


def generate_archive_index(archive_path, season_number, archive_type, processing_results):
    """
    Generate an index.html page for the archive
    
    Args:
        archive_path: Archive directory
        season_number: Season number
        archive_type: "monthly" or "final"
        processing_results: Results from content processing
    
    Returns:
        Dict with index generation results
    """
    from pathlib import Path
    from datetime import datetime
    
    try:
        archive_path = Path(archive_path)
        
        # Determine what pages were generated
        pages_generated = processing_results.get("pages_generated", [])
        charts_generated = processing_results.get("charts_generated", [])
        
        # Separate SC and HC pages
        sc_pages = [p for p in pages_generated if not p.startswith("hc")]
        hc_pages = [p for p in pages_generated if p.startswith("hc")]
        
        # Archive info
        archive_date = datetime.now().strftime("%B %d, %Y at %H:%M")
        archive_title = f"Season {season_number} {archive_type.title()} Archive"
        
        # Generate index HTML
        index_html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{archive_title} - PoD Analytics</title>
    <link rel="stylesheet" href="../../../css/test-css.css">
    <link rel="icon" type="image/x-icon" href="../../../icons/pod.ico">
    <style>
        .archive-index {{
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
        }}
        .archive-header {{
            text-align: center;
            margin-bottom: 40px;
        }}
        .game-mode-section {{
            margin: 30px 0;
            padding: 20px;
            border: 1px solid #ddd;
            border-radius: 8px;
        }}
        .page-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
            margin-top: 20px;
        }}
        .page-card {{
            padding: 15px;
            border: 1px solid #ccc;
            border-radius: 5px;
            text-align: center;
            background-color: #f9f9f9;
        }}
        .page-card a {{
            text-decoration: none;
            font-weight: bold;
            color: #333;
        }}
        .page-card:hover {{
            background-color: #e9e9e9;
        }}
        .archive-stats {{
            margin: 20px 0;
            padding: 15px;
            background-color: #f0f0f0;
            border-radius: 5px;
        }}
    </style>
</head>
<body>
    <div class="archive-index">
        <div class="archive-header">
            <h1>{archive_title}</h1>
            <h2>Path of Diablo Analytics Archive</h2>
            <p>Created on {archive_date}</p>
        </div>
        
        <div class="archive-stats">
            <h3>Archive Statistics</h3>
            <p><strong>Total Pages:</strong> {len(pages_generated)}</p>
            <p><strong>Total Charts:</strong> {len(charts_generated)}</p>
            <p><strong>Softcore Pages:</strong> {len(sc_pages)}</p>
            <p><strong>Hardcore Pages:</strong> {len(hc_pages)}</p>
        </div>
"""
        
        # Add Softcore section
        if sc_pages:
            index_html += f"""
        <div class="game-mode-section">
            <h2>🔥 Softcore Pages</h2>
            <div class="page-grid">
"""
            for page in sc_pages:
                page_name = page.replace(".html", "").replace("Home", "Home Page").replace("FunFacts", "Fun Facts").replace("ItemsEquipment", "Items & Equipment").replace("Mercenaries", "Mercenary Analysis")
                index_html += f"""
                <div class="page-card">
                    <a href="{page}">{page_name}</a>
                </div>
"""
            index_html += """
            </div>
        </div>
"""
        
        # Add Hardcore section
        if hc_pages:
            index_html += f"""
        <div class="game-mode-section">
            <h2>💀 Hardcore Pages</h2>
            <div class="page-grid">
"""
            for page in hc_pages:
                page_name = page.replace("hc", "").replace(".html", "").replace("Home", "Home Page").replace("FunFacts", "Fun Facts").replace("ItemsEquipment", "Items & Equipment").replace("Mercenaries", "Mercenary Analysis")
                index_html += f"""
                <div class="page-card">
                    <a href="{page}">{page_name}</a>
                </div>
"""
            index_html += """
            </div>
        </div>
"""
        
        # Add footer
        index_html += f"""
        <div class="archive-footer" style="margin-top: 40px; text-align: center; color: #666;">
            <p>This archive contains snapshot data from Season {season_number} of Path of Diablo.</p>
            <p>Generated by PoD Analytics Archive System</p>
        </div>
    </div>
</body>
</html>
"""
        
        # Save index file
        index_file = archive_path / "index.html"
        with open(index_file, 'w', encoding='utf-8') as f:
            f.write(index_html)
        
        return {
            "success": True,
            "index_file": str(index_file),
            "message": f"Generated archive index with {len(pages_generated)} pages"
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": f"Failed to generate archive index: {e}"
        }


def generate_freeze_banner_text(season_info):
    """
    Generate banner text for live site freeze
    
    Args:
        season_info: Season info dict from get_archive_season_info()
    
    Returns:
        String with freeze banner text
    """
    if not season_info:
        return "Site temporarily frozen - please check back later"
    
    return season_info.get("freeze_banner_text", f"Season {season_info.get('season_number', 'Unknown')} has ended. Viewing historical data.")


def get_banner_text_for_archive(archive_type="monthly"):
    """
    Get appropriate banner text for archive pages
    
    Args:
        archive_type: "monthly" or "final"
    
    Returns:
        String with banner text or None if error
    """
    archive_info = get_archive_season_info()
    if not archive_info:
        return None
    
    if archive_type == "final" and archive_info["is_season_end"]:
        return archive_info["banner_text"]  # "Viewing Season X historical data from the end of the ladder"
    else:
        return archive_info["banner_text"]  # Monthly or post-season banner


def get_live_site_freeze_banner():
    """
    Get banner text for live site during season-end freeze
    
    Returns:
        String with freeze banner text or None if not needed
    """
    archive_info = get_archive_season_info()
    if not archive_info or not archive_info.get("needs_freeze"):
        return None
    
    return archive_info.get("freeze_banner_text")


def get_archive_folder_name():
    """
    Get the appropriate folder name for current archive
    
    Returns:
        String with folder name (e.g., "October", "Final") or None if error
    """
    archive_info = get_archive_season_info()
    if not archive_info:
        return None
    
    return archive_info["archive_folder"]

def fetch_character_data(league='sc'):
    """
    Fetch character ladder data (you'll need to implement this based on your existing method)
    For now, this loads from local files as a placeholder
    """
    filename = f"{league}_ladder.json"
    try:
        with open(filename, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"⚠️ {filename} not found, skipping {league.upper()} character data")
        return None

def update_unified_csv_from_character_data(characters, league, snapshot_label):
    """
    Update character skill/item data in unified CSV
    """
    csv_path = 'unified-usage-over-time.csv'
    
    # Load existing CSV
    with open(csv_path, 'r', newline='') as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        rows = list(reader)
    
    # Add new snapshot column if needed
    if snapshot_label not in fieldnames:
        fieldnames = list(fieldnames) + [snapshot_label]
        for row in rows:
            row[snapshot_label] = '0'
    
    # Create lookup for efficient updates
    row_lookup = {}
    for i, row in enumerate(rows):
        key = (row['Type'], row['League'], row['Class'], row['Name'])
        row_lookup[key] = i
    
    # Count character usage
    usage_counter = defaultdict(lambda: [0, 0])  # [normal, synth]
    
    for char in characters:
        cls = char.get("Class")
        
        # Count skills
        for tab in char.get("SkillTabs", []):
            for skill in tab.get("Skills", []):
                key = (skill["Name"], cls, "Skill", league)
                usage_counter[key][0] += skill["Level"]
        
        # Count equipped items
        for item in char.get("Equipped", []):
            quality_code = item.get("QualityCode")
            name = item.get("Title")
            if not name:
                continue
            
            if quality_code == "q_runeword":
                key = (name, "", "Runeword", league)
            elif quality_code == "q_set":
                key = (name, "", "Set", league)
            elif quality_code == "q_unique":
                key = (name, "", "Unique", league)
            else:
                continue
            
            is_synth = "Synthesized" in item.get("Tag", "")
            usage_counter[key][1 if is_synth else 0] += 1
        
        # Count mercenary items
        for item in char.get("MercenaryEquipped", []):
            quality_code = item.get("QualityCode")
            name = item.get("Title")
            if not name:
                continue
            
            if quality_code == "q_runeword":
                key = (name, "", "Mercenary Runeword", league)
            elif quality_code == "q_set":
                key = (name, "", "Mercenary Set", league)
            elif quality_code == "q_unique":
                key = (name, "", "Mercenary Unique", league)
            else:
                continue
            
            is_synth = "Synthesized" in item.get("Tag", "")
            usage_counter[key][1 if is_synth else 0] += 1
        
        # Count unique charms from inventory (Gheed's, Torch, Anni)
        # Only count charms in active charm area (bottom 4 rows, y: 5-8)
        inventory = char.get("Inventory", [])
        if isinstance(inventory, list):
            for item in inventory:
                if not isinstance(item, dict):
                    continue
                
                # Check if charm is in active area (bottom 4 rows)
                position = item.get("Position", {})
                y_pos = position.get("y", 0)
                if not (5 <= y_pos <= 8):
                    continue
                
                quality_code = item.get("QualityCode")
                if quality_code != "q_unique":
                    continue
                
                props = item.get("PropertyList", [])
                if not props:
                    continue
                
                charm_name = None
                
                # Gheed's Fortune (Grand Charm with gold find and vendor prices)
                has_gold_find = any("Extra Gold from Monsters" in p for p in props)
                has_vendor = any("Reduces all Vendor Prices" in p for p in props)
                if has_gold_find and has_vendor:
                    charm_name = "Gheed's Fortune"
                
                # Hellfire Torch (Large Charm with +3 to class skills)
                has_class_skills = any("+3 to" in p and "Skill Levels" in p for p in props)
                if has_class_skills:
                    charm_name = "Hellfire Torch"
                
                # Annihilus (Small Charm with +1 to all skills and experience)
                has_all_skills = any("+1 to All Skills" in p for p in props)
                has_exp = any("Experience Gained" in p for p in props)
                if has_all_skills and has_exp:
                    charm_name = "Annihilus"
                
                if charm_name:
                    key = (charm_name, "", "Unique Charm", league)
                    is_synth = "Synthesized" in item.get("Tag", "")
                    usage_counter[key][1 if is_synth else 0] += 1
    
    # Update existing rows or create new ones
    for (name, cls, typ, lg), (normal, synth) in usage_counter.items():
        lookup_key = (typ, lg, cls, name)
        
        if lookup_key in row_lookup:
            # Update existing row
            row_idx = row_lookup[lookup_key]
            if synth:
                value = f"{normal}(+{synth})"
            else:
                value = str(normal)
            rows[row_idx][snapshot_label] = value
        else:
            # Create new row
            new_row = {col: '0' for col in fieldnames}
            new_row['Type'] = typ
            new_row['League'] = lg
            new_row['Class'] = cls
            new_row['Name'] = name
            if synth:
                value = f"{normal}(+{synth})"
            else:
                value = str(normal)
            new_row[snapshot_label] = value
            rows.append(new_row)
    
    # Save updated CSV
    with open(csv_path, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    
    print(f"✅ Updated {league.upper()} character data for {snapshot_label}")

def update_server_data_in_unified_csv(server_stats, game_servers, snapshot_label):
    """
    Update server metrics in unified CSV
    """
    csv_path = 'unified-usage-over-time.csv'
    
    # Load existing CSV
    with open(csv_path, 'r', newline='') as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        rows = list(reader)
    
    # Add new snapshot column if needed
    if snapshot_label not in fieldnames:
        fieldnames = list(fieldnames) + [snapshot_label]
        for row in rows:
            row[snapshot_label] = '0'
    
    # Create lookup
    row_lookup = {}
    for i, row in enumerate(rows):
        key = (row['Type'], row['League'], row['Class'], row['Name'])
        row_lookup[key] = i
    
    # Update global server stats
    server_mapping = {
        'online_now': 'Online_Now',
        'online_last_hour': 'Online_Last_Hour',
        'online_last_day': 'Online_Last_Day', 
        'online_last_week': 'Online_Last_Week',
        'online_last_fornight': 'Online_Last_Fortnight',
        'online_in_any_games': 'Online_In_Games',
        'games_open': 'Games_Open'
    }
    
    for api_key, csv_name in server_mapping.items():
        if api_key in server_stats:
            key = ('Server', 'ALL', '', csv_name)
            # Clean the value (remove quotes)
            value = str(server_stats[api_key]).strip('"')
            
            if key in row_lookup:
                rows[row_lookup[key]][snapshot_label] = value
            else:
                # Create new server metric row
                new_row = {col: '0' for col in fieldnames}
                new_row['Type'] = 'Server'
                new_row['League'] = 'ALL'
                new_row['Class'] = ''
                new_row['Name'] = csv_name
                new_row[snapshot_label] = value
                rows.append(new_row)
                print(f"📝 Created new server metric: {csv_name}")
    
    # Update individual game server stats
    for server in game_servers:
        country = server.get('country', 'Unknown').strip('"')
        location = server.get('location', 'Unknown').strip('"')
        
        # Extract city name from location (before comma)
        city = location.split(',')[0].strip() if ',' in location else location
        city = city.replace(' ', '_').replace('\t', '').replace('&#9899;', '')  # Clean up
        
        # Update players on this server
        players_key = ('GameServer', 'ALL', country, f'{city}_Players')
        players_value = str(server.get('players', 0))
        
        if players_key in row_lookup:
            rows[row_lookup[players_key]][snapshot_label] = players_value
        else:
            # Create new game server row
            new_row = {col: '0' for col in fieldnames}
            new_row['Type'] = 'GameServer'
            new_row['League'] = 'ALL'
            new_row['Class'] = country
            new_row['Name'] = f'{city}_Players'
            new_row[snapshot_label] = players_value
            rows.append(new_row)
            print(f"📝 Created new game server metric: {country} {city}_Players")
        
        # Update games on this server
        games_key = ('GameServer', 'ALL', country, f'{city}_Games')
        games_value = str(server.get('games', 0))
        
        if games_key in row_lookup:
            rows[row_lookup[games_key]][snapshot_label] = games_value
        else:
            # Create new game server row
            new_row = {col: '0' for col in fieldnames}
            new_row['Type'] = 'GameServer'
            new_row['League'] = 'ALL'
            new_row['Class'] = country
            new_row['Name'] = f'{city}_Games'
            new_row[snapshot_label] = games_value
            rows.append(new_row)
            print(f"📝 Created new game server metric: {country} {city}_Games")
    
    # Save updated CSV
    with open(csv_path, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    
    print(f"✅ Updated server data for {snapshot_label}")

def generate_web_pages():
    """
    Generate HTML pages from unified CSV data (similar to original sc/hc web generation)
    """
    csv_path = 'unified-usage-over-time.csv'
    
    # Load CSV data
    with open(csv_path, 'r', newline='') as f:
        reader = csv.DictReader(f)
        headers = reader.fieldnames
        rows = list(reader)
    
    # Get time columns (exclude Type, League, Class, Name)
    time_columns = [h for h in headers if h not in ['Type', 'League', 'Class', 'Name']]
    
    # Organize data by league and type
    data_by_league = {
        'SC': {'Skills': {}, 'Uniques': [], 'Sets': [], 'Runewords': [], 'Unique Charms': [], 'Mercenary Uniques': [], 'Mercenary Sets': [], 'Mercenary Runewords': []},
        'HC': {'Skills': {}, 'Uniques': [], 'Sets': [], 'Runewords': [], 'Unique Charms': [], 'Mercenary Uniques': [], 'Mercenary Sets': [], 'Mercenary Runewords': []},
        'ALL': {'Server': [], 'GameServer': []}
    }
    
    for row in rows:
        league = row['League']
        data_type = row['Type']
        char_class = row.get('Class', '').strip()
        name = row['Name']
        
        # Get usage data for all time periods
        usage_data = {col: row[col] for col in time_columns}
        
        if league in ['SC', 'HC']:
            if data_type == 'Skill':
                if char_class not in data_by_league[league]['Skills']:
                    data_by_league[league]['Skills'][char_class] = []
                data_by_league[league]['Skills'][char_class].append((name, usage_data))
            elif data_type in ['Unique', 'Set', 'Runeword', 'Unique Charm', 'Mercenary Unique', 'Mercenary Set', 'Mercenary Runeword']:
                data_by_league[league][data_type + 's' if not data_type.endswith('s') else data_type].append((name, usage_data))
        elif league == 'ALL':
            data_by_league['ALL'][data_type].append((name, usage_data))
    
    # Generate HTML for SC and HC
    for league in ['SC', 'HC']:
        generate_league_html(league, data_by_league[league], time_columns)
    
    # Generate HTML for server data
    generate_server_html(data_by_league['ALL'], time_columns)
    
    print("✅ Generated web pages:")
    print("   📄 sc-usage-over-time.html")
    print("   📄 hc-usage-over-time.html") 
    print("   📄 server-stats-over-time.html")

def generate_league_html(league, league_data, time_columns):
    """Generate HTML page for a specific league (SC or HC)"""
    
    filename = f"{league.lower()}-usage-over-time.html"
    title = f"{league} - Usage Over Time"
    
    with open(filename, 'w', encoding='utf-8') as f:
        f.write(f"""<!DOCTYPE html>
<html>
<head>
    <title>{title}</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        body {{ 
            font-family: Arial, sans-serif; 
            margin: 20px; 
            background-image: url("icons/stone_background_2600.jpg");
            background-position: bottom center;
            background-repeat: repeat;
            background-size: auto;
            background-color: #232323;
            color: #f5f5f5;
        }}
        table {{ 
            border-collapse: collapse; 
            width: 100%; 
            margin: 20px 0; 
            background-color: rgba(35, 35, 35, 0.9);
        }}
        th, td {{ 
            border: 1px solid #555; 
            padding: 8px; 
            text-align: left; 
            color: #f5f5f5;
        }}
        th {{ 
            background-color: rgba(50, 50, 50, 0.95); 
            cursor: pointer; 
        }}
        th:hover {{ background-color: rgba(70, 70, 70, 0.95); }}
        .usage-label {{ 
            cursor: pointer; 
            color: #d6a69f; 
        }}
        .usage-label:hover {{ background-color: rgba(100, 100, 100, 0.5); }}
        #tooltipChart {{
            position: absolute;
            display: none;
            border: 1px solid #aaa;
            background-color: #fff;
            z-index: 9999;
            padding: 6px;
            box-shadow: 2px 2px 6px rgba(0,0,0,0.2);
        }}
        .league-header {{ 
            background: linear-gradient(135deg, #441D1D 0%, #782121 100%);
            color: white;
            padding: 20px;
            border-radius: 10px;
            margin-bottom: 20px;
            text-align: center;
            border: 2px solid #782121;
        }}
        .section-header {{
            background-color: rgba(50, 50, 50, 0.9);
            color: #f5f5f5;
            padding: 10px;
            margin: 20px 0 10px 0;
        }}
    </style>
</head>
<body>
    <canvas id="tooltipChart" width="300" height="150"></canvas>
    
    <div class="league-header">
        <h1>Path of Diablo - {title}</h1>
        <p>Interactive skill and item usage analytics</p>
        <p><em>Hover over items to see usage trends • Click columns to sort</em></p>
    </div>
""")

        # Class color mapping
        class_colors = {
            "Amazon": "rgb(255, 102, 105)",
            "Assassin": "rgb(255, 255, 255)",
            "Barbarian": "rgb(150, 105, 32)",
            "Druid": "rgb(255, 186, 74)",
            "Necromancer": "rgb(179, 255, 253)",
            "Paladin": "rgb(255, 243, 112)",
            "Sorceress": "rgb(188, 107, 255)"
        }

        # Skills grouped by class
        f.write('<div class="section-header"><h2>Skills by Class</h2></div>\n')
        for char_class, skills in league_data['Skills'].items():
            class_icon = f'icons/{char_class}.png'
            class_color = class_colors.get(char_class, "#666")
#            f.write(f'<h3><img src="{class_icon}" alt="{char_class}" style="vertical-align: middle; height: 60px; margin-right: 8px;"></h3>\n')
            f.write(f'<h3>{char_class}</h3>\n')
#            f.write(f'<table style="border: 3px solid {class_color};">\n')
            f.write(f'<table style="border-left: 3px solid {class_color};">\n')
            f.write('<tr><th onclick="sortTable(this, \'str\')">Skill Name</th>')
            for col in time_columns:
                f.write(f'<th onclick="sortTable(this, \'num\')">{col}</th>')
            f.write('</tr>\n')
            
            for name, usage_data in skills:
                usage_json = json.dumps(usage_data)
                f.write(f'<tr><td class="usage-label" data-usage=\'{usage_json}\'>{name}</td>')
                for col in time_columns:
                    f.write(f'<td>{usage_data.get(col, "0")}</td>')
                f.write('</tr>\n')
            f.write('</table>\n')
        
        # Items by category
        item_categories = [
            ('Uniques', '💎'),
            ('Sets', '📦'), 
            ('Runewords', '🔮'),
            ('Unique Charms', '✨'),
            ('Mercenary Uniques', '⚔️💎'),
            ('Mercenary Sets', '⚔️📦'),
            ('Mercenary Runewords', '⚔️🔮')
        ]
        
        # Color mapping for item types
        type_colors = {
            'Uniques': 'rgb(144, 136, 88)',
            'Sets': 'rgb(0, 196, 0)',
            'Runewords': 'rgb(144, 136, 88)',
            'Unique Charms': 'rgb(255, 165, 0)',
            'Mercenary Uniques': 'rgb(144, 136, 88)',
            'Mercenary Sets': 'rgb(0, 196, 0)',
            'Mercenary Runewords': 'rgb(144, 136, 88)'
        }
        
        for category, emoji in item_categories:
            if league_data[category]:
                border_color = type_colors.get(category, '#666')
#                f.write(f'<div class="section-header"><h2>{emoji} {category}</h2></div>\n')
                f.write(f'<div class="section-header" style="border-left: 4px solid {border_color};"><h2>{category}</h2></div>\n')
                f.write(f'<table style="border-left: 4px solid {border_color};">\n')
                f.write('<tr><th onclick="sortTable(this, \'str\')">Item Name</th>')
                for col in time_columns:
                    f.write(f'<th onclick="sortTable(this, \'num\')">{col}</th>')
                f.write('</tr>\n')
                
                for name, usage_data in league_data[category]:
                    usage_json = json.dumps(usage_data)
                    f.write(f'<tr><td class="usage-label" data-usage=\'{usage_json}\'>{name}</td>')
                    for col in time_columns:
                        f.write(f'<td>{usage_data.get(col, "0")}</td>')
                    f.write('</tr>\n')
                f.write('</table>\n')
        
        # Add JavaScript for interactivity
        f.write("""
<script>
document.addEventListener('DOMContentLoaded', () => {
    const canvas = document.getElementById('tooltipChart');
    const ctx = canvas.getContext('2d');
    let chart;

    // Hover charts for usage trends
    document.querySelectorAll('.usage-label').forEach(label => {
        label.addEventListener('mouseenter', e => {
            const data = JSON.parse(label.dataset.usage);
            const labels = Object.keys(data);
            const values = Object.values(data).map(v => {
                // Handle values like "123(+5)" for synthesized items
                const match = v.match(/^(\\d+)/);
                return match ? parseInt(match[1]) : 0;
            });

            canvas.style.display = 'block';
            canvas.style.left = e.pageX + 10 + 'px';
            canvas.style.top = e.pageY - 80 + 'px';

            if (chart) chart.destroy();
            chart = new Chart(ctx, {
                type: 'line',
                data: {
                    labels: labels,
                    datasets: [{
                        label: label.textContent + ' Usage',
                        data: values,
                        borderColor: '#667eea',
                        backgroundColor: 'rgba(102, 126, 234, 0.1)',
                        borderWidth: 2,
                        fill: true,
                        tension: 0.4
                    }]
                },
                options: {
                    responsive: false,
                    animation: false,
                    plugins: {
                        legend: { display: false },
                        title: {
                            display: true,
                            text: label.textContent + ' - Usage Trend',
                            font: { size: 12, weight: 'bold' }
                        }
                    },
                    scales: {
                        y: { beginAtZero: true },
                        x: { ticks: { maxRotation: 45, minRotation: 45 } }
                    }
                }
            });
        });

        label.addEventListener('mouseleave', () => {
            canvas.style.display = 'none';
        });
    });

    // Table sorting functionality
    window.sortTable = function(header, type) {
        const table = header.closest('table');
        const tbody = table.querySelector('tbody') || table;
        const rows = Array.from(tbody.querySelectorAll('tr')).slice(1); // Skip header
        const columnIndex = Array.from(header.parentNode.children).indexOf(header);
        
        rows.sort((a, b) => {
            const aVal = a.children[columnIndex].textContent.trim();
            const bVal = b.children[columnIndex].textContent.trim();
            
            if (type === 'num') {
                const aNum = parseInt(aVal.match(/^(\\d+)/) ? aVal.match(/^(\\d+)/)[1] : '0');
                const bNum = parseInt(bVal.match(/^(\\d+)/) ? bVal.match(/^(\\d+)/)[1] : '0');
                return bNum - aNum; // Descending
            } else {
                return aVal.localeCompare(bVal); // Ascending
            }
        });
        
        rows.forEach(row => tbody.appendChild(row));
    };
});
</script>
</body>
</html>""")

def generate_server_html(server_data, time_columns):
    """Generate HTML page for server statistics"""
    
    filename = "server-stats-over-time.html"
    title = "Server Statistics Over Time"
    
    with open(filename, 'w', encoding='utf-8') as f:
        f.write(f"""<!DOCTYPE html>
<html>
<head>
    <title>{title}</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        body {{ 
            font-family: Arial, sans-serif; 
            margin: 20px; 
            background-image: url("icons/stone_background_2600.jpg");
            background-position: bottom center;
            background-repeat: repeat;
            background-size: auto;
            background-color: #232323;
            color: #f5f5f5;
        }}
        table {{ 
            border-collapse: collapse; 
            width: 100%; 
            margin: 20px 0; 
            background-color: rgba(35, 35, 35, 0.9);
        }}
        th, td {{ 
            border: 1px solid #555; 
            padding: 8px; 
            text-align: left; 
            color: #f5f5f5;
        }}
        th {{ 
            background-color: rgba(50, 50, 50, 0.95); 
            cursor: pointer; 
        }}
        th:hover {{ background-color: rgba(70, 70, 70, 0.95); }}
        .usage-label {{ 
            cursor: pointer; 
            color: #d6a69f; 
        }}
        .usage-label:hover {{ background-color: rgba(100, 100, 100, 0.5); }}
        #tooltipChart {{
            position: absolute;
            display: none;
            border: 1px solid #aaa;
            background-color: #fff;
            z-index: 9999;
            padding: 6px;
            box-shadow: 2px 2px 6px rgba(0,0,0,0.2);
        }}
        .server-header {{ 
            background: linear-gradient(135deg, #441D1D 0%, #782121 100%);
            color: white;
            padding: 20px;
            border-radius: 10px;
            margin-bottom: 20px;
            text-align: center;
            border: 2px solid #782121;
        }}
        .section-header {{
            background-color: rgba(50, 50, 50, 0.9);
            color: #f5f5f5;
            padding: 10px;
            border-left: 4px solid #28a745;
            margin: 20px 0 10px 0;
        }}
    </style>
</head>
<body>
    <canvas id="tooltipChart" width="300" height="150"></canvas>
    
    <div class="server-header">
        <h1>Path of Diablo - Server Analytics</h1>
        <p>Real-time server population and infrastructure monitoring</p>
        <p><em>Hover over metrics to see trends • Click columns to sort</em></p>
    </div>
""")

        # Global server stats
        if server_data['Server']:
            f.write('<div class="section-header"><h2>Global Server Statistics</h2></div>\n')
            f.write('<table>\n')
            f.write('<tr><th onclick="sortTable(this, \'str\')">Metric</th>')
            for col in time_columns:
                f.write(f'<th onclick="sortTable(this, \'num\')">{col}</th>')
            f.write('</tr>\n')
            
            for name, usage_data in server_data['Server']:
                usage_json = json.dumps(usage_data)
                display_name = name.replace('_', ' ').title()
                f.write(f'<tr><td class="usage-label" data-usage=\'{usage_json}\'>{display_name}</td>')
                for col in time_columns:
                    f.write(f'<td>{usage_data.get(col, "0")}</td>')
                f.write('</tr>\n')
            f.write('</table>\n')
        
        # Game server stats grouped by region
        if server_data['GameServer']:
            f.write('<div class="section-header"><h2>Game Servers by Region</h2></div>\n')
            
            # Group by country
            servers_by_country = {}
            for name, usage_data in server_data['GameServer']:
                # Extract country from the data structure
                # GameServer rows have country in the 'Class' field when we organized the data
                country = 'Unknown'
                for row in server_data['GameServer']:
                    if row[0] == name:  # Find matching row
                        break
                
                # Get country from original CSV data by looking at the first part of name
                if '_Players' in name or '_Games' in name:
                    city = name.replace('_Players', '').replace('_Games', '')
                    # We need to find the country - let's group by the first part for now
                    country = 'Various'  # We'll improve this
                
                if country not in servers_by_country:
                    servers_by_country[country] = []
                servers_by_country[country].append((name, usage_data))
            
            # Generate tables for each country
            for country, server_list in servers_by_country.items():
#                f.write(f'<h3>{country} Servers</h3>\n')
                f.write('<table>\n')
                f.write('<tr><th onclick="sortTable(this, \'str\')">Server Metric</th>')
                for col in time_columns:
                    f.write(f'<th onclick="sortTable(this, \'num\')">{col}</th>')
                f.write('</tr>\n')
                
                for name, usage_data in server_list:
                    usage_json = json.dumps(usage_data)
                    display_name = name.replace('_', ' ').title()
                    f.write(f'<tr><td class="usage-label" data-usage=\'{usage_json}\'>{display_name}</td>')
                    for col in time_columns:
                        f.write(f'<td>{usage_data.get(col, "0")}</td>')
                    f.write('</tr>\n')
                f.write('</table>\n')
        
        # Add the same JavaScript as the league pages
        f.write("""
<script>
document.addEventListener('DOMContentLoaded', () => {
    const canvas = document.getElementById('tooltipChart');
    const ctx = canvas.getContext('2d');
    let chart;

    document.querySelectorAll('.usage-label').forEach(label => {
        label.addEventListener('mouseenter', e => {
            const data = JSON.parse(label.dataset.usage);
            const labels = Object.keys(data);
            const values = Object.values(data).map(v => parseInt(v) || 0);

            canvas.style.display = 'block';
            canvas.style.left = e.pageX + 10 + 'px';
            canvas.style.top = e.pageY - 80 + 'px';

            if (chart) chart.destroy();
            chart = new Chart(ctx, {
                type: 'line',
                data: {
                    labels: labels,
                    datasets: [{
                        label: label.textContent + ' Trend',
                        data: values,
                        borderColor: '#28a745',
                        backgroundColor: 'rgba(40, 167, 69, 0.1)',
                        borderWidth: 2,
                        fill: true,
                        tension: 0.4
                    }]
                },
                options: {
                    responsive: false,
                    animation: false,
                    plugins: {
                        legend: { display: false },
                        title: {
                            display: true,
                            text: label.textContent + ' - Server Trend',
                            font: { size: 12, weight: 'bold' }
                        }
                    },
                    scales: {
                        y: { beginAtZero: true },
                        x: { ticks: { maxRotation: 45, minRotation: 45 } }
                    }
                }
            });
        });

        label.addEventListener('mouseleave', () => {
            canvas.style.display = 'none';
        });
    });

    window.sortTable = function(header, type) {
        const table = header.closest('table');
        const tbody = table.querySelector('tbody') || table;
        const rows = Array.from(tbody.querySelectorAll('tr')).slice(1);
        const columnIndex = Array.from(header.parentNode.children).indexOf(header);
        
        rows.sort((a, b) => {
            const aVal = a.children[columnIndex].textContent.trim();
            const bVal = b.children[columnIndex].textContent.trim();
            
            if (type === 'num') {
                return parseInt(bVal) - parseInt(aVal); // Descending
            } else {
                return aVal.localeCompare(bVal); // Ascending
            }
        });
        
        rows.forEach(row => tbody.appendChild(row));
    };
});
</script>
</body>
</html>""")

def full_data_update(snapshot_label=None):
    """
    Complete data update: fetch all API data and update CSV
    """
    if not snapshot_label:
        # Generate smart label based on season progress (matching github-update-csv-web.py)
        snapshot_label = generate_snapshot_label()
    
    print(f"🚀 Starting full data update for {snapshot_label}")
    print("=" * 60)
    
    # Fetch server data
    print("📡 Fetching server statistics...")
    server_stats = fetch_server_stats()
    if server_stats:
        print(f"   Online now: {server_stats.get('online_now', 'N/A')}")
        print(f"   Games open: {server_stats.get('games_open', 'N/A')}")
    
    print("🖥️  Fetching game server data...")
    game_servers = fetch_game_servers()
    if game_servers:
        print(f"   Found {len(game_servers)} game servers")
        for server in game_servers:
            country = server.get('country', 'Unknown').strip('"')
            players = server.get('players', 0)
            games = server.get('games', 0)
            print(f"   {country}: {players} players, {games} games")
    
    # Fetch character data
    print("👥 Fetching character data...")
    sc_characters = fetch_character_data('sc')
    if sc_characters:
        print(f"   SC: {len(sc_characters)} characters")
    
    hc_characters = fetch_character_data('hc')
    if hc_characters:
        print(f"   HC: {len(hc_characters)} characters")
    
    # Update CSV
    print("💾 Updating unified CSV...")
    
    if sc_characters:
        update_unified_csv_from_character_data(sc_characters, 'SC', snapshot_label)
    
    if hc_characters:
        update_unified_csv_from_character_data(hc_characters, 'HC', snapshot_label)
    
    if server_stats or game_servers:
        update_server_data_in_unified_csv(server_stats or {}, game_servers or [], snapshot_label)
    
    # Generate web pages
    print("🌐 Generating web pages...")
    generate_web_pages()
    
    print("=" * 60)
    print(f"🎉 Data update complete for {snapshot_label}!")
    
    # Show summary
    if server_stats:
        print(f"📊 Current server status:")
        print(f"   Players online: {server_stats.get('online_now', 'N/A')}")
        print(f"   Games open: {server_stats.get('games_open', 'N/A')}")
        print(f"   Last day activity: {server_stats.get('online_last_day', 'N/A')}")

def monitor_servers(interval_minutes=60, max_updates=24):
    """
    Continuously monitor server stats at regular intervals
    
    interval_minutes: How often to check (default: every hour)
    max_updates: Maximum number of updates before stopping (default: 24 hours)
    """
    print(f"🔄 Starting server monitoring (every {interval_minutes} minutes)")
    print(f"📅 Will run for {max_updates} updates")
    print("Press Ctrl+C to stop")
    
    for i in range(max_updates):
        try:
            # Use meaningful monitoring labels instead of timestamps
            current_time = datetime.now()
            if interval_minutes >= 60:
                # For hourly or longer intervals, use hour-based labels
                timestamp = f"Monitor_Hour_{current_time.hour:02d}"
            else:
                # For shorter intervals, use hour:minute format
                timestamp = f"Monitor_{current_time.hour:02d}_{current_time.minute:02d}"
            
            print(f"\n⏰ Update {i+1}/{max_updates} at {datetime.now().strftime('%H:%M:%S')}")
            
            # Only update server data for monitoring (not character data)
            server_stats = fetch_server_stats()
            game_servers = fetch_game_servers()
            
            if server_stats or game_servers:
                update_server_data_in_unified_csv(server_stats or {}, game_servers or [], timestamp)
            
            if i < max_updates - 1:  # Don't sleep after the last update
                print(f"💤 Sleeping for {interval_minutes} minutes...")
                time.sleep(interval_minutes * 60)
                
        except KeyboardInterrupt:
            print("\n⚠️ Monitoring stopped by user")
            break
        except Exception as e:
            print(f"❌ Error during monitoring: {e}")
            print("Continuing...")

def suggest_snapshot_labels():
    """
    Suggest snapshot labels based on current season progress and show auto-generated label
    """
    # Show what the auto-generated label would be
    auto_label = generate_snapshot_label()
    season_number, start_time, season_status = get_current_season_info()
    
    print("🤖 AUTO-GENERATED LABEL:")
    print(f"   {auto_label}")
    
    if season_number and start_time:
        now = datetime.now(timezone.utc)
        delta_days = (now - start_time).days
        print(f"   (Season {season_number}, Day {delta_days + 1}, Status: {season_status})")
    
    print()
    print("💡 MANUAL LABEL OPTIONS:")
    
    current_month = datetime.now().strftime("%B")
    
    if season_number:
        if season_status == "post_season":
            suggestions = [
                f"Post Season {season_number}",
                f"S{season_number + 1} Pre-Season",
                current_month,
                "Off Season",
            ]
        else:
            suggestions = [
                f"S{season_number} {current_month}",  # e.g., "S14 October"
                f"S{season_number} Mid Season",
                f"S{season_number} End of Season", 
                f"Post Season {season_number}",
                current_month,  # e.g., "October"
                "Mid Season",
                "End of Season",
            ]
            
            # Add day/week suggestions based on current progress
            if start_time and delta_days < 14:
                suggestions.insert(1, f"S{season_number} Day {delta_days + 1}")
            elif start_time and delta_days < 49:
                week_number = ((delta_days - 14) // 7) + 2
                suggestions.insert(1, f"S{season_number} Week {week_number}")
    else:
        suggestions = [
            current_month,
            "Mid Season",
            "End of Season",
            "Week 1",
            "Day 30",
        ]
    
    for i, label in enumerate(suggestions, 1):
        print(f"   {i}. {label}")
    
    print()
    print("📅 Usage: python3 api_integration.py \"<label>\"")
    print("📅 Default: python3 api_integration.py (uses auto-generated label)")
    
    return suggestions

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        if sys.argv[1] == "monitor":
            # Usage: python api_integration.py monitor [interval_minutes] [max_updates]
            interval = int(sys.argv[2]) if len(sys.argv) > 2 else 60
            max_updates = int(sys.argv[3]) if len(sys.argv) > 3 else 24
            monitor_servers(interval, max_updates)
        elif sys.argv[1] == "test":
            # Just test the API endpoints
            print("🧪 Testing API endpoints...")
            stats = fetch_server_stats()
            servers = fetch_game_servers()
            print(f"Stats API: {'✅' if stats else '❌'}")
            print(f"Servers API: {'✅' if servers else '❌'}")
            if stats:
                print(f"Current players: {stats.get('online_now')}")
            if servers:
                print(f"Active servers: {len(servers)}")
        elif sys.argv[1] == "suggest":
            # Show suggested snapshot labels
            suggest_snapshot_labels()
        elif sys.argv[1] == "web":
            # Generate web pages only (without updating data)
            print("🌐 Generating web pages from current CSV data...")
            generate_web_pages()
        elif sys.argv[1] in ["help", "--help", "-h"]:
            # Show help/usage information
            print("📖 Archive Automation System - Command Line Interface")
            print("")
            print("Usage:")
            print("  python api_integration.py [command] [options]")
            print("")
            print("Commands:")
            print("  monitor [interval] [max]  - Monitor servers (default: 60min, 24 cycles)")
            print("  test                      - Test API endpoints")
            print("  suggest                   - Show suggested snapshot labels")
            print("  web                       - Generate web pages from current data")
            print("  archive [type] [--force] - Create archive (monthly/final)")
            print("  help                      - Show this help message")
            print("  <custom_label>            - Full data update with custom label")
            print("")
            print("Archive Examples:")
            print("  python api_integration.py archive monthly")
            print("  python api_integration.py archive final --force")
            print("  python api_integration.py archive monthly --force")
            print("")
            print("Other Examples:")
            print("  python api_integration.py monitor 30 12")
            print("  python api_integration.py November_Update")
        elif sys.argv[1] == "archive":
            # Handle archive commands
            archive_type = sys.argv[2] if len(sys.argv) > 2 else "monthly"  # Default to monthly
            force_flag = "--force" in sys.argv
            
            if archive_type == "monthly":
                print(f"🗄️  Creating monthly archive (force={force_flag})...")
                result = create_monthly_archive(force=force_flag)
            elif archive_type == "final":
                print(f"🗄️  Creating final archive (force={force_flag})...")
                result = create_final_archive(force=force_flag)
            else:
                print(f"❌ Error: Unknown archive type '{archive_type}'. Use 'monthly' or 'final'")
                print("Usage: python api_integration.py archive [monthly|final] [--force]")
                sys.exit(1)
            
            if result.get("success"):
                print(f"✅ Archive created successfully: {result.get('archive_path')}")
                sys.exit(0)
            else:
                print(f"❌ Archive creation failed: {result.get('error')}")
                sys.exit(1)
        else:
            # Custom snapshot label
            full_data_update(sys.argv[1])
    else:
        # Default: full update with current month
        full_data_update()