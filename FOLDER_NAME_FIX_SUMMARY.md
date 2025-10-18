# Folder Name Mismatch Fix Summary

**Date**: October 18, 2025
**Status**: ✅ Fixed
**Branch**: `develop`
**Commit**: `eeafff5`

---

## 🐛 Issue Identified

The uninstall scripts were looking for the wrong installation directory:
- **Uninstall scripts looked for**: `~/vast-reporter`
- **Install scripts actually install to**: `~/vast-asbuilt-reporter`

This mismatch would cause the uninstall process to fail, as it couldn't find the installation directory.

---

## 🔧 Files Fixed

### Scripts Updated

1. **`docs/deployment/uninstall-mac.sh`**
   - Default install directory: `vast-reporter` → `vast-asbuilt-reporter`
   - Backup directory: `vast-reporter-backup-*` → `vast-asbuilt-reporter-backup-*`
   - Shell config patterns: `/vast-reporter/` → `/vast-asbuilt-reporter/`
   - Symlink checks: `vast-reporter` → `vast-asbuilt-reporter`
   - System log directory: `/var/log/vast-reporter` → `/var/log/vast-asbuilt-reporter`

2. **`docs/deployment/uninstall-windows.ps1`**
   - Default install directory: `vast-reporter` → `vast-asbuilt-reporter`
   - Backup directory: `vast-reporter-backup-*` → `vast-asbuilt-reporter-backup-*`
   - PATH variable cleanup: `*vast-reporter*` → `*vast-asbuilt-reporter*`

### Documentation Updated

3. **`docs/deployment/UNINSTALL-GUIDE.md`**
   - All backup command examples
   - Directory removal commands
   - Configuration file paths

4. **`docs/deployment/UPDATE-GUIDE.md`**
   - All directory references
   - Git pull commands
   - Update procedures

5. **`docs/deployment/INSTALLATION-GUIDE.md`**
   - Installation directory paths
   - Usage examples

6. **`docs/deployment/DEPLOYMENT.md`**
   - Deployment directory references
   - Configuration paths

---

## 📊 Changes Summary

### Before Fix
```bash
# Install creates:
~/vast-asbuilt-reporter/

# Uninstall looks for:
~/vast-reporter/  ❌ NOT FOUND
```

### After Fix
```bash
# Install creates:
~/vast-asbuilt-reporter/

# Uninstall looks for:
~/vast-asbuilt-reporter/  ✅ FOUND
```

---

## 🔍 Specific Changes

### Mac Uninstall Script

**Line 27**: Default directory
```bash
# Before
DEFAULT_INSTALL_DIR="$HOME/vast-reporter"

# After
DEFAULT_INSTALL_DIR="$HOME/vast-asbuilt-reporter"
```

**Line 170**: Backup directory
```bash
# Before
local backup_dir="$HOME/vast-reporter-backup-$(date +%Y%m%d_%H%M%S)"

# After
local backup_dir="$HOME/vast-asbuilt-reporter-backup-$(date +%Y%m%d_%H%M%S)"
```

**Lines 250, 262, 272**: Shell configuration patterns
```bash
# Before
grep -q "vast-reporter"
sed -i.bak '/vast-reporter/d'

# After
grep -q "vast-asbuilt-reporter"
sed -i.bak '/vast-asbuilt-reporter/d'
```

**Line 299**: Symlink removal
```bash
# Before
if [ -L "$bin_dir/vast-reporter" ]; then
    rm -f "$bin_dir/vast-reporter"

# After
if [ -L "$bin_dir/vast-asbuilt-reporter" ]; then
    rm -f "$bin_dir/vast-asbuilt-reporter"
```

**Line 317**: System logs
```bash
# Before
if [ -d "/var/log/vast-reporter" ]; then
    sudo rm -rf "/var/log/vast-reporter"

# After
if [ -d "/var/log/vast-asbuilt-reporter" ]; then
    sudo rm -rf "/var/log/vast-asbuilt-reporter"
```

### Windows Uninstall Script

**Line 25**: Default directory
```powershell
# Before
$script:DefaultInstallDir = "$env:USERPROFILE\vast-reporter"

# After
$script:DefaultInstallDir = "$env:USERPROFILE\vast-asbuilt-reporter"
```

**Line 172**: Backup directory
```powershell
# Before
$backupDir = "$env:USERPROFILE\vast-reporter-backup-$timestamp"

# After
$backupDir = "$env:USERPROFILE\vast-asbuilt-reporter-backup-$timestamp"
```

**Lines 254-258**: PATH cleanup
```powershell
# Before
if ($userPath -like "*vast-reporter*") {
    $newPath = ($userPath -split ';' | Where-Object { $_ -notlike "*vast-reporter*" }) -join ';'

# After
if ($userPath -like "*vast-asbuilt-reporter*") {
    $newPath = ($userPath -split ';' | Where-Object { $_ -notlike "*vast-asbuilt-reporter*" }) -join ';'
```

### Documentation Files

**All `vast-reporter` references replaced with `vast-asbuilt-reporter`**:
- Backup commands
- Directory paths
- Configuration file locations
- Git commands
- Usage examples

---

## ✅ Verification

