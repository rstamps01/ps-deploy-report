---
name: Add Profiles to Pages
overview: Add Saved Profiles functionality (load, save, delete) to the Health Check and Advanced Operations pages, reusing the existing profile backend and matching the Generate page UX.
todos:
  - id: health-profiles
    content: Add Saved Profiles UI and JavaScript to Health Check page
    status: completed
  - id: advops-profiles
    content: Add Saved Profiles UI and JavaScript to Advanced Operations page
    status: completed
  - id: test-profiles
    content: Test profile loading/saving across all three pages
    status: completed
isProject: false
---

# Add Saved Profiles to Health Check and Advanced Operations Pages

## Current State

The Generate page has profile functionality:

- Dropdown to select saved profiles
- Save button (checkmark icon) to save current form
- Delete button (trash icon) to remove selected profile
- Backend: `/profiles` GET/POST, `/profiles/<name>` DELETE

## Changes Required

### 1. Health Check Page (`frontend/templates/health.html`)

Add profile controls to the connection settings section:

```html
<div class="form-group">
    <label for="profileSelect">Saved Profiles</label>
    <div class="profile-controls">
        <select id="profileSelect" onchange="loadProfile()">
            <option value="">-- Select a profile --</option>
        </select>
        <button type="button" class="btn-icon-save" onclick="saveProfile()" title="Save profile">...</button>
        <button type="button" class="btn-icon-delete" onclick="deleteProfile()" title="Delete profile">...</button>
    </div>
</div>
```

Add JavaScript functions:

- `fetchProfiles()` - Load profiles from API
- `loadProfile()` - Populate form from selected profile
- `saveProfile()` - Save current form as profile
- `deleteProfile()` - Delete selected profile

Profile fields for Health Check:

- `cluster_ip`, `username`, `password`
- `node_user`, `node_password` (for Tier 2)
- `switch_user`, `switch_password` (for Tier 3)

### 2. Advanced Operations Page (`frontend/templates/advanced_ops.html`)

Same profile controls added to the Connection Settings card.

Profile fields for Advanced Ops:

- `cluster_ip`, `username`, `password`
- `node_user`, `node_password`
- `switch_user`, `switch_password`

### 3. Shared Profile Fields

Both pages use the same credential fields, so profiles saved from any page will work on all three pages.

## Implementation

1. **Update Health Check template** - Add profile dropdown and JS functions
2. **Update Advanced Ops template** - Add profile dropdown and JS functions
3. **Test profile sharing** - Verify profiles saved from Generate work on Health/Advanced Ops

## Files to Modify

- `frontend/templates/health.html`
- `frontend/templates/advanced_ops.html`
