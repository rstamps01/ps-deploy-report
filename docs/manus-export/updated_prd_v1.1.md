# Project Requirements Document (PRD): VAST As-Built Report Generator

**Version:** 1.1 (Updated September 2025)  
**Original Version:** 1.0  
**Author:** Manus AI  
**Updates:** Enhanced API data points integration

---

## 1. Introduction & Vision

### 1.1. Problem Statement
Following the installation of a VAST Data cluster, Professional Services (PS) engineers manually gather configuration data to create an "as-built" report for the customer. This process is time-consuming, prone to human error, and can result in inconsistent documentation.

### 1.2. Proposed Solution
To develop a Python-based command-line tool that leverages the VAST REST API to automatically generate a comprehensive, professionally formatted as-built report. This tool will standardize the reporting process, save significant engineering time, and provide customers with a consistent, high-quality deliverable.

**Enhanced Solution (v1.1):** Recent API analysis has identified additional data points available through VAST API v7, increasing automated data collection coverage from approximately 70% to 80%, further reducing manual data entry requirements.

### 1.3. Target Audience
- **Primary Users:** VAST Data Professional Services Engineers, Systems Engineers, and Implementation Partners.
- **Secondary Audience:** VAST Data Support Engineers (for troubleshooting) and Customers (as the recipients of the final report).

---

## 2. Project Goals & Objectives

### 2.1. Business Goals
- Reduce the time spent on post-deployment documentation by at least 80%.
- Improve the quality and consistency of customer-facing documentation.
- Enhance the customer onboarding experience by providing immediate, detailed system documentation.
- **Enhanced Goal (v1.1):** Achieve 80% automated data collection through improved API utilization, reducing manual data entry errors.

### 2.2. Technical Objectives
- Develop a reliable and fault-tolerant Python application.
- Ensure secure handling of cluster credentials.
- Produce a report that is both human-readable (PDF) and machine-readable (JSON).
- Implement comprehensive logging for easy troubleshooting.
- **Enhanced Objective (v1.1):** Integrate newly discovered API capabilities for rack positioning and cluster support tracking.

---

## 3. Functional Requirements (What it Does)

### FR-1: Data Collection
The tool must connect to a specified VAST cluster and extract configuration data via its REST API.

**Enhanced FR-1 (v1.1):** The tool must utilize the expanded API capabilities including:
- Hardware rack positioning data via `Schema/CBox/index_in_rack` and `Schema/DBox/index_in_rack`
- Cluster Product Serial Number Tracking (PSNT) via `Schema/Cluster/psnt`

### FR-2: Report Sections
The tool must gather data for and structure the report into the following sections:

#### FR-2.1: Executive Summary
- Cluster Name, Version, GUID, State, License
- **Enhanced (v1.1):** Cluster PSNT for support tracking integration

#### FR-2.2: Physical Hardware Inventory
- CNodes, DNodes, hardware details
- **Enhanced (v1.1):** Automated rack height positioning for CBoxes and DBoxes

#### FR-2.3: Network Configuration
- DNS, NTP, VIP Pools

#### FR-2.4: Logical Configuration
- Tenants, Views, View Policies

#### FR-2.5: Security & Authentication
- AD/LDAP providers

#### FR-2.6: Data Protection
- Snapshot Policies

### FR-3: Report Generation
The tool must compile the collected data into two output formats:

#### FR-3.1: PDF Report
A professionally formatted PDF document with a title page, table of contents, and clear section headings.
**Enhanced (v1.1):** Include rack positioning diagrams and PSNT prominently in executive summary.

#### FR-3.2: JSON Report
A structured JSON file containing all the raw data collected from the API.
**Enhanced (v1.1):** Include rack height and PSNT fields in the structured data schema.

### FR-4: Configuration
The tool must use an external configuration file for settings like API timeouts.

### FR-5: Authentication
The tool must prompt the user for credentials at runtime or accept them via secure environment variables. Credentials must not be stored in plain text.

---

## 4. Non-Functional Requirements (How it Works)

### NFR-1: Performance
The entire report generation process for a standard-sized cluster should complete in under 5 minutes.

### NFR-2: Reliability & Fault Tolerance
- The tool must handle API connection errors and timeouts gracefully.
- It must implement a retry mechanism for transient network failures.
- If a non-critical data point cannot be retrieved, the tool must log a warning, mark the data as "Unavailable" in the report, and continue execution.
- **Enhanced NFR-2 (v1.1):** Graceful handling of clusters where enhanced API fields (rack heights, PSNT) may not be available in older versions.

### NFR-3: Usability
The tool must be a command-line interface (CLI) application that is simple to run with clear arguments (e.g., specifying the cluster IP and output directory).