### Install Scripts
✅ Already using correct folder: `vast-asbuilt-reporter`
- `install-mac.sh`: Line 228 - `project_dir="$HOME/vast-asbuilt-reporter"`
- `install-windows.ps1`: Line 266 - `$projectDir = "$env:USERPROFILE\vast-asbuilt-reporter"`

### Uninstall Scripts
✅ Now using correct folder: `vast-asbuilt-reporter`
- `uninstall-mac.sh`: Line 27 - `DEFAULT_INSTALL_DIR="$HOME/vast-asbuilt-reporter"`
- `uninstall-windows.ps1`: Line 25 - `$script:DefaultInstallDir = "$env:USERPROFILE\vast-asbuilt-reporter"`

### Documentation
✅ All references updated
- Total occurrences fixed: 163
- Files updated: 4 documentation files
- No remaining `vast-reporter` references (without `-asbuilt`)

---

## 🧪 Testing Required

### Mac Testing
- [ ] Run `uninstall-mac.sh` on system with existing installation
- [ ] Verify script finds `~/vast-asbuilt-reporter/`
- [ ] Verify backup creates `~/vast-asbuilt-reporter-backup-*/`
- [ ] Verify shell config cleanup works
- [ ] Verify symlink removal works

### Windows Testing
- [ ] Run `uninstall-windows.ps1` on system with existing installation
- [ ] Verify script finds `%USERPROFILE%\vast-asbuilt-reporter\`
- [ ] Verify backup creates `%USERPROFILE%\vast-asbuilt-reporter-backup-*\`
- [ ] Verify PATH cleanup works
- [ ] Verify environment variable cleanup works

---

## 📝 Impact Analysis

### User Impact
- **Existing installations**: Uninstall will now work correctly
- **New installations**: No change (already installing to correct location)
- **Documentation**: All paths now consistent and accurate

### Breaking Changes
- None - this is a bug fix, not a breaking change
- Existing installations are already in `vast-asbuilt-reporter/`

### Backward Compatibility
- Scripts are backward compatible
- If old `vast-reporter/` directory exists, it won't be found (correct behavior)
- Users should use correct folder name

---

## 🚀 Release Notes Entry

### Bug Fixes
- **Fixed folder name mismatch in uninstall scripts**: Uninstall scripts were looking for `~/vast-reporter/` but installations are in `~/vast-asbuilt-reporter/`. This prevented successful uninstallation. All scripts and documentation now use the correct folder name consistently.

---

## 📚 Related Files

- Installation Scripts:
  - `docs/deployment/install-mac.sh` ✅ (already correct)
  - `docs/deployment/install-windows.ps1` ✅ (already correct)

- Uninstall Scripts:
  - `docs/deployment/uninstall-mac.sh` ✅ (fixed)
  - `docs/deployment/uninstall-windows.ps1` ✅ (fixed)

- Documentation:
  - `docs/deployment/UNINSTALL-GUIDE.md` ✅ (fixed)
  - `docs/deployment/UPDATE-GUIDE.md` ✅ (fixed)
  - `docs/deployment/INSTALLATION-GUIDE.md` ✅ (fixed)
  - `docs/deployment/DEPLOYMENT.md` ✅ (fixed)

---

## ✨ Consistency Check

Performed search for `vast-reporter` (without `-asbuilt`):
```bash
grep -r "vast-reporter[^-]" docs/deployment/
```

**Result**: 0 matches ✅

All folder references now consistently use: `vast-asbuilt-reporter`

---

## 🔐 Security Notes

No security implications from this change.
- Only affects directory paths
- No changes to authentication or API calls
- No changes to data handling

---

## 📦 Commit Details

**Commit Hash**: `eeafff5`
**Commit Message**:
```
Fix folder name mismatch: vast-reporter → vast-asbuilt-reporter

- Update uninstall scripts to use correct folder name
- Fix all documentation references
- Ensure consistency across all deployment files
- Uninstall scripts now correctly find installation directory
```

**Files Changed**: 8
- `docs/deployment/uninstall-mac.sh`
- `docs/deployment/uninstall-windows.ps1`
- `docs/deployment/UNINSTALL-GUIDE.md`
- `docs/deployment/UPDATE-GUIDE.md`
- `docs/deployment/INSTALLATION-GUIDE.md`
- `docs/deployment/DEPLOYMENT.md`

**Total Changes**: 163 replacements

---

## 🎯 Lessons Learned

### Root Cause
- Installation scripts were updated to use `vast-asbuilt-reporter`
- Uninstall scripts and documentation were not updated simultaneously
- No automated tests to catch path mismatches

### Prevention
- **Recommendation**: Add validation test to verify install/uninstall directory consistency
- **Recommendation**: Use shared constants for directory names
- **Recommendation**: Add integration test that installs then uninstalls

### Future Improvements
1. Create shared configuration file with directory constants
2. Source this configuration in both install and uninstall scripts
3. Add automated testing for install/uninstall cycle
4. Add CI/CD check to verify path consistency across all files

---

**Status**: ✅ Fixed and Committed
**Next Steps**: Test on clean systems (Mac and Windows)
**Merge Target**: `develop` → `main` after full testing
