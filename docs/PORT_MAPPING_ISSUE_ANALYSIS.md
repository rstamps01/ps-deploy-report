# Port Mapping Section Missing - Issue Analysis

**Date:** November 5, 2025
**Cluster:** selab-var-204 (10.143.11.204)
**Report:** `output/vast_asbuilt_report_selab-var-204_20251105_141400.pdf`
**Issue:** Port Mapping section not appearing in PDF report, network topology diagram has no connections

---

## Executive Summary

The Port Mapping section is not appearing in the generated PDF report because:
1. **Port mapping collection failed** due to switch authentication issues
2. **Data extractor sets `available: False`** when external collection fails
3. **Report builder skips the section** if `available` is False
4. **Network diagram has no connections** because `port_map` is empty

---

## 1. Current Workflow

### 1.1 Port Mapping Collection Flow

```
main.py (_collect_data)
  └─> _collect_port_mapping() [if --enable-port-mapping]
      └─> ExternalPortMapper.collect_port_mapping()
          └─> _detect_switch_os() [checks Cumulus/Onyx]
              └─> ❌ FAILED: Authentication failed with both credential sets
          └─> raw_data["port_mapping_external"] = None (or error dict)
```

### 1.2 Data Extraction Flow

```
main.py (_process_data)
  └─> data_extractor.extract_all_data(use_external_port_mapping=True)
      └─> extract_port_mapping(raw_data, use_external=True)
          └─> Check: if use_external and "port_mapping_external" in raw_data
              └─> ❌ If False: return ReportSection with available=False
              └─> ✅ If True: process external data, return with available=True
```

### 1.3 Report Generation Flow

```
main.py (_generate_report)
  └─> report_builder.build_report()
      └─> _create_hardware_inventory()
          └─> _create_network_diagram_section()
              └─> NetworkDiagramGenerator.generate_network_diagram()
                  └─> Uses port_mapping_data.get("port_map", [])
                      └─> ❌ Empty list = no connections drawn
          └─> (line 3369-3378) Check port_mapping_data.get("available")
              └─> ❌ If False: skip port mapping section
              └─> ✅ If True: add _create_port_mapping_section()
```

---

## 2. Root Cause Analysis

### 2.1 Primary Issue: Switch Authentication Failure

**Error from logs:**
```
ERROR - Error collecting port mapping: Could not detect OS type for switch 10.143.11.153 - authentication failed with both credential sets
```

**Location:** `src/external_port_mapper.py` - `_detect_switch_os()`

**What happened:**
1. Code tried to authenticate with Cumulus credentials (`cumulus` / `Vasdata1!`)
2. Authentication failed
3. Code tried to authenticate with Onyx credentials (same credentials)
4. Authentication failed
5. Exception raised: "Could not detect OS type"

**Root cause:**
- **Incorrect switch credentials** or **switch not accessible**
- Switch at 10.143.11.153 requires different credentials
- Switch may be using different authentication method

### 2.2 Secondary Issue: Error Handling

**Current behavior:**
- When port mapping collection fails, `main.py` logs a warning and continues
- `raw_data["port_mapping_external"]` may not be set, or contains error dict
- `data_extractor.extract_port_mapping()` returns `available: False`
- Report builder skips the section entirely

**Problem:**
- No indication in the report that port mapping was attempted but failed
- Network diagram shows devices but no connections (confusing)
- User doesn't know why the section is missing

---

## 3. Code Locations

### 3.1 Port Mapping Collection

**File:** `src/main.py`
- **Line 343-345:** Collects port mapping if enabled
- **Line 358-429:** `_collect_port_mapping()` method

**File:** `src/external_port_mapper.py`
- **Line 362:** `_detect_switch_os()` - where authentication fails
- **Line 509:** `collect_port_mapping()` - main collection method

### 3.2 Data Extraction

