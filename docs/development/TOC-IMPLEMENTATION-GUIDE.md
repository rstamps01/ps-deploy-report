# Table of Contents Implementation Guide

## Overview

This document describes the two Table of Contents (TOC) implementations in the VAST As-Built Report Generator:

1. **Static TOC** (Current Production) - `_create_table_of_contents_static()`
2. **Dynamic TOC** (Under Development) - `_create_table_of_contents()`

---

## Current Implementation: Static TOC

### Method
`_create_table_of_contents_static(data: Dict[str, Any]) -> List[Any]`

### Location
`src/report_builder.py` (lines 637-855)

### Description
The static TOC uses **hardcoded page numbers** that are manually maintained. This implementation provides:

- ✅ Precise formatting control
- ✅ Custom dot leaders with exact positioning
- ✅ VAST brand compliance
- ✅ Custom spacing between sections
- ❌ Manual page number updates required
- ❌ Doesn't adapt to dynamic content changes

### Page Number Structure
```python
toc_structure = [
    ("Executive Summary", 0, "3", True),      # Page 3
    ("Cluster Information", 0, "4", True),    # Page 4
    ("Hardware Summary", 0, "5", True),       # Page 5
    ("Physical Rack Layout", 0, "6", True),   # Page 6
    ("Network Configuration", 0, "7", True),  # Page 7
    ("Switch Configuration", 0, "8", True),   # Page 8
    ("Port Mapping", 0, "10", True),          # Page 10
    ("Logical Network Diagram", 0, "11", True), # Page 11
    ("Logical Configuration", 0, "12", True), # Page 12
    ("Security & Authentication", 0, "13", True), # Page 13
]
```

### Features
- **Two-column layout**: Text with dot leaders | Page number
- **Custom dot leader lengths**: Individually tuned per section
- **Variable spacing**: Extra spacing after specific subsections
- **Bold main sections**: Hierarchical visual structure
- **Perfect alignment**: Page numbers right-aligned at 0.15" from edge

### When to Update
Manually update page numbers when:
- Adding new sections
- Removing sections
- Content grows and pushes sections to new pages
- Optional sections appear (e.g., Port Mapping)

---

## Development Implementation: Dynamic TOC

### Method
`_create_table_of_contents(data: Dict[str, Any]) -> List[Any]`

### Location
`src/report_builder.py` (lines 857-920)

### Status
🚧 **Under Development** - Currently calls static version as fallback

### Description
The dynamic TOC will use **ReportLab's TableOfContents class** for automatic page number tracking:

- ✅ Automatic page number updates
- ✅ Handles dynamic content (optional sections)
- ✅ Two-pass PDF generation (collect pages, then render TOC)
- ⚠️ Requires adding `toc.notifyEntry()` after each section heading
- ⚠️ May need custom formatting for dot leaders

### Implementation Plan

#### Phase 1: Basic Dynamic TOC
1. Uncomment TOC implementation in `_create_table_of_contents()`
2. Add `toc.notifyEntry()` calls after each section heading
3. Test with various cluster configurations
4. Validate page numbers are correct

#### Phase 2: Custom Formatting
1. Subclass `TableOfContents` to create `VASTTableOfContents`
2. Override `drawOn()` method for custom dot leaders
3. Implement VAST-branded spacing and alignment
4. Match current static TOC appearance

#### Phase 3: Testing & Validation
1. Test with clusters of different sizes
2. Verify with/without optional sections (Port Mapping)
3. Test with 1-switch vs 2-switch configurations
4. Validate against static TOC output

#### Phase 4: Production Release
1. Update main `_create_table_of_contents()` to use dynamic version
2. Keep `_create_table_of_contents_static()` as backup
3. Update documentation
4. Create rollback plan if issues arise

---

## Usage Examples

### Using Static TOC (Current)
```python
# In _build_report_story()
if self.config.include_toc:
    story.extend(self._create_table_of_contents(processed_data))
    story.append(PageBreak())
```

This automatically calls `_create_table_of_contents_static()` as the fallback.

### Switching to Dynamic TOC (Future)
```python
# Step 1: Uncomment implementation in _create_table_of_contents()
# Step 2: Add TOC entry notifications after each section

def _create_executive_summary(self, data: Dict[str, Any]) -> List[Any]:
    content = []

    # Add section heading
    heading_elements = self.brand_compliance.create_vast_section_heading(
        "Executive Summary", level=1
    )
    content.extend(heading_elements)

    # NEW: Register with TOC
    if hasattr(self, '_toc'):
        content.append(self._toc.addEntry(
            level=0,
            text='Executive Summary',
            key='exec_summary'
        ))

    # ... rest of section content
    return content
```

---

## Technical Details

### Static TOC Formatting

**Column Widths:**
- Text + Dot Leaders: 7.35" (available_width - 0.15")
- Page Numbers: 0.15"

