# VAST Cluster IPv6 Deployment — Requirements & Cluster-Create Flags

> Research compiled from VAST Data internal Confluence (site: `vastdata.atlassian.net`).
> Last compiled: 2026-07-24

---

## 1. Context: what "IPv6" support means for VAST

IPv6 is primarily driven by **service providers** and **Federal customers**. VAST's formal certification is narrow:

> "We made IPv6 USGv6 certification. This certification validates **only the server management interfaces and nothing else**." — IPv6 FRD

There are **two supported deployment models** — choosing between them is the first requirement:

| Model | What runs on IPv6 | Notes |
| --- | --- | --- |
| **Full IPv6** (e.g. Taiga Cloud) | All data *and* management traffic; LDAP, DNS, NFSv3/v4 w/ KRB5 AD, SMB, S3 | KRB5 uses `IP6.ARPA` for rDNS; end user needs IPv6 DNS delegation + round-robin in VIPPool |
| **Partial IPv6** (e.g. Genesis Cloud) | VIPPool + view-policy (data path) on IPv6; **management stays IPv4** | Driven by scale (thousands of IPs in host-based access rules) |

Source: [IPv6 FRD](https://vastdata.atlassian.net/wiki/spaces/DEV/pages/3907452951/IPv6+FRD)

---

## 2. Hard constraints / documented technical gaps

Plan around these — they dictate what must be correct **at install time**:

- **BMC/IPMI must be back-to-back (B2B).** IPMI is not part of IPv6 support.
- **No IPv4 → IPv6 conversion in place.** VAST will *not* support converting already-configured services (VMS-VIP, DNS) or the data network from IPv4 to IPv6. → **Deploy IPv6 from the start; do not migrate later.**
- **IPv4 and IPv6 must live in the *same* VIPPool.** Because of how view policies and share names work, a VIPPool carries two entries (one IPv4, one IPv6) for CIDR and gateway. VastDNS cannot be set to both versions simultaneously (one or the other).
- All protocols (NFSv3/NFSv4/SMB/S3) and auth services (AD/LDAP/NIS/DNS) must be validated for the chosen IP version; HTTPS/SSL must work over IPv6 for S3 and the VMS VIP.

Source: [IPv6 FRD](https://vastdata.atlassian.net/wiki/spaces/DEV/pages/3907452951/IPv6+FRD)

---

## 3. Cluster-create flags (`vcli cluster create`)

IPv6 support is enabled through these flags on the legacy install command:

| Flag | Purpose |
| --- | --- |
| `--cnode_ipv6_addresses` | Comma-separated list of CNode IPv6 addresses |
| `--dnode_ipv6_addresses` | Comma-separated list of DNode IPv6 addresses |
| `--ipv6-mgmt-vip` | IPv6 management VIP address |
| `--ipv6-external-gateway` | IPv6 external gateway |
| `--ipv6-prefix` | IPv6 prefix length (integer) |

> Note the inconsistent naming: node-address flags use **underscores** (`--cnode_ipv6_addresses`, `--dnode_ipv6_addresses`); VIP/gateway/prefix flags use **hyphens** (`--ipv6-mgmt-vip`, etc.). Use them exactly as written.

### Example command stanza

```bash
export cnodes_ips=`echo 172.16.128.{1..12} | sed 's/ /,/g'`
export dnodes_ips=`echo 172.16.128.{100..105} | sed 's/ /,/g'`

# add IPv6 addressing to the optional flags
export flags=' --cnode-cores 20 --enable-encryption --enable-pfc \
  --cnode_ipv6_addresses 2001:db8:30::1,2001:db8:30::2,... \
  --dnode_ipv6_addresses 2001:db8:30::100,2001:db8:30::101,... \
  --ipv6-mgmt-vip 2001:db8:30::100 \
  --ipv6-external-gateway 2001:db8:30::1 \
  --ipv6-prefix 64'

./vman.sh $branch_tag $pem_file vcli $VMAN_USER_PASSWORD -c cluster create \
  --build ${branch_tag} --cnode-ips ${cnodes_ips} --dnode-ips ${dnodes_ips} \
  --name $cluster_name --psnt $cluster_label ${flags}
```

**⚠️ Approval required.** These IPv6 flags are in the page's **"Other Flags"** section:

> "These flags require explicit approval from VAST Engineering, vForce, or Customer Support before use in production environments."

The page also marks IPv6 as **"possibly not GA yet."** Confirm GA status for your target VAST OS version before a customer deployment.

Source: [Legacy Install - vcli cluster create flags](https://vastdata.atlassian.net/wiki/spaces/FIELD/pages/6915293324/Legacy+Install+-+vcli+cluster+create+flags) (documented against 5.4.0)

---

## 4. Node/network configuration (`configure_network.py`)

`cluster create` sets node IPv6 addressing + the IPv6 mgmt VIP; the rest of the node network stack is configured with `configure_network.py`:

| Flag | Purpose |
| --- | --- |
| `--ext-ip-ipv6 <IPv6>` | External IPv6 address |
| `--ext-prefix-ipv6 <PREFIX>` | IPv6 prefix length |
| `--ext-gateway-ipv6 <IPv6>` | IPv6 default gateway |
| `--mgmt-vip-ipv6 <IPv6>` | Floating IPv6 management VIP (identical on all nodes) |
| `--mgmt-data-vip-ipv6` / `--mgmt-data-vip-prefix-ipv6` / `--mgmt-data-vip-gateway-ipv6` | Optional management-data IPv6 VIP (must differ from mgmt VIP) |
| `--ext-dns` / `--ntp` | Accept IPv6 servers (up to three DNS servers) |

### Dual-stack example

```bash
configure_network.py 3 \
  --ext-interface ens3f0 \
  --ext-ip 10.20.30.13 --ext-netmask 255.255.255.0 --ext-gateway 10.20.30.1 \
  --ext-ip-ipv6 2001:db8:30::13 --ext-prefix-ipv6 64 --ext-gateway-ipv6 2001:db8:30::1 \
  --mgmt-vip 10.20.30.100 --mgmt-vip-ipv6 2001:db8:30::100
```

Validation: `--mgmt-vip-ipv6` must differ from `--mgmt-data-vip-ipv6`; IPv6 args validated as IPv6. Fast IPv6 mgmt-VIP update is allowed only if an external IPv6 config already exists in the saved param file.

Source: [configure_network.py](https://vastdata.atlassian.net/wiki/spaces/~712020c7509c510ac042989c457d8f45eadd11/pages/7673577506/configure_network.py)

---

## 5. Management-plane items that must be IPv6-aware

During install/config, every field that accepts an IP must hold valid IPv6:

- Node mgmt IPs, node IPMI IPs
- Gateway, DNS, callhome proxy
- Switch mgmt IPs
- VIP pools (ranges, gateway, CIDR, polling VIPs)
- VastDNS service IP
- Replication peer VIPs
- Data-flow / top-actor filters
- SMTP / syslog / callhome hosts
- Mgmt IPv6 VIP must expose GUI/REST on the IPv6 endpoint

Source: [IPv6 - Management changes](https://vastdata.atlassian.net/wiki/spaces/DEV/pages/3872194640/IPv6+-+Management+changes)

---

## 6. Special case: true "IPv6-only" (L3 northband) installs

Newer pattern for **IPv6-only** clusters where external, NTP, and DNS are all IPv6, using L3 northband on the CNodes:

- DNodes configured normally as a back-to-back cluster; CNodes marked for L3 on the north ports with the mgmt interface on the north ports.
- Flags: `--auto-ports-ext-iface northband`, `--mgmt-vip-ipv6`, `--ext-ip-ipv6`, `--ext-prefix-ipv6 128`, `--nb-eth-mtu 9000 9000`, plus L3 flags `--l3-northband-asn <customer ASN>` and `--l3-northband-router-id <unique IPv4 per node>`.
- **All VIP Pools must be L3-enabled** and **all IPv6 VIP-pool CIDRs must be /128**; VMS expects the mgmt VIP IPv6 interface at prefix /128.
- FRR/BGP peers with the north ports must be verified up before proceeding (risk of losing access otherwise): `sudo vtysh -c "show bgp summary"`.

Source: [L3 northband | Install](https://vastdata.atlassian.net/wiki/spaces/do/pages/7901839482/L3+northband+Install) (based on release/5.4.3-sp3-hf9)

---

## 7. Operational access tip

To reach node ports over IPv6 during bring-up:

```bash
ssh -6 vastdata@fe80::4911:69e:feaf:6ee9%ens1f0
```

See "How To - Access Ports Using IPv6" (linked from [Deployments - Tools, Tips, and Tricks](https://vastdata.atlassian.net/wiki/spaces/~7120200e1c43a9b6f741eca536d39491156fa8/pages/5752586248/Deployments+-+Tools+Tips+and+Tricks)).

---

## 8. Requirements checklist (summary)

1. **Decide the model** up front: Full IPv6 vs Partial IPv6 — you cannot convert later.
2. **IPMI/BMC on back-to-back** networking (not part of IPv6 support).
3. **Provision IPv6 for every mgmt-plane object** (node mgmt, switches, VIP pools, DNS, NTP, callhome, replication).
4. **`vcli cluster create`**: add `--cnode_ipv6_addresses`, `--dnode_ipv6_addresses`, `--ipv6-mgmt-vip`, `--ipv6-external-gateway`, `--ipv6-prefix` (with approval).
5. **`configure_network.py`**: add `--ext-ip-ipv6`, `--ext-prefix-ipv6`, `--ext-gateway-ipv6`, `--mgmt-vip-ipv6`; identical mgmt VIP on all nodes.
6. **Put IPv4 + IPv6 in the same VIPPool**, with dual CIDR/GW entries.
7. **Validate protocols + auth (NFS/SMB/S3, AD/LDAP/NIS/DNS) and HTTPS** over the chosen IP version.
8. For **IPv6-only (L3 northband)**: use /128 prefixes for ext IP and all IPv6 VIP pools, L3-enabled VIP pools, north-port BGP/FRR verified.

---

## 9. Gaps / caveats

- The IPv6 FRD (last updated 2024) predates the L3-northband IPv6-only flow (2026); treat the FRD for *policy/constraints* and the L3 northband + `configure_network.py` pages for *current install mechanics*.
- The `vcli cluster create` flags page is written against **5.4.0**; flag set and GA status may differ on your target release. Cross-check release notes and the current install template.
- IPv6 create flags are gated as "Other Flags" and marked "possibly not GA yet" — get Engineering/vForce/CS approval before production use.
- The FRD lists NFSv3 as MVP with SMB/others following — confirm current protocol coverage against your target VAST OS release notes.

---

## Sources

- [IPv6 FRD](https://vastdata.atlassian.net/wiki/spaces/DEV/pages/3907452951/IPv6+FRD)
- [IPv6 - Management changes](https://vastdata.atlassian.net/wiki/spaces/DEV/pages/3872194640/IPv6+-+Management+changes)
- [IPv6 only - mgmt](https://vastdata.atlassian.net/wiki/spaces/DEV/pages/4540006444/IPv6+only+-+mgmt)
- [Legacy Install - vcli cluster create flags](https://vastdata.atlassian.net/wiki/spaces/FIELD/pages/6915293324/Legacy+Install+-+vcli+cluster+create+flags)
- [configure_network.py](https://vastdata.atlassian.net/wiki/spaces/~712020c7509c510ac042989c457d8f45eadd11/pages/7673577506/configure_network.py)
- [L3 northband | Install](https://vastdata.atlassian.net/wiki/spaces/do/pages/7901839482/L3+northband+Install)
- [Deployments - Tools, Tips, and Tricks](https://vastdata.atlassian.net/wiki/spaces/~7120200e1c43a9b6f741eca536d39491156fa8/pages/5752586248/Deployments+-+Tools+Tips+and+Tricks)