**File:** `src/data_extractor.py`
- **Line 1743-1983:** `extract_port_mapping()` method
- **Line 1770-1772:** Checks for external port mapping data
- **Line 1808-1817:** Returns `available: False` if no data
- **Line 1972-1983:** Exception handler returns `available: False`

### 3.3 Report Generation

**File:** `src/report_builder.py`
- **Line 2505-2568:** `_create_network_diagram_section()` - generates network diagram
- **Line 2563:** Passes `port_mapping_data` to diagram generator
- **Line 3369-3378:** Checks `port_mapping_data.get("available")` before adding section
- **Line 2814-3048:** `_create_port_mapping_section()` - creates port mapping tables

**File:** `src/network_diagram.py`
- **Line 254-271:** Uses `port_map` from `port_mapping_data` to draw connections
- **Line 267:** Filters to show only `f0` and `f1` interfaces

---

## 4. Required Fixes

### 4.1 Immediate Fix: Improve Error Handling and User Feedback

#### 4.1.1 Add Port Mapping Status Section

**Problem:** When port mapping fails, report doesn't indicate why section is missing.

**Solution:** Always show port mapping section, but display status message if unavailable.

**Changes needed in `src/report_builder.py`:**

```python
# Current code (line 3369-3378):
if port_mapping_data.get("available"):
    content.append(PageBreak())
    port_mapping_content = self._create_port_mapping_section(
        port_mapping_data, switches
    )
    content.extend(port_mapping_content)

# Proposed change:
# Always add port mapping section, but show status if unavailable
content.append(PageBreak())
if port_mapping_data.get("available"):
    port_mapping_content = self._create_port_mapping_section(
        port_mapping_data, switches
    )
    content.extend(port_mapping_content)
else:
    # Show status message explaining why port mapping is unavailable
    status_content = self._create_port_mapping_status_section(
        port_mapping_data
    )
    content.extend(status_content)
```

**New method needed in `src/report_builder.py`:**

```python
def _create_port_mapping_status_section(
    self, port_mapping_data: Dict[str, Any]
) -> List[Any]:
    """Create port mapping status section when data is unavailable."""
    content = []
    styles = getSampleStyleSheet()

    # Add section heading
    heading_elements = self.brand_compliance.create_vast_section_heading(
        "Port Mapping", level=1
    )
    content.extend(heading_elements)

    # Status message
    message = port_mapping_data.get(
        "message",
        "Port mapping data is not available."
    )
    error = port_mapping_data.get("error")

    status_style = ParagraphStyle(
        "Status_Message",
        parent=styles["Normal"],
        fontSize=self.config.font_size,
        textColor=self.brand_compliance.colors.BACKGROUND_DARK,
        spaceAfter=12,
    )

    content.append(Paragraph(message, status_style))

    if error:
        error_style = ParagraphStyle(
            "Error_Message",
            parent=styles["Normal"],
            fontSize=self.config.font_size - 1,
            textColor=colors.HexColor("#dc2626"),  # Red
            spaceAfter=12,
        )
        content.append(Paragraph(f"Error: {error}", error_style))

    # Add troubleshooting information
    troubleshooting = """
    <b>Troubleshooting:</b><br/>
    • Verify switch credentials are correct<br/>
    • Ensure switches are accessible via SSH<br/>
    • Check that --enable-port-mapping flag is used<br/>
    • Verify --switch-user and --switch-password arguments<br/>
    • Review logs for detailed error messages
    """

    troubleshooting_style = ParagraphStyle(
        "Troubleshooting",
        parent=styles["Normal"],
        fontSize=self.config.font_size - 1,
        textColor=self.brand_compliance.colors.BACKGROUND_DARK,
        spaceAfter=12,
        leftIndent=12,
    )

    content.append(Paragraph(troubleshooting, troubleshooting_style))

    return content
```

#### 4.1.2 Improve Network Diagram When Port Mapping Unavailable

**Problem:** Network diagram shows devices but no connections, which is confusing.

