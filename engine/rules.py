"""Mapping rule registry (44 rules) for L3SM -> L3NM -> device mapping.

Rule IDs follow the draft sections:
  R5.1-xx  service-level mapping   (batch #7 direct fields)
  R5.2-xx  site-level mapping      (batch #7 direct fields)
  R5.3-xx  access-level mapping    (batch #7 direct fields)
  R5.4-xx  derived fields          (batch #8 derived)
  R5.5-xx  dynamic extensions      (batch #8 derived)
  R6-xx    device distribution     (batch #9 SPLIT)
"""

from __future__ import annotations

from typing import Dict, List

RULES: List[Dict[str, str]] = [
    # ---- Section 5.1: service level (batch #7) ----
    {
        "id": "R5.1-01",
        "batch": "#7",
        "op": "COPY",
        "source": "l3sm vpn-service/vpn-id",
        "target": "l3nm vpn-service/vpn-id",
        "note": "VPN service identifier is copied verbatim.",
    },
    {
        "id": "R5.1-02",
        "batch": "#7",
        "op": "DROP",
        "source": "l3sm vpn-service/vpn-name",
        "target": "-",
        "note": "Service-layer naming has no network-layer counterpart.",
    },
    {
        "id": "R5.1-03",
        "batch": "#7",
        "op": "COPY",
        "source": "l3sm vpn-service/vpn-description",
        "target": "l3nm vpn-service/vpn-description",
        "note": "Description is copied verbatim.",
    },
    {
        "id": "R5.1-04",
        "batch": "#7",
        "op": "N/DROP",
        "source": "l3sm vpn-service/customer-name",
        "target": "l3nm vpn-service/customer-name",
        "note": "Customer name is optional in the network model; kept when present.",
    },
    {
        "id": "R5.1-05",
        "batch": "#7",
        "op": "DROP",
        "source": "l3sm vpn-service/vpn-type",
        "target": "-",
        "note": "Signaling type is a service-layer concept.",
    },
    {
        "id": "R5.1-06",
        "batch": "#7",
        "op": "D",
        "source": "l3sm vpn-service/vpn-service-topology",
        "target": "l3nm vpn-service/vpn-service-topology",
        "note": "Topology identity is derived (any-to-any/hub-spoke/...).",
    },
    {
        "id": "R5.1-07",
        "batch": "#7",
        "op": "D(*)",
        "source": "l3sm vpn-service/cloud-accesses",
        "target": "device underlay",
        "note": "Cloud access is derived into device underlay routing.",
    },
    {
        "id": "R5.1-08",
        "batch": "#7",
        "op": "D(*)",
        "source": "l3sm vpn-profiles",
        "target": "reference library",
        "note": "VPN profiles (cloud/qos/slo-sle identifiers) form a reference "
        "library consumed by derived fields; kept at the service layer.",
    },
    # ---- Section 5.2: site level (batch #7) ----
    {
        "id": "R5.2-01",
        "batch": "#7",
        "op": "RENAME",
        "source": "l3sm site",
        "target": "l3nm vpn-node",
        "note": "Site is renamed to VPN node.",
    },
    {
        "id": "R5.2-02",
        "batch": "#7",
        "op": "RENAME",
        "source": "l3sm site/site-id",
        "target": "l3nm vpn-node/vpn-node-id",
        "note": "Site identifier becomes the VPN node identifier.",
    },
    {
        "id": "R5.2-03",
        "batch": "#7",
        "op": "DROP",
        "source": "l3sm site/site-name",
        "target": "-",
        "note": "Site name is not represented in the network model.",
    },
    {
        "id": "R5.2-04",
        "batch": "#7",
        "op": "COPY",
        "source": "l3sm site/site-role",
        "target": "l3nm vpn-node/site-role",
        "note": "Site role is copied to the VPN node.",
    },
    {
        "id": "R5.2-05",
        "batch": "#7",
        "op": "DROP",
        "source": "l3sm site/locations",
        "target": "-",
        "note": "Geographic locations are not represented in the network model.",
    },
    {
        "id": "R5.2-06",
        "batch": "#7",
        "op": "DROP",
        "source": "l3sm site/devices",
        "target": "-",
        "note": "CE device inventory is not represented in the network model.",
    },
    {
        "id": "R5.2-07",
        "batch": "#7",
        "op": "DROP",
        "source": "l3sm site/management",
        "target": "-",
        "note": "Management mode is a service-layer concept.",
    },
    {
        "id": "R5.2-08",
        "batch": "#7",
        "op": "DROP",
        "source": "l3sm site/site-diversity",
        "target": "-",
        "note": "Diversity constraints are handled by the orchestrator.",
    },
    # ---- Section 5.3: access level (batch #7) ----
    {
        "id": "R5.3-01",
        "batch": "#7",
        "op": "RENAME",
        "source": "l3sm site-network-access",
        "target": "l3nm vpn-network-access",
        "note": "Site network access is renamed to VPN network access.",
    },
    {
        "id": "R5.3-02",
        "batch": "#7",
        "op": "RENAME",
        "source": "l3sm site-network-access/site-network-access-id",
        "target": "l3nm vpn-network-access/id",
        "note": "Access identifier is renamed.",
    },
    {
        "id": "R5.3-03",
        "batch": "#7",
        "op": "COPY",
        "source": "l3sm site-network-access/site-network-access-type",
        "target": "l3nm vpn-network-access/vpn-network-access-type",
        "note": "Access type is copied (point-to-point/multipoint).",
    },
    {
        "id": "R5.3-04",
        "batch": "#7",
        "op": "COPY",
        "source": "l3sm site-network-access/ip-connection",
        "target": "l3nm vpn-network-access/connection/ip-connection",
        "note": "IP connection (IPv4/IPv6 addresses) is copied.",
    },
    {
        "id": "R5.3-05",
        "batch": "#7",
        "op": "COPY",
        "source": "l3sm site-network-access/routing-protocols",
        "target": "l3nm vpn-network-access/service/routing-protocols",
        "note": "Routing protocols are copied; type identity prefix is rewritten "
        "l3vpn-svc -> l3vpn-ntw.",
    },
    {
        "id": "R5.3-06",
        "batch": "#7",
        "op": "DERIVE",
        "source": "l3sm site-network-access/service/svc-input-bandwidth",
        "target": "l3nm vpn-network-access/service/qos/qos-profile",
        "note": "Input bandwidth derives the QoS profile.",
    },
    {
        "id": "R5.3-07",
        "batch": "#7",
        "op": "DERIVE",
        "source": "l3sm site-network-access/service/svc-output-bandwidth",
        "target": "l3nm vpn-network-access/service/qos/qos-profile",
        "note": "Output bandwidth derives the QoS profile.",
    },
    {
        "id": "R5.3-08",
        "batch": "#7",
        "op": "COPY",
        "source": "l3sm site-network-access/service/mtu",
        "target": "l3nm vpn-network-access/service/mtu",
        "note": "MTU is copied verbatim.",
    },
    {
        "id": "R5.3-09",
        "batch": "#7",
        "op": "RENAME",
        "source": "l3sm site-network-access/service/security",
        "target": "l3nm vpn-network-access/service/security",
        "note": "Security container is renamed; encryption profile is kept.",
    },
    # ---- Section 5.4: derived fields (batch #8) ----
    {
        "id": "R5.4-01",
        "batch": "#8",
        "op": "DERIVE",
        "source": "l3sm vpn-service/vpn-id",
        "target": "l3nm vpn-node/vpn-node-properties/active-vpn-instance-profiles/rd",
        "note": "Route distinguisher is derived from the VPN id.",
    },
    {
        "id": "R5.4-02",
        "batch": "#8",
        "op": "DERIVE",
        "source": "l3sm vpn-service/vpn-id",
        "target": "l3nm vpn-node/vpn-node-properties/active-vpn-instance-profiles/vpn-targets",
        "note": "Route targets are derived from the VPN id.",
    },
    {
        "id": "R5.4-03",
        "batch": "#8",
        "op": "DERIVE",
        "source": "l3sm site/site-id",
        "target": "l3nm vpn-node/ne-id",
        "note": "Network element id is derived from the site id.",
    },
    {
        "id": "R5.4-04",
        "batch": "#8",
        "op": "DERIVE",
        "source": "l3sm vpn-service/vpn-id",
        "target": "device loopback router-id",
        "note": "Router id is a device-layer concept (draft 5.4); derived to the "
        "device loopback interface, not written into L3NM.",
    },
    {
        "id": "R5.4-05",
        "batch": "#8",
        "op": "DERIVE",
        "source": "l3sm vpn-service/cloud-accesses",
        "target": "device underlay",
        "note": "Underlay connectivity is derived from cloud access.",
    },
    # ---- Section 5.5: dynamic extensions (batch #8) ----
    {
        "id": "R5.5-01",
        "batch": "#8",
        "op": "COPY",
        "source": "l3sm site/temporary-connection-indicator",
        "target": "l3nm vpn-node (ntw-ext)",
        "note": "Temporary connection indicator is copied.",
    },
    {
        "id": "R5.5-02",
        "batch": "#8",
        "op": "COPY",
        "source": "l3sm site-network-access/service/dynamic-l3vpn/dynamic-l3vpn-id",
        "target": "l3nm vpn-network-access/dynamic-l3vpn/dynamic-l3vpn-id",
        "note": "Dynamic L3VPN id is copied.",
    },
    {
        "id": "R5.5-03",
        "batch": "#8",
        "op": "COPY",
        "source": "l3sm site-network-access/service/dynamic-l3vpn/adjustment-mode",
        "target": "l3nm vpn-network-access/dynamic-l3vpn/adjustment-mode",
        "note": "Adjustment mode is copied.",
    },
    {
        "id": "R5.5-04",
        "batch": "#8",
        "op": "COPY",
        "source": "l3sm site-network-access/service/qos/qos-profile/slo-sle-profile",
        "target": "l3nm vpn-network-access/service/qos/qos-profile",
        "note": "SLO/SLE profile reference is copied into the QoS profile.",
    },
    {
        "id": "R5.5-05",
        "batch": "#8",
        "op": "COPY",
        "source": "l3sm site-network-access/service/classification-policy",
        "target": "l3nm vpn-network-access/classification-policy",
        "note": "Classification policy is copied to the access level.",
    },
    {
        "id": "R5.5-06",
        "batch": "#8",
        "op": "COPY",
        "source": "l3sm site/service/classification-policy",
        "target": "l3nm vpn-node/classification-policy",
        "note": "Classification policy is copied to the node level.",
    },
    {
        "id": "R5.5-07",
        "batch": "#8",
        "op": "DERIVE",
        "source": "l3sm site-network-access/service/qos/qos-profile/custom/class/isolation",
        "target": "l3nm vpn-network-access/service/qos/qos-action/rule-isolation",
        "note": "QoS class isolation derives the rule-isolation flag.",
    },
    {
        "id": "R5.5-08",
        "batch": "#8",
        "op": "DERIVE",
        "source": "l3sm site-network-access/service/dynamic-l3vpn",
        "target": "l3nm vpn-network-access/perf-mon",
        "note": "Performance monitoring is derived from dynamic L3VPN.",
    },
    {
        "id": "R5.5-09",
        "batch": "#8",
        "op": "DERIVE",
        "source": "l3sm site-network-access/ip-connection-security",
        "target": "l3nm vpn-network-access/service/security/security-classes",
        "note": "IP connection security derives security classes.",
    },
    {
        "id": "R5.5-10",
        "batch": "#8",
        "op": "DERIVE",
        "source": "l3sm site-network-access/service/security/encryption",
        "target": "l3nm vpn-network-access/service/security/security-classes/encryption-profile-id",
        "note": "Encryption profile derives the security class encryption.",
    },
    # ---- Section 6: device distribution (batch #9 SPLIT) ----
    {
        "id": "R6-01",
        "batch": "#9",
        "op": "SPLIT",
        "source": "l3nm vpn-node + vpn-network-access",
        "target": "device vrfs/vrf + interfaces/interface + ip",
        "note": "G1: VRF, G2: interface, G3: IP addresses are split to PE devices.",
    },
    {
        "id": "R6-02",
        "batch": "#9",
        "op": "SPLIT",
        "source": "l3nm vpn-network-access/service/routing-protocols",
        "target": "device bgp/neighbor + ospf/instance + routing/static-route",
        "note": "G5: routing protocols are split to device routing config.",
    },
    {
        "id": "R6-03",
        "batch": "#9",
        "op": "SPLIT",
        "source": "l3nm classification-policy + qos",
        "target": "device acls/acl + qos/qos-profile + routing-policy/policy",
        "note": "G4: QoS, G6: ACL, G7: routing policy are split to devices.",
    },
    {
        "id": "R6-04",
        "batch": "#9",
        "op": "SPLIT",
        "source": "l3nm security + underlay",
        "target": "device ipsec/ike + sr-policies/sr-policy",
        "note": "G9: PQC/IPsec and G11: SR policy are split to devices.",
    },
    {
        "id": "R6-05",
        "batch": "#9",
        "op": "SPLIT",
        "source": "l3nm perf-mon + schedule",
        "target": "device stamp/session",
        "note": "G8: schedule and G10: perf-mon aggregation are split to STAMP sessions.",
    },
]


def rule_by_id(rule_id: str) -> Dict[str, str]:
    for r in RULES:
        if r["id"] == rule_id:
            return r
    raise KeyError(f"unknown rule id: {rule_id}")


def rules_by_batch(batch: str) -> List[Dict[str, str]]:
    return [r for r in RULES if r["batch"] == batch]