### NFR-4: Logging
The tool must generate detailed, structured logs to a file, including INFO, WARNING, and ERROR levels to assist with troubleshooting.

### NFR-5: Security
Credentials must never be logged or stored in configuration files.

### NFR-6: Maintainability
The code must be modular, well-documented (docstrings, comments), and adhere to PEP 8 style guidelines.

---

## 5. Assumptions & Dependencies

### A-1: Network Access
The user running the tool will have network access to the VAST Management Service (VMS) IP address.

### A-2: Credentials
The user will have valid, read-only (or higher) credentials for the VAST cluster.

### A-3: API Version Compatibility (Enhanced v1.1)
The enhanced features (rack heights, PSNT) are available in VAST API v7 with cluster version 5.3+. The tool will gracefully handle older versions.

### D-1: Python Environment
The tool will require Python 3.8+ and access to the pip package manager for installing dependencies.

### D-2: API Version Support
The development will target VAST Cluster version 5.3 and API version 7. The tool should be designed with future API versions in mind.

---

## 6. Enhanced API Data Points (v1.1 Update)

### 6.1. Newly Discovered API Capabilities

The following data points have been identified as available through the VAST API v7, improving automated data collection:

| Data Point | Previous Method | Enhanced Method | API Schema Path |
|------------|----------------|-----------------|-----------------|
| CBox Rack Heights | Manual | API | `Schema/CBox/index_in_rack` |
| DBox Rack Heights | Manual | API | `Schema/DBox/index_in_rack` |
| Cluster PSNT | Manual | API | `Schema/Cluster/psnt` |

### 6.2. Impact on Data Collection Coverage

- **Previous Coverage:** ~70% of required data via API
- **Enhanced Coverage:** ~80% of required data via API
- **Improvement:** 10% reduction in manual data entry requirements

### 6.3. Implementation Requirements

The enhanced API capabilities require:
- Updated API handler methods for rack height collection
- Enhanced data validation for physical positioning data
- PSNT integration in cluster identification sections
- Backward compatibility handling for older cluster versions

---

## 7. Updated Project Plan

### 7.1. Enhanced Phase 1 Deliverables

**Sprint 1 (Weeks 1-2) - Enhanced Core Functionality:**
- **Setup:** Initialize Git repository, project structure, virtual environment
- **Enhanced API Handler:** Build resilient API client with expanded data collection capabilities including rack heights and PSNT
- **Enhanced Data Extractor:** Implement data extraction for all report sections with improved API coverage
- **Configuration:** Implement configuration file handling
- **Enhanced JSON Output:** Generate structured JSON with expanded data schema
- **Unit Tests:** Enhanced tests for new API capabilities
- **Deliverable:** Functional CLI tool with 80% automated data collection

### 7.2. Enhanced Phase 2 Deliverables

**Sprint 2 (Weeks 3-4) - Enhanced Report Formatting:**
- **Enhanced PDF Generator:** Professional formatting with rack positioning and PSNT integration
- **Logging Enhancement:** Comprehensive logging for all modules
- **Packaging:** Complete tool packaging with enhanced requirements
- **Enhanced Documentation:** Updated documentation reflecting new capabilities
- **Comprehensive Testing:** End-to-end testing including enhanced API features
- **Deliverable:** Complete tool with enhanced automated reporting capabilities

---

## 8. Updated Risk Management

| Risk | Likelihood | Impact | Enhanced Mitigation Strategy |
|------|------------|--------|------------------------------|
| API Changes/Undocumented Behavior | Medium | High | Build modularly with version detection for enhanced features. Implement graceful degradation for missing API fields. |
| Enhanced API Field Availability | Low | Medium | Implement backward compatibility checks. Provide clear messaging when enhanced features are unavailable. |
| Data Validation Complexity | Medium | Medium | Implement comprehensive validation for rack height formats and PSNT patterns. |

---

## 9. Success Criteria (Updated)

### 9.1. Primary Success Metrics
- Tool generates complete as-built reports in under 5 minutes
- 80% of data collected automatically via API (enhanced from 70%)
- Zero credential exposure in logs or configuration files
- Professional PDF output suitable for customer delivery

### 9.2. Enhanced Success Metrics (v1.1)
- Accurate rack positioning data collection for 100% of compatible clusters
- PSNT integration in all generated reports for support tracking
- Graceful handling of mixed-version cluster environments
- Enhanced report quality with physical layout information

---

**Document Version History:**
- **v1.0:** Original requirements document
- **v1.1:** Enhanced with additional API data points (rack heights, PSNT) and improved automated data collection coverage