**Solution:** Add a message or visual indicator when connections are missing.

**Changes needed in `src/network_diagram.py`:**

```python
# In generate_network_diagram() method, after drawing devices:
port_map = port_mapping_data.get("port_map", [])

if not port_map:
    # Add text indicating no connections available
    from reportlab.lib import colors
    from reportlab.lib.styles import getSampleStyleSheet

    # Draw message in center of diagram
    c.setFillColor(colors.HexColor("#666666"))
    c.setFont("Helvetica", 10)
    message = "Port mapping data not available - connections cannot be displayed"
    text_width = c.stringWidth(message, "Helvetica", 10)
    x_center = drawing_size[0] / 2 - text_width / 2
    y_center = drawing_size[1] / 2
    c.drawString(x_center, y_center, message)
```

---

### 4.2 Fix Switch Authentication

#### 4.2.1 Enhanced Switch Credential Detection

**Problem:** Code assumes all switches use same credentials, fails if authentication fails.

**Solution:** Add more robust credential handling and better error messages.

**Changes needed in `src/external_port_mapper.py`:**

```python
def _detect_switch_os(
    self, switch_ip: str
) -> Tuple[str, str, str]:
    """
    Detect switch OS type and return OS type, username, password.

    Enhanced version with better error handling and credential options.
    """
    # Try Cumulus first
    try:
        if self._test_switch_connection(
            switch_ip, self.switch_user, self.switch_password, "cumulus"
        ):
            return "cumulus", self.switch_user, self.switch_password
    except Exception as e:
        self.logger.debug(f"Cumulus authentication failed for {switch_ip}: {e}")

    # Try Onyx
    try:
        if self._test_switch_connection(
            switch_ip, self.switch_user, self.switch_password, "onyx"
        ):
            return "onyx", self.switch_user, self.switch_password
    except Exception as e:
        self.logger.debug(f"Onyx authentication failed for {switch_ip}: {e}")

    # Try alternative credentials if provided
    # (Could add config file support for per-switch credentials)

    # Enhanced error message
    error_msg = (
        f"Could not detect OS type for switch {switch_ip} - "
        f"authentication failed with credentials (user: {self.switch_user}). "
        f"Please verify:\n"
        f"  1. Switch is accessible at {switch_ip}\n"
        f"  2. SSH credentials are correct\n"
        f"  3. Switch supports Cumulus or Onyx OS\n"
        f"  4. SSH service is running on switch"
    )

    raise Exception(error_msg)
```

#### 4.2.2 Add Per-Switch Credential Support

**Enhancement:** Allow different credentials for different switches.

**Configuration file example:**
```yaml
switch_credentials:
  - ip: "10.143.11.153"
    username: "cumulus"
    password: "Vasdata1!"
    os_type: "cumulus"
  - ip: "10.143.11.154"
    username: "admin"
    password: "different_password"
    os_type: "onyx"
```

---

### 4.3 Add Diagnostic Information

#### 4.3.1 Enhanced Logging

**Problem:** When port mapping fails, logs don't provide enough detail for troubleshooting.

**Solution:** Add comprehensive diagnostic logging.

**Changes needed in `src/external_port_mapper.py`:**

```python
def collect_port_mapping(self) -> Dict[str, Any]:
    """Collect port mapping with enhanced diagnostics."""
    diagnostic_info = {
        "collection_started": datetime.now().isoformat(),
        "switches_attempted": [],
        "switches_successful": [],
        "switches_failed": [],
        "errors": [],
    }

    try:
        # ... existing collection code ...

        # Log diagnostic summary
        self.logger.info("Port mapping collection diagnostic summary:")
        self.logger.info(f"  Switches attempted: {len(diagnostic_info['switches_attempted'])}")
        self.logger.info(f"  Switches successful: {len(diagnostic_info['switches_successful'])}")
        self.logger.info(f"  Switches failed: {len(diagnostic_info['switches_failed'])}")

        if diagnostic_info['errors']:
            self.logger.warning("Errors encountered:")
            for error in diagnostic_info['errors']:
                self.logger.warning(f"  - {error}")

        # Include diagnostic info in return value
        result["diagnostic_summary"] = diagnostic_info

    except Exception as e:
        diagnostic_info["collection_failed"] = str(e)
        result["diagnostic_summary"] = diagnostic_info
        raise
```

