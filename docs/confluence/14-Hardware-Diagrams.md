# 14.0 - Hardware Diagrams: Qualified CBox, DBox, and Switches

| **DBoxes** | **5.2** | **5.1** | **5.0** | **4.7** | **4.6** | **4.5** | **4.4** | **4.3** | **4.2** | **4.1** | **4.0** | **3.6** | **3.4** | **3.2** |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| DF-5615. Maverick | X | X | X | X | X | X | X | X | X | X | X | X | X | X |
| DF-5630  Maverick | X | X | X | X | X | X | X | X | X\* | - | - | - | - | - |
| DF-3015 | X | X | X | X | X | X | X | \*\* | \*\* | - | - | - | - | - |
| DF-3060. (Ceres 60TB) | X | X | - | - | - | - | - | - | - | - | - | - | - | - |
| DF-5630 (MLK)\*\*\*\* | X | ≥sp40 | ≥sp60 |   |   |   |   |   |   |   |   |   |   |   |
| DF-5660 (MLK)\*\*\*\* | X | ≥sp40 | ≥sp60 | - | - | - | - | - | - | - | - | - | - | - |
| Mercury D Box V 1 - 15TB | X | X | X | X | \*\* | - | - | - | - | - | - | - | - | - |
| Mercury D Box V 1 - 30TB (TBC) | X | X | X | X | - | - | - | - | - | - | - | - | - | - |
| **CBoxes** |   |   |   |   |   |   |   |   |   |   |   |   |   |   |
| Broadwell | X | X | X | X | X | X | X | X | X | X | X | X | X | X |
| Cascade Lake (Old but still in the field) | X | X | X | X | X | X | X | X | X | X | X | - | - | - |
| Ice Lake (HPE) | X | X | X | X | X | X | \*\* | - | - | - | - | - | - | - |
| Ice Lake (Dell) | X | X | X | X | - | - | - | - | - | - | - | - | - | - |
| Mercury C Box - Cascade Lake | X | X | X | X | \*\* | - | - | - | - | - | - | - | - | - |
| **EBoxes - Include CNode and DNode functions - 1Ux12** |   |   |   |   |   |   |   |   |   |   |   |   |   |   |
| SMC | X | Alpha | - | - | - | - | - | - | - | - | - | - | - | - |
| Cisco (pending) |  |  |  |  |  |  |  |  |  |  |  |  |  |  |

X Supported/GA,  - No support,  \*DF-5630 requires at least 2 D-boxes until 4.3,  \*\*Beta/Approval Only \*\*\* without Limiter/approval only \*\*\*\*Minimum SW required for MLK (New Cluster) listed. FRU Replacement has additional minimum SW requirements.

| **Ethernet Switches** |
| --- |
| **VAST SKU** | **Switch Model** | **Description** | **Availability** | **Manufacture SKU** |   |
| ETH-NVMEF-2X16 | NVIDIA SN2100 | 16 x 100G Switch | Available Now |   |   |
| ETH-NVMEF-1X32 | NVIDIA SN2700C | 32 x 100G Switch | Available Now (EOS) |   |   |
| ETH-NVMEF-1X32-200G | NVIDIA SN3700 | 32 x 200G Switch | Available Now |   |   |
| ETH-NVMEF-1X64-200G | NVIDIA SN4600C | 64 x 100G Switch | Available Now |   |   |
| ETH-NVMEF-1X64 | NVIDIA SN4600 | 64 x 200G Switch | Available Now |   |   |
| ETH-NVMEF-1X32-400G | Arista 7050DX4-32S | 32 x 400G Switch QSFP-DD | Available Now (At Lead Time) |   |   |
| ETH-NVMEF-1X32-400G | NVIDIA SN4700 | 32 x 400G Switch QSFP-DD | Awaiting ETA |   |   |
| ETH-NVMEF-1X64-400G | Arista 7060DX5-64S | 64 x 400G Switch QSFP-DD | Available Now (At Lead Time) |   |   |
| ETH-NVMEF-1X64-400G | NVIDIA SN5400 | 64 x 400G Switch QSFP-DD | Available Now (At Lead Time) |   |   |
| **IB Switches** |
| **VAST SKU** | **Switch Model** | **Description** | **Availability** | **Manufacture SKU** |   |
| HDR-NVMEF-1X40 | NVIDIA QM8700 | 40 x 200G Switch (HDR)- Managed | Available Now | MQM8700-HS2F-VTA |   |
| HDR-NVMEF-1X40 | NVIDIA QM8790 | 40 x 200G Switch (HDR) - UnManaged | Available Now | MQM8790-HS2F |   |
| EDR-NVMEF-1X36 | NVIDIA MSB7790 | 36 port x 100Gb Unmanaged | Supported / No Longer Available | MSB7790-EB2F |   |
| EDR-NVMEF-1X36 | NVIDIA MSB7800 | 36 port x 100Gb Managed | Supported / No Longer Available | MSB7800-ES2F |   |

# VAST Supported Switches 

| **Ethernet Switches** |   |
| --- | --- |
| **Switch Make/Model** | **Description** | **OS** | **Notes** |   |
| Arista DCS-7060PX4-32 | 32 x 400G 1U Switch | EOS |   |   |
| Arista 7050CX3-32S | 32 x 100G 1U Switch | EOS |   |   |
| Cisco Nexus C9336C-FX2 | 36 x 100G 1.2RU Switch | NX-OS |   |   |
| Cisco Nexus 9364D-GX2 | 64 x 400G 2U Switch | NX-OS |   |   |
| Aruba 8325-32C | 32 x 100G 1U Switch |   |   |   |
| NVIDIA SN4700 | 32 x 400G Switch (QSFP-DD) | Cumulus |   |   |
| _NVIDIA SN5400_ | _64 x 4000G Switch (QSFP-DD)_ | _Cumulus_ |   |   |
| NVIDIA SN5600 | 64 x 800G Switch (OSFP) | Cumulus | Used to comply with NVIDIA NCP |   |   |
| _NVIDIA QM9700_ | _64 port x 400G (OSFP)_ | _Cumulus_ |   | _MQM9700-NS2F_ |
