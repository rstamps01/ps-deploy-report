---
name: Fix UI Consistency
overview: "Fix three UI issues in the Advanced Operations Connection Settings: revert dropdown to standard icon-button style matching Generate/Health pages, replace Default Credentials checkbox with a toggle-switch slider, relocate the toggle under the Add button, and make Add toggle the credential section open/close (instead of Save)."
todos:
  - id: revert-dropdown
    content: Replace profile-bar text-button layout with standard form-group + label + profile-controls + icon buttons (save/add/delete)
    status: completed
  - id: toggle-switch
    content: Replace checkbox with toggle-switch slider (toggle-switch + toggle-slider classes) and relocate under Add button
    status: completed
  - id: add-toggle-behavior
    content: Change addProfile() to toggle open/close and remove collapseCredentials from saveProfile
    status: completed
  - id: cleanup-css
    content: Remove unused .profile-bar, .toggle-label, .btn-success CSS rules from the style block
    status: completed
isProject: false
---

# Fix Advanced Ops UI Consistency

## Changes (all in `advanced_ops.html`)

### 1. Revert Saved Profiles dropdown to standard style

Replace the current profile-bar (text buttons: Save/Add/Delete) with the standard `form-group` + `label` + `profile-controls` pattern used in Generate and Health pages. Use icon buttons (`btn-icon-save`, `btn-icon-add`, `btn-icon-delete`) already defined in [`frontend/static/css/app.css`](frontend/static/css/app.css) lines 193-239.

Current (non-standard):

```html
<div class="profile-controls">
    <select id="profileSelect" ... class="form-control">
    <button class="btn btn-sm btn-secondary">Save</button>
    <button class="btn btn-sm btn-success">Add</button>
    <button class="btn btn-sm btn-danger">Delete</button>
</div>
```

Target (matching Generate/Health):

```html
<div class="form-group" style="margin-bottom: 12px;">
    <label for="profileSelect">Saved Profiles</label>
    <div class="profile-controls">
        <select id="profileSelect" onchange="loadProfile()">...</select>
        <button class="btn-icon-save" onclick="saveProfile()">checkmark SVG</button>
        <button class="btn-icon-add" onclick="addProfile()">plus SVG</button>
        <button class="btn-icon-delete" onclick="deleteProfile()">trash SVG</button>
    </div>
</div>
```

### 2. Replace Default Credentials checkbox with toggle-switch slider

Replace the `<label class="toggle-label"><input type="checkbox">` with the standard toggle-switch pattern from Generate Report, using existing CSS classes (`toggle-switch`, `toggle-slider`, `toggle-label-text`) defined in [`frontend/static/css/app.css`](frontend/static/css/app.css) lines 364-401.

```html
<div class="default-creds-toggle">
    <div class="toggle-control">
        <label class="toggle-switch">
            <input type="checkbox" id="useDefaultCreds" checked onchange="toggleDefaultCredentials()">
            <span class="toggle-slider"></span>
        </label>
        <span class="toggle-label-text">Default Credentials</span>
    </div>
</div>
```

### 3. Relocate toggle under the Add button

Place the `default-creds-toggle` div directly after the Add button in the profile-controls row (or immediately below the button cluster), visually aligned beneath the Add icon.

### 4. Add button toggles credential section open/close

Modify `addProfile()` JS function: instead of always expanding, it should toggle. If section is collapsed, expand it and clear fields; if already expanded, collapse it.

```js
function addProfile() {
    if (isCredentialsExpanded()) {
        collapseCredentials();
    } else {
        document.getElementById('profileSelect').value = '';
        document.getElementById('clusterIp').value = '';
        toggleDefaultCredentials();
        document.getElementById('vipPool').value = 'main';
        expandCredentials();
    }
}
```

Remove `collapseCredentials()` call from `saveProfile()` since Save no longer collapses.

### 5. Remove unused CSS

Remove the custom `.profile-bar`, `.toggle-label`, and `.btn-success` styles that were added in the previous edit since they are no longer needed.