---

## 5. Implementation Checklist

### Phase 1: Immediate Fixes (Error Handling)
- [ ] Add `_create_port_mapping_status_section()` method to `report_builder.py`
- [ ] Modify port mapping section check to always show section
- [ ] Add status message when port mapping is unavailable
- [ ] Add troubleshooting information to status section
- [ ] Update network diagram to show message when no connections
- [ ] Test with failed port mapping collection

### Phase 2: Switch Authentication Improvements
- [ ] Enhance `_detect_switch_os()` with better error messages
- [ ] Add per-switch credential support (config file)
- [ ] Add credential validation before attempting connection
- [ ] Add retry logic with exponential backoff
- [ ] Test with various switch configurations

### Phase 3: Diagnostics and Monitoring
- [ ] Add comprehensive diagnostic logging
- [ ] Include diagnostic summary in port mapping data
- [ ] Display diagnostic information in report status section
- [ ] Add verbose logging for switch authentication attempts
- [ ] Create diagnostic report file

### Phase 4: User Experience
- [ ] Add clear error messages in report
- [ ] Add troubleshooting guide section
- [ ] Provide example credentials format
- [ ] Add validation for required credentials
- [ ] Update documentation with troubleshooting steps

---

## 6. Testing Plan

### 6.1 Test Scenarios

1. **Port mapping successful:**
   - Verify section appears in report
   - Verify network diagram has connections
   - Verify port mapping tables are populated

2. **Port mapping failed (authentication):**
   - Verify status section appears
   - Verify error message is displayed
   - Verify troubleshooting information is shown
   - Verify network diagram shows message

3. **Port mapping partially successful:**
   - Some switches succeed, some fail
   - Verify partial data is shown
   - Verify failed switches are noted

4. **Port mapping disabled:**
   - Verify section doesn't appear (or shows "disabled" message)
   - Verify network diagram shows message

### 6.2 Test Cluster

**Cluster:** 10.143.11.204 (selab-var-204)
- **Switches:** 10.143.11.153, 10.143.11.154
- **Issue:** Authentication failing with provided credentials
- **Action:** Obtain correct credentials or test with working cluster

---

## 7. Root Cause Summary

| Issue | Root Cause | Impact | Priority |
|-------|------------|--------|----------|
| Port mapping section missing | Collection failed → `available=False` → section skipped | Section not shown | High |
| Network diagram has no connections | Empty `port_map` list | No connections drawn | High |
| No error indication in report | Error handling skips section entirely | User doesn't know why | Medium |
| Switch authentication failure | Incorrect credentials or switch not accessible | Collection fails | High |
| Poor error messages | Generic error messages | Hard to troubleshoot | Medium |

---

## 8. Recommended Actions

### Immediate (High Priority):
1. **Fix error handling** - Always show port mapping section with status
2. **Add diagnostic information** - Show why collection failed
3. **Verify switch credentials** - Test with correct credentials

### Short-term (Medium Priority):
1. **Improve switch authentication** - Add per-switch credential support
2. **Enhance error messages** - Provide actionable troubleshooting steps
3. **Add retry logic** - Handle transient network issues

### Long-term (Low Priority):
1. **Add configuration file support** - Per-switch credentials
2. **Add credential validation** - Check before attempting connection
3. **Create diagnostic report** - Separate file with detailed diagnostics

---

**Document Version:** 1.0
**Last Updated:** November 5, 2025
**Status:** Ready for implementation


