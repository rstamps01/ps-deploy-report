---

## Jira Project: [Installs] Create As-Built record functionality

https://vastdata.atlassian.net/browse/CSSCRUM-4186

---

## Initial Kick-off Meeting Notes: 8/29/25 @ 12:30pm PST

* Travis Mickelberry
* Mike Slisinger
* Brad Faas
* Ray Stamps

### Goal:

* Define method/approach to generate standardized post deployment "As Built" Reporting

### Agenda:

* Define information to include, level of detail, and format
* Identify data sources, available tools, and gaps
* Scope requirements and target timeline

### Target Outcome:

* Set MVP requirements and timeline target

---

## Research: Identify Information Available via VAST API

### Cluster Hardware Details:

* BOM

    * Part Numbers*
    * Quantities
    * Serial Numbers
    
* CBoxes

    * Quantity
    * Hardware type & manufacturer
    * # of Nodes
    * # of NICs
    * B2B enabled?
    * Encryption enabled?
    * Similarity enabled?
    * VAST Code Version(s)
    * Rack Height (U#)
    
* DBoxes

    * Quantity
    * Hardware type & manufacturer
    * # of Nodes
    * B2B enabled?
    * VAST Code Version(s)
    * Rack Height (U#)
    
* Switches

    * Quantity
    * Hardware type & manufacturer - Mellanox / Cisco / Aruba
    * Protocol - Ethernet / IB
    * Ports Count - 16 / 32 / 40 / 64
    * Port Speed(s)
    * Port Function - Node / IPL / ISL / MLAG
    * Ports in use
    * Ports Available
    * Switch role - Master / Slave*
    * Switch tier - Leaf / Spine*
    * Firmware Version(s)
    * Rack Height (U#)*
    * Cables - direct / splitter*
    
* Northbound Connection - Switch to Switch / CNode to Switch*

---

### Cluster Deployment Details:

* Usable Capacity
* Licensed Capacity
* Protocol - NFS, SMB, Object, Block, etc
* Use Case(s) - AI, ML, HPC, DB, BU, Cloud, Hybrid, etc*
* Advanced Features - Replication, DataBase, etc

---

### Cluster Administration Details:

* Cluster Name
* Cluster PSNT
* Cluster VMS VIP
* Default Users & Passwords*

    * VMS
    * IPMI
    * Mgmt Port
    * Tech Port
    
* IP Information

    * Network Services
    
        * DNS
        * DNS Search Domain
        * NTP
        * AD
        * LDAP
        * Other
        
    * CNode & DNode & Switch Management
    
        * Port Label
        * Port IP
        * Port Function
        * IPMI
        * Mgmt Port
        * Tech Port
        
    * Data Network
    
        * VIP
        * Replication
        * Other
        
    
* Node to Switch to Switch Connectivity map*
* Network Port Map
* Switch Configuration*
* Switch Cable Routing Validation Report*

**NOTE:** * indicates API alternative or manual data entry required

---

### Data Requiring Alternative Methods

The following data points will require manual input or the use of external tools:

* Hardware:

    * Bill of Materials (BOM) part numbers
    * Switch roles (Master/Slave) and tiers (Leaf/Spine)
    * Cable types (direct/splitter)
    
* Deployment:

    * Use cases (AI, ML, HPC, etc.)
    
* Administration:

    * Default users and passwords (should be managed securely and not stored in the report)
    * Node to switch to switch connectivity map
    * Switch configurations
    * Switch cable routing validation report
    

‌

---

## Example - Manually Generated Report:

### Alternative Option w/Labeling Chart:

---

## Report Links:

### Fortinet Expansion - Ottawa

https://vastdata-my.sharepoint.com/:b:/g/personal/ray_stamps_vastdata_onmicrosoft_com/EbNdBOxGbZdHiSibsoQy7oUBTB11GmtkELu2txI_ShmTLQ?e=bGdPQR

### Fortinet Expansion - Vancouver (Burnaby)

https://vastdata-my.sharepoint.com/:p:/g/personal/ray_stamps_vastdata_onmicrosoft_com/EVCYEcpyOxRJuWycSG5MnRoBcwQEfT-UBp86mjY1kTpLXw?e=eWbFXo

### Cerebras Installation - OKC

https://vastdata-my.sharepoint.com/:p:/g/personal/ray_stamps_vastdata_onmicrosoft_com/EdrgmtQRH9dAvZgcvxsYKAQBfrJXzTWzpA8UGZPHOYthTQ?e=2sdOss

---

## Review API documentation:

[https://10.143.11.204/docs/en/index-en.html](https://10.143.11.204/docs/en/index-en.html)

https://support.vastdata.com/s/api-docs?_gl=1*7nyv9k*_gcl_au*MTQ5NzI2Mzk2LjE3NTY4NDQxMzc.

---

## Review monitor data:

[https://monitor.vastdata.com/d/-MwXN3SWz/system-report?orgId=1&var-psnt=VA251913658](https://monitor.vastdata.com/d/-MwXN3SWz/system-report?orgId=1&var-psnt=VA251913658)

---

## Review deployment scripts:

Review Install Plan - [HERE](https://vastdata.atlassian.net/wiki/spaces/FIELD/pages/4183818246)

Expansion Plan - [HERE](https://vastdata.atlassian.net/wiki/spaces/FIELD/pages/5133631489)

---

## Review Slack channel content:

### Cerebras EKM Redeployment

External - https://vastsupport.slack.com/archives/C08NT1HH6Q0 

Internal - https://vastdata.slack.com/archives/C099RR1FHGF 

SSP1 - https://docs.google.com/spreadsheets/d/1rcAELAsyuX50yxeWcmFdCNxtysntzzaY5-K_7_aLMR8/edit?usp=sharing 

SSP2 - https://docs.google.com/spreadsheets/d/1mVzN_N9DzxQ9w7Tu38HOQEPftNpxLdSXcZYFqVTKRpY/edit?usp=sharing 

Install Plan - https://docs.google.com/spreadsheets/d/1mVzN_N9DzxQ9w7Tu38HOQEPftNpxLdSXcZYFqVTKRpY/edit?usp=sharing

### Fortinet Expansion (VAN)

External - https://vastsupport.slack.com/archives/C05KVSHKP7E 

Internal - https://vastdata.slack.com/archives/C096DK0TE6Q 

SSP1 - https://docs.google.com/spreadsheets/d/1l8waCWagukUtDhk8Sj6TStUz6lv2h0VPBC2_BOJxJvg/edit?usp=sharing 

SSP2 - https://docs.google.com/spreadsheets/d/1kzfnFaSuP_CtUlveNhVx1s7cGPwySFLtN-NrkiIPBEM/edit?usp=sharing 

Install Plan - https://vastdata.atlassian.net/wiki/x/VwA7eAE