**Dot Leader Calculation:**
```python
dot_leader_length = 5.0 * inch  # Custom per section
dot_width = stringWidth(".", "Helvetica", text_size - 1)
num_dots = int(dot_leader_length / dot_width)
dots = '<font color="#CCCCCC">' + ("." * num_dots) + "</font>"
```

**Custom Dot Leader Lengths:**
- Executive Summary: 5.0"
- Physical Rack Layout: 4.92"
- Network Configuration: 4.87"
- Switch Configuration: 4.95"
- Port Mapping: 5.4"
- Logical Network Diagram: 4.78"
- Logical Configuration: 4.95"

**Spacing Rules:**
- Main sections: 12pt spaceBefore (except first)
- Subsections: 0.5pt spaceAfter
- Group separators: 8pt spaceAfter (after specific subsections)

### Dynamic TOC Architecture

**ReportLab's Two-Pass System:**
1. **First Pass**: Build document, collect TOC entries with page numbers
2. **Second Pass**: Rebuild TOC with actual page numbers, finalize PDF

**Entry Registration:**
```python
# During document build, each section registers:
toc.addEntry(
    level=0,           # 0 = main section, 1 = subsection
    text='Section Title',
    key='unique_key'   # For internal tracking
)
```

**Page Number Collection:**
- ReportLab automatically tracks which page each entry appears on
- No manual page number management needed
- Works with dynamic content (optional sections, variable length content)

---

## Migration Checklist

When migrating from static to dynamic TOC:

- [ ] Uncomment dynamic implementation in `_create_table_of_contents()`
- [ ] Add `self._toc = None` to `__init__()` method
- [ ] Add `toc.addEntry()` calls to these methods:
  - [ ] `_create_executive_summary()`
  - [ ] `_create_cluster_information()`
  - [ ] `_create_hardware_inventory()`
  - [ ] `_create_comprehensive_network_configuration()`
  - [ ] `_create_switch_configuration()`
  - [ ] `_create_port_mapping_section()` (if available)
  - [ ] `_create_logical_network_diagram()`
  - [ ] `_create_logical_configuration()`
  - [ ] `_create_security_configuration()`
- [ ] Test with multiple cluster configurations
- [ ] Validate page numbers match actual content
- [ ] Compare formatting with static TOC
- [ ] Update user documentation

---

## Rollback Plan

If dynamic TOC causes issues:

1. **Immediate Fix**:
   ```python
   def _create_table_of_contents(self, data: Dict[str, Any]) -> List[Any]:
       # Rollback to static
       return self._create_table_of_contents_static(data)
   ```

2. **Remove TOC Entry Calls**:
   - Comment out all `toc.addEntry()` calls
   - Or add conditional: `if hasattr(self, '_toc') and self._toc:`

3. **Testing**:
   - Generate test reports
   - Verify static TOC works as before

---

## Benefits of Dynamic TOC

### Production Benefits
- ✅ Automatic adaptation to content changes
- ✅ Handles optional sections (Port Mapping, etc.)
- ✅ Works with multi-switch configurations
- ✅ No manual page number maintenance
- ✅ Reduces development time for new sections

### Development Benefits
- ✅ Easier to add new report sections
- ✅ Less error-prone (no manual page tracking)
- ✅ Better scalability for future enhancements
- ✅ Standard ReportLab approach (better support)

---

## Current Status

**Production**: Static TOC (`_create_table_of_contents_static()`)
**Development**: Dynamic TOC skeleton created, ready for implementation
**Next Step**: Implement and test dynamic TOC with TOC entry notifications

---

## References

- [ReportLab User Guide - Table of Contents](https://www.reportlab.com/docs/reportlab-userguide.pdf)
- `src/report_builder.py` - Implementation location
- `docs/development/` - Development documentation directory

---

## UPDATE: Dynamic TOC Now Production Ready!

**Date:** October 22, 2025
**Status:** ✅ Dynamic TOC Implemented and Deployed

The dynamic TOC using custom two-pass generation is now **production ready** and active!

### New Implementation

See **DYNAMIC-TOC-IMPLEMENTATION.md** for complete details on the production dynamic TOC system.

**Key Features:**
- ✅ Automatic page numbering via two-pass generation
- ✅ Custom PageMarker flowables capture page numbers
- ✅ Beautiful formatting preserved
- ✅ ~1 second overhead for automatic updates
- ✅ Handles optional sections (rack layout, port mapping)

**Files:**
- `src/report_builder.py` - Complete implementation
- `docs/development/DYNAMIC-TOC-IMPLEMENTATION.md` - Full documentation

---

*Last Updated: October 22, 2025*
*Status: Dynamic TOC in production (see DYNAMIC-TOC-IMPLEMENTATION.md)*
*Static TOC preserved as backup*
