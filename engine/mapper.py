"""Core mapping engine: L3SM -> L3NM -> device configuration.

Implements the 44 rules from draft-huang-onsen-l3vpn-model-mapping
(sections 5.1-5.5 and 6) with full trace recording.
"""

from __future__ import annotations

import copy
from typing import Any, Dict, List, Optional, Tuple

from .trace import TraceRecorder

SVC_PREFIX = "ietf-l3vpn-svc:"
NTW_PREFIX = "ietf-l3vpn-ntw:"
SVC_TOP = "ietf-l3vpn-svc:l3vpn-svc"
NTW_TOP = "ietf-l3vpn-ntw:l3vpn-ntw"
DEVICES = ["pe1", "pe2", "pe3"]


def _svc_path(*segs: str) -> str:
    return "l3sm:/" + "/".join(segs)


def _ntw_path(*segs: str) -> str:
    return "l3nm:/" + "/".join(segs)


def _dev_path(device: str, *segs: str) -> str:
    return f"device:{device}/" + "/".join(segs)


def _rewrite_identity(value: str, old: str, new: str) -> str:
    """Rewrite an identityref module prefix."""
    if isinstance(value, str) and value.startswith(old):
        return new + value[len(old):]
    return value


def _derive_rd(vpn_id: str, index: int) -> str:
    return f"65000:{index}"


def _derive_rt(vpn_id: str, index: int) -> str:
    return f"65000:{100 + index}"


def _derive_ne_id(site_id: str) -> str:
    return f"NE-{site_id}"


def _derive_router_id(index: int) -> str:
    return f"10.255.{index}.1"


def _derive_qos_profile(bandwidth: Optional[int]) -> str:
    if bandwidth is None:
        return "QOS-default"
    try:
        bw = int(bandwidth)
    except (TypeError, ValueError):
        return "QOS-default"
    mbps = bw // 1_000_000
    return f"QOS-{mbps}M"


def _pick_device(node_index: int, site_role: Optional[str]) -> str:
    """Assign a VPN node to a PE device: hub role -> pe1, spokes round-robin."""
    if site_role and "hub" in site_role:
        return "pe1"
    return DEVICES[node_index % len(DEVICES)]


# ---------------------------------------------------------------------------
# L3SM -> L3NM
# ---------------------------------------------------------------------------

def map_l3sm_to_l3nm(l3sm: Dict[str, Any], trace: TraceRecorder) -> Dict[str, Any]:
    """Map an L3SM instance to an L3NM instance (batches #7 and #8)."""
    svc = l3sm.get(SVC_TOP, {})
    vpn_services = svc.get("vpn-services", {}).get("vpn-service", [])

    # ---- R5.1-08 vpn-profiles D(*) ----
    if "vpn-profiles" in svc:
        trace.record(
            "R5.1-08", "#7",
            _svc_path("vpn-profiles"),
            "reference library", "D(*)",
            list(svc["vpn-profiles"].keys()),
            "VPN profiles form a reference library consumed by derived fields.",
        )

    l3nm: Dict[str, Any] = {
        NTW_TOP: {"vpn-services": {"vpn-service": []}}
    }

    for vs in vpn_services:
        vpn_id = vs.get("vpn-id", "")
        vs_path = f"vpn-services/vpn-service[vpn-id={vpn_id}]"
        nvs: Dict[str, Any] = {"vpn-id": vpn_id, "vpn-nodes": {"vpn-node": []}}

        # ---- R5.1-01 vpn-id COPY ----
        trace.record(
            "R5.1-01", "#7",
            _svc_path(vs_path, "vpn-id"),
            _ntw_path("vpn-services", f"vpn-service[vpn-id={vpn_id}]", "vpn-id"),
            "COPY", vpn_id,
        )

        # ---- R5.1-02 vpn-name DROP ----
        if "vpn-name" in vs:
            trace.record(
                "R5.1-02", "#7",
                _svc_path(vs_path, "vpn-name"), "-", "DROP", vs["vpn-name"],
                "Service-layer naming has no network-layer counterpart.",
            )

        # ---- R5.1-03 vpn-description COPY ----
        if "vpn-description" in vs:
            nvs["vpn-description"] = vs["vpn-description"]
            trace.record(
                "R5.1-03", "#7",
                _svc_path(vs_path, "vpn-description"),
                _ntw_path("vpn-services", f"vpn-service[vpn-id={vpn_id}]", "vpn-description"),
                "COPY", vs["vpn-description"],
            )

        # ---- R5.1-04 customer-name N/DROP ----
        if "customer-name" in vs:
            nvs["customer-name"] = vs["customer-name"]
            trace.record(
                "R5.1-04", "#7",
                _svc_path(vs_path, "customer-name"),
                _ntw_path("vpn-services", f"vpn-service[vpn-id={vpn_id}]", "customer-name"),
                "N/DROP", vs["customer-name"],
                "Optional in the network model; kept when present.",
            )

        # ---- R5.1-05 vpn-type DROP ----
        if "vpn-type" in vs:
            trace.record(
                "R5.1-05", "#7",
                _svc_path(vs_path, "vpn-type"), "-", "DROP", vs["vpn-type"],
                "Signaling type is a service-layer concept.",
            )

        # ---- R5.1-06 vpn-service-topology D ----
        topo = vs.get("vpn-service-topology", SVC_PREFIX + "any-to-any")
        nvs["vpn-service-topology"] = _rewrite_identity(topo, SVC_PREFIX, NTW_PREFIX)
        trace.record(
            "R5.1-06", "#7",
            _svc_path(vs_path, "vpn-service-topology"),
            _ntw_path("vpn-services", f"vpn-service[vpn-id={vpn_id}]", "vpn-service-topology"),
            "D", nvs["vpn-service-topology"],
            "Topology identity is derived.",
        )

        # ---- R5.1-07 cloud-access D(*) ----
        cloud_accesses = vs.get("cloud-accesses", {}).get("cloud-access", [])
        if cloud_accesses:
            trace.record(
                "R5.1-07", "#7",
                _svc_path(vs_path, "cloud-accesses"),
                "device underlay", "D(*)",
                [ca.get("cloud-access-id") for ca in cloud_accesses],
                "Cloud access is derived into device underlay routing.",
            )

        # ---- sites -> vpn-nodes ----
        sites = vs.get("sites", {}).get("site", [])
        node_index = 0
        for site in sites:
            site_id = site.get("site-id", "")
            site_path = f"{vs_path}/sites/site[site-id={site_id}]"
            site_role = site.get("site-role")

            # ---- R5.2-01 site -> vpn-node RENAME ----
            trace.record(
                "R5.2-01", "#7",
                _svc_path(site_path),
                _ntw_path("vpn-services", f"vpn-service[vpn-id={vpn_id}]",
                          "vpn-nodes", f"vpn-node[vpn-node-id={site_id}]"),
                "RENAME", site_id,
            )

            nvn: Dict[str, Any] = {
                "vpn-node-id": site_id,
                "vpn-node-properties": {"active-vpn-instance-profiles": {
                    "active-vpn-instance-profile": []
                }},
                "vpn-network-accesses": {"vpn-network-access": []},
            }

            # ---- R5.2-02 site-id -> vpn-node-id RENAME ----
            trace.record(
                "R5.2-02", "#7",
                _svc_path(site_path, "site-id"),
                _ntw_path("vpn-services", f"vpn-service[vpn-id={vpn_id}]",
                          "vpn-nodes", f"vpn-node[vpn-node-id={site_id}]", "vpn-node-id"),
                "RENAME", site_id,
            )

            # ---- R5.2-03 site-name DROP ----
            if "site-name" in site:
                trace.record(
                    "R5.2-03", "#7",
                    _svc_path(site_path, "site-name"), "-", "DROP", site["site-name"],
                )

            # ---- R5.2-04 site-role COPY ----
            if site_role:
                nvn["site-role"] = _rewrite_identity(site_role, SVC_PREFIX, NTW_PREFIX)
                trace.record(
                    "R5.2-04", "#7",
                    _svc_path(site_path, "site-role"),
                    _ntw_path("vpn-services", f"vpn-service[vpn-id={vpn_id}]",
                              "vpn-nodes", f"vpn-node[vpn-node-id={site_id}]", "site-role"),
                    "COPY", nvn["site-role"],
                )

            # ---- R5.2-05 locations DROP ----
            if "locations" in site:
                trace.record(
                    "R5.2-05", "#7",
                    _svc_path(site_path, "locations"), "-", "DROP",
                    [loc.get("location-id") for loc in site["locations"].get("location", [])],
                )

            # ---- R5.2-06 devices DROP ----
            if "devices" in site:
                trace.record(
                    "R5.2-06", "#7",
                    _svc_path(site_path, "devices"), "-", "DROP",
                    [d.get("device-id") for d in site["devices"].get("device", [])],
                )

            # ---- R5.2-07 management DROP ----
            if "management" in site:
                trace.record(
                    "R5.2-07", "#7",
                    _svc_path(site_path, "management"), "-", "DROP", site["management"],
                )

            # ---- R5.2-08 site-diversity DROP ----
            if "site-diversity" in site:
                trace.record(
                    "R5.2-08", "#7",
                    _svc_path(site_path, "site-diversity"), "-", "DROP",
                    "Handled by the orchestrator.",
                )

            # ---- R5.4-01 RD DERIVE ----
            rd = _derive_rd(vpn_id, node_index + 1)
            profile = {
                "profile-name": f"{vpn_id}-profile",
                "rd": rd,
                "vpn-targets": {"vpn-target": []},
            }
            trace.record(
                "R5.4-01", "#8",
                _svc_path(vs_path, "vpn-id"),
                _ntw_path("vpn-services", f"vpn-service[vpn-id={vpn_id}]",
                          "vpn-nodes", f"vpn-node[vpn-node-id={site_id}]",
                          "vpn-node-properties", "active-vpn-instance-profiles",
                          "active-vpn-instance-profile", "rd"),
                "DERIVE", rd,
            )

            # ---- R5.4-02 RT DERIVE ----
            rt = _derive_rt(vpn_id, node_index + 1)
            profile["vpn-targets"]["vpn-target"].append({
                "rt": rt,
                "rt-type": NTW_PREFIX + "both",
            })
            trace.record(
                "R5.4-02", "#8",
                _svc_path(vs_path, "vpn-id"),
                _ntw_path("vpn-services", f"vpn-service[vpn-id={vpn_id}]",
                          "vpn-nodes", f"vpn-node[vpn-node-id={site_id}]",
                          "vpn-node-properties", "active-vpn-instance-profiles",
                          "active-vpn-instance-profile", "vpn-targets", "vpn-target"),
                "DERIVE", rt,
            )
            nvn["vpn-node-properties"]["active-vpn-instance-profiles"][
                "active-vpn-instance-profile"].append(profile)

            # ---- R5.4-03 ne-id DERIVE ----
            ne_id = _derive_ne_id(site_id)
            nvn["ne-id"] = ne_id
            trace.record(
                "R5.4-03", "#8",
                _svc_path(site_path, "site-id"),
                _ntw_path("vpn-services", f"vpn-service[vpn-id={vpn_id}]",
                          "vpn-nodes", f"vpn-node[vpn-node-id={site_id}]", "ne-id"),
                "DERIVE", ne_id,
            )

            # ---- R5.4-04 router-id DERIVE (device layer only) ----
            router_id = _derive_router_id(node_index + 1)
            trace.record(
                "R5.4-04", "#8",
                _svc_path(vs_path, "vpn-id"),
                "device loopback router-id", "DERIVE", router_id,
                "Router id is a device-layer concept; not written into L3NM.",
            )

            # ---- R5.4-05 underlay DERIVE ----
            if cloud_accesses:
                trace.record(
                    "R5.4-05", "#8",
                    _svc_path(vs_path, "cloud-accesses"),
                    "device underlay", "DERIVE",
                    "Underlay connectivity derived from cloud access.",
                )

            # ---- R5.5-01 temporary-connection-indicator COPY ----
            if "ietf-l3vpn-svc-dynamic-ext:temporary-connection-indicator" in site:
                nvn["ietf-l3vpn-ntw-ext:temporary-connection-indicator"] = \
                    site["ietf-l3vpn-svc-dynamic-ext:temporary-connection-indicator"]
                trace.record(
                    "R5.5-01", "#8",
                    _svc_path(site_path, "ietf-l3vpn-svc-dynamic-ext:temporary-connection-indicator"),
                    _ntw_path("vpn-services", f"vpn-service[vpn-id={vpn_id}]",
                              "vpn-nodes", f"vpn-node[vpn-node-id={site_id}]",
                              "ietf-l3vpn-ntw-ext:temporary-connection-indicator"),
                    "COPY", site["ietf-l3vpn-svc-dynamic-ext:temporary-connection-indicator"],
                )

            # ---- R5.5-06 site-level classification-policy COPY ----
            site_service = site.get("ietf-l3vpn-svc-dynamic-ext:service", {})
            site_class_pol = site_service.get("classification-policy", [])
            if site_class_pol:
                nvn["ietf-l3vpn-ntw-ext:classification-policy"] = copy.deepcopy(
                    site_class_pol)
                trace.record(
                    "R5.5-06", "#8",
                    _svc_path(site_path, "service", "classification-policy"),
                    _ntw_path("vpn-services", f"vpn-service[vpn-id={vpn_id}]",
                              "vpn-nodes", f"vpn-node[vpn-node-id={site_id}]",
                              "ietf-l3vpn-ntw-ext:classification-policy"),
                    "COPY", [r.get("rule-id") for r in site_class_pol],
                )

            # ---- site-network-accesses -> vpn-network-accesses ----
            snas = site.get("site-network-accesses", {}).get("site-network-access", [])
            for sna in snas:
                acc_id = sna.get("site-network-access-id", "")
                sna_path = f"{site_path}/site-network-accesses/site-network-access[site-network-access-id={acc_id}]"
                nva_path = ("vpn-services", f"vpn-service[vpn-id={vpn_id}]",
                            "vpn-nodes", f"vpn-node[vpn-node-id={site_id}]",
                            "vpn-network-accesses", f"vpn-network-access[id={acc_id}]")

                # ---- R5.3-01 RENAME ----
                trace.record(
                    "R5.3-01", "#7",
                    _svc_path(sna_path),
                    _ntw_path(*nva_path),
                    "RENAME", acc_id,
                )

                nva: Dict[str, Any] = {
                    "id": acc_id,
                    "connection": {},
                    "service": {},
                }

                # ---- R5.3-02 id RENAME ----
                trace.record(
                    "R5.3-02", "#7",
                    _svc_path(sna_path, "site-network-access-id"),
                    _ntw_path(*nva_path, "id"),
                    "RENAME", acc_id,
                )

                # ---- R5.3-03 access type COPY ----
                acc_type = sna.get("site-network-access-type")
                if acc_type:
                    nva["vpn-network-access-type"] = _rewrite_identity(
                        acc_type, SVC_PREFIX, NTW_PREFIX)
                    trace.record(
                        "R5.3-03", "#7",
                        _svc_path(sna_path, "site-network-access-type"),
                        _ntw_path(*nva_path, "vpn-network-access-type"),
                        "COPY", nva["vpn-network-access-type"],
                    )

                # ---- R5.3-04 ip-connection COPY ----
                ip_conn = sna.get("ip-connection")
                if ip_conn:
                    nva["connection"]["ip-connection"] = copy.deepcopy(ip_conn)
                    trace.record(
                        "R5.3-04", "#7",
                        _svc_path(sna_path, "ip-connection"),
                        _ntw_path(*nva_path, "connection", "ip-connection"),
                        "COPY", list(ip_conn.keys()),
                    )

                # ---- R5.3-05 routing-protocols COPY ----
                rp = sna.get("routing-protocols", {}).get("routing-protocol", [])
                if rp:
                    nva["service"]["routing-protocols"] = {"routing-protocol": []}
                    for proto in rp:
                        p = copy.deepcopy(proto)
                        if "type" in p:
                            p["type"] = _rewrite_identity(p["type"], SVC_PREFIX, NTW_PREFIX)
                        if "bgp" in p and "address-family" in p["bgp"]:
                            p["bgp"]["address-family"] = _rewrite_identity(
                                p["bgp"]["address-family"], SVC_PREFIX, NTW_PREFIX)
                        if "ospf" in p and "address-family" in p["ospf"]:
                            p["ospf"]["address-family"] = _rewrite_identity(
                                p["ospf"]["address-family"], SVC_PREFIX, NTW_PREFIX)
                        nva["service"]["routing-protocols"]["routing-protocol"].append(p)
                    trace.record(
                        "R5.3-05", "#7",
                        _svc_path(sna_path, "routing-protocols"),
                        _ntw_path(*nva_path, "service", "routing-protocols"),
                        "COPY", [p.get("type") for p in rp],
                        "Type identity prefix rewritten l3vpn-svc -> l3vpn-ntw.",
                    )

                # ---- service fields ----
                svc = sna.get("service", {})
                dyn_svc = sna.get("ietf-l3vpn-svc-dynamic-ext:service", {})

                # R5.3-06/07 bandwidth DERIVE -> qos-profile
                in_bw = svc.get("svc-input-bandwidth")
                out_bw = svc.get("svc-output-bandwidth")
                qos_profile = None
                if in_bw is not None:
                    qos_profile = _derive_qos_profile(in_bw)
                    trace.record(
                        "R5.3-06", "#7",
                        _svc_path(sna_path, "service", "svc-input-bandwidth"),
                        _ntw_path(*nva_path, "service", "qos", "qos-profile"),
                        "DERIVE", qos_profile,
                    )
                if out_bw is not None:
                    qos_profile = _derive_qos_profile(out_bw)
                    trace.record(
                        "R5.3-07", "#7",
                        _svc_path(sna_path, "service", "svc-output-bandwidth"),
                        _ntw_path(*nva_path, "service", "qos", "qos-profile"),
                        "DERIVE", qos_profile,
                    )
                if qos_profile:
                    nva["service"].setdefault("qos", {})["qos-profile"] = qos_profile

                # R5.3-08 mtu COPY
                if "mtu" in svc:
                    nva["service"]["mtu"] = svc["mtu"]
                    trace.record(
                        "R5.3-08", "#7",
                        _svc_path(sna_path, "service", "mtu"),
                        _ntw_path(*nva_path, "service", "mtu"),
                        "COPY", svc["mtu"],
                    )

                # R5.3-09 security RENAME
                if "security" in svc:
                    nva["service"]["security"] = copy.deepcopy(svc["security"])
                    trace.record(
                        "R5.3-09", "#7",
                        _svc_path(sna_path, "service", "security"),
                        _ntw_path(*nva_path, "service", "security"),
                        "RENAME", list(svc["security"].keys()),
                    )

                # ---- R5.5-02/03 dynamic-l3vpn COPY ----
                dyn = dyn_svc.get("dynamic-l3vpn", {})
                if dyn:
                    nva["ietf-l3vpn-ntw-ext:dynamic-l3vpn"] = copy.deepcopy(dyn)
                    if "dynamic-l3vpn-id" in dyn:
                        trace.record(
                            "R5.5-02", "#8",
                            _svc_path(sna_path, "service", "dynamic-l3vpn", "dynamic-l3vpn-id"),
                            _ntw_path(*nva_path, "ietf-l3vpn-ntw-ext:dynamic-l3vpn", "dynamic-l3vpn-id"),
                            "COPY", dyn["dynamic-l3vpn-id"],
                        )
                    if "adjustment-mode" in dyn:
                        trace.record(
                            "R5.5-03", "#8",
                            _svc_path(sna_path, "service", "dynamic-l3vpn", "adjustment-mode"),
                            _ntw_path(*nva_path, "ietf-l3vpn-ntw-ext:dynamic-l3vpn", "adjustment-mode"),
                            "COPY", dyn["adjustment-mode"],
                        )

                # ---- R5.5-04 slo-sle-profile COPY ----
                slo = dyn_svc.get("qos", {}).get("qos-profile", {}).get("slo-sle-profile")
                if slo:
                    nva["service"].setdefault("qos", {})["qos-profile"] = slo
                    trace.record(
                        "R5.5-04", "#8",
                        _svc_path(sna_path, "service", "qos", "qos-profile", "slo-sle-profile"),
                        _ntw_path(*nva_path, "service", "qos", "qos-profile"),
                        "COPY", slo,
                    )

                # ---- R5.5-05 access-level classification-policy COPY ----
                acc_class_pol = dyn_svc.get("classification-policy", [])
                if acc_class_pol:
                    nva["ietf-l3vpn-ntw-ext:classification-policy"] = copy.deepcopy(
                        acc_class_pol)
                    trace.record(
                        "R5.5-05", "#8",
                        _svc_path(sna_path, "service", "classification-policy"),
                        _ntw_path(*nva_path, "ietf-l3vpn-ntw-ext:classification-policy"),
                        "COPY", [r.get("rule-id") for r in acc_class_pol],
                    )

                # ---- R5.5-07 qos isolation DERIVE ----
                isolation = svc.get("qos", {}).get("qos-profile", {}).get(
                    "custom", {}).get("class", [])
                if isolation:
                    nva["service"].setdefault("ietf-l3vpn-ntw-ext:qos", {}).setdefault(
                        "qos-action", {})["rule-isolation"] = True
                    trace.record(
                        "R5.5-07", "#8",
                        _svc_path(sna_path, "service", "qos", "qos-profile", "custom", "class", "isolation"),
                        _ntw_path(*nva_path, "service", "ietf-l3vpn-ntw-ext:qos", "qos-action", "rule-isolation"),
                        "DERIVE", True,
                    )

                # ---- R5.5-08 perf-mon DERIVE ----
                if dyn:
                    nva["ietf-l3vpn-ntw-ext:perf-mon"] = {
                        "enabled": True,
                        "interval": 60,
                        "metrics": ["delay", "jitter", "packet-loss"],
                    }
                    trace.record(
                        "R5.5-08", "#8",
                        _svc_path(sna_path, "service", "dynamic-l3vpn"),
                        _ntw_path(*nva_path, "ietf-l3vpn-ntw-ext:perf-mon"),
                        "DERIVE", ["delay", "jitter", "packet-loss"],
                    )

                # ---- R5.5-09 ip-connection-security DERIVE ----
                ipsec = sna.get("ietf-l3vpn-svc-dynamic-ext:ip-connection-security")
                if ipsec:
                    sec_classes = []
                    for i, pref in enumerate(
                        ipsec.get("allowed-ipv4-prefixes", [])
                        + ipsec.get("allowed-ipv6-prefixes", [])
                    ):
                        sec_classes.append({
                            "class-id": f"SC-{acc_id}-{i + 1}",
                            "allowed-ipv4-prefixes": ipsec.get("allowed-ipv4-prefixes", []),
                            "allowed-ipv6-prefixes": ipsec.get("allowed-ipv6-prefixes", []),
                        })
                    nva["service"].setdefault(
                        "ietf-l3vpn-ntw-ext:security", {}).setdefault(
                        "security-classes", {"security-class": sec_classes},
                    )
                    trace.record(
                        "R5.5-09", "#8",
                        _svc_path(sna_path, "ietf-l3vpn-svc-dynamic-ext:ip-connection-security"),
                        _ntw_path(*nva_path, "service", "ietf-l3vpn-ntw-ext:security",
                                  "security-classes"),
                        "DERIVE", [c["class-id"] for c in sec_classes],
                    )

                # ---- R5.5-10 encryption DERIVE ----
                enc = svc.get("security", {}).get("encryption", {})
                if enc.get("encryption-profile-id"):
                    nva["service"].setdefault(
                        "ietf-l3vpn-ntw-ext:security", {}).setdefault(
                        "security-classes", {"security-class": []},
                    )
                    nva["service"]["ietf-l3vpn-ntw-ext:security"][
                        "security-classes"]["security-class"].append({
                            "class-id": f"ENC-{acc_id}",
                            "encryption-profile-id": enc["encryption-profile-id"],
                        })
                    trace.record(
                        "R5.5-10", "#8",
                        _svc_path(sna_path, "service", "security", "encryption"),
                        _ntw_path(*nva_path, "service", "ietf-l3vpn-ntw-ext:security",
                                  "security-classes", "security-class", "encryption-profile-id"),
                        "DERIVE", enc["encryption-profile-id"],
                    )

                nvn["vpn-network-accesses"]["vpn-network-access"].append(nva)

            nvs["vpn-nodes"]["vpn-node"].append(nvn)
            node_index += 1

        l3nm[NTW_TOP]["vpn-services"]["vpn-service"].append(nvs)

    return l3nm


# ---------------------------------------------------------------------------
# L3NM -> device configuration
# ---------------------------------------------------------------------------

def map_l3nm_to_device(l3nm: Dict[str, Any], trace: TraceRecorder) -> Dict[str, Any]:
    """Map an L3NM instance to per-PE device configuration (batch #9 SPLIT)."""
    devices: Dict[str, Any] = {d: {} for d in DEVICES}
    vpn_services = l3nm.get(NTW_TOP, {}).get("vpn-services", {}).get("vpn-service", [])

    for vs in vpn_services:
        vpn_id = vs.get("vpn-id", "")
        vs_path = f"vpn-services/vpn-service[vpn-id={vpn_id}]"
        vpn_nodes = vs.get("vpn-nodes", {}).get("vpn-node", [])
        for node_index, nvn in enumerate(vpn_nodes):
            node_id = nvn.get("vpn-node-id", "")
            device = _pick_device(node_index, nvn.get("site-role", ""))
            node_path = f"{vs_path}/vpn-nodes/vpn-node[vpn-node-id={node_id}]"

            # ---- R6-01 VRF + interface + IP SPLIT ----
            profiles = nvn.get("vpn-node-properties", {}).get(
                "active-vpn-instance-profiles", {}).get(
                "active-vpn-instance-profile", [])
            rd = profiles[0].get("rd", "") if profiles else ""
            rts = []
            if profiles:
                for vt in profiles[0].get("vpn-targets", {}).get("vpn-target", []):
                    rts.append({"rt": vt.get("rt"), "rt-type": vt.get("rt-type")})
            devices[device].setdefault("vrfs", {}).setdefault("vrf", []).append({
                "name": vpn_id,
                "rd": rd,
                "vpn-targets": rts,
            })
            trace.record(
                "R6-01", "#9",
                _ntw_path(node_path, "vpn-node-properties",
                          "active-vpn-instance-profiles"),
                _dev_path(device, "vrfs", f"vrf[name={vpn_id}]"),
                "SPLIT", {"rd": rd, "vpn-targets": rts},
                "G1: VRF is split to the PE device.",
            )

            # router-id -> loopback interface (R5.4-04 device side)
            router_id = _derive_router_id(node_index + 1)
            devices[device].setdefault("interfaces", {}).setdefault(
                "interface", []).append({
                    "name": "Loopback0",
                    "description": f"router-id for {vpn_id}",
                    "ipv4": [{"address": router_id, "prefix-length": 32}],
                })
            trace.record(
                "R5.4-04", "#9",
                _ntw_path(vs_path, "vpn-id"),
                _dev_path(device, "interfaces", "interface[name=Loopback0]", "ipv4"),
                "DERIVE", router_id,
                "Router id is derived to the device loopback interface.",
            )

            # ---- R6-01b interface + IP per access ----
            vnas = nvn.get("vpn-network-accesses", {}).get("vpn-network-access", [])
            for acc_index, nva in enumerate(vnas):
                acc_id = nva.get("id", "")
                acc_path = f"{node_path}/vpn-network-accesses/vpn-network-access[id={acc_id}]"
                iface_name = f"GE0/0/{acc_index + 1}"
                iface = {"name": iface_name, "description": f"access {acc_id}"}
                ip_conn = nva.get("connection", {}).get("ip-connection", {})
                ipv4_addrs = ip_conn.get("ipv4", {}).get("addresses", {}).get("address", [])
                ipv6_addrs = ip_conn.get("ipv6", {}).get("addresses", {}).get("address", [])
                if ipv4_addrs:
                    iface["ipv4"] = [
                        {"address": a["address"], "prefix-length": a["prefix-length"]}
                        for a in ipv4_addrs
                    ]
                if ipv6_addrs:
                    iface["ipv6"] = [
                        {"address": a["address"], "prefix-length": a["prefix-length"]}
                        for a in ipv6_addrs
                    ]
                devices[device].setdefault("interfaces", {}).setdefault(
                    "interface", []).append(iface)
                trace.record(
                    "R6-01", "#9",
                    _ntw_path(acc_path, "connection", "ip-connection"),
                    _dev_path(device, "interfaces", f"interface[name={iface_name}]"),
                    "SPLIT", {"ipv4": len(ipv4_addrs), "ipv6": len(ipv6_addrs)},
                    "G2/G3: interface and IP addresses are split to the PE device.",
                )

                # ---- R6-02 routing SPLIT ----
                rps = nva.get("service", {}).get("routing-protocols", {}).get(
                    "routing-protocol", [])
                for proto in rps:
                    ptype = proto.get("type", "")
                    if "bgp" in ptype:
                        bgp = proto.get("bgp", {})
                        devices[device].setdefault("bgp", {}).setdefault(
                            "neighbor", []).append({
                                "vpn": vpn_id,
                                "neighbor": bgp.get("autonomous-system"),
                                "address-family": bgp.get("address-family"),
                            })
                    elif "ospf" in ptype:
                        ospf = proto.get("ospf", {})
                        devices[device].setdefault("ospf", {}).setdefault(
                            "instance", []).append({
                                "vpn": vpn_id,
                                "area": ospf.get("area"),
                                "address-family": ospf.get("address-family"),
                            })
                    elif "static" in ptype:
                        st = proto.get("static", {})
                        devices[device].setdefault("routing", {}).setdefault(
                            "static-route", []).append({
                                "vpn": vpn_id,
                                "prefix": st.get("prefix"),
                            })
                trace.record(
                    "R6-02", "#9",
                    _ntw_path(acc_path, "service", "routing-protocols"),
                    _dev_path(device, "bgp", "neighbor"),
                    "SPLIT", [p.get("type") for p in rps],
                    "G5: routing protocols are split to device routing config.",
                )

                # ---- R6-03 policy SPLIT (ACL + QoS) ----
                class_pol = nva.get("ietf-l3vpn-ntw-ext:classification-policy", [])
                if class_pol:
                    devices[device].setdefault("acls", {}).setdefault("acl", []).append({
                        "name": f"ACL-{acc_id}",
                        "rules": [
                            {
                                "rule-id": r.get("rule-id"),
                                "match-type": (
                                    "match-flow" if "match-flow" in r
                                    else "match-application" if "match-application" in r
                                    else ""
                                ),
                            }
                            for r in class_pol
                        ],
                    })
                    trace.record(
                        "R6-03", "#9",
                        _ntw_path(acc_path, "ietf-l3vpn-ntw-ext:classification-policy"),
                        _dev_path(device, "acls", f"acl[name=ACL-{acc_id}]"),
                        "SPLIT", [r.get("rule-id") for r in class_pol],
                        "G6: classification policy is split to device ACLs.",
                    )
                qos_prof = nva.get("service", {}).get("qos", {}).get("qos-profile")
                if qos_prof:
                    devices[device].setdefault("qos", {}).setdefault(
                        "qos-profile", []).append({
                            "name": qos_prof,
                            "vpn": vpn_id,
                        })
                    trace.record(
                        "R6-03", "#9",
                        _ntw_path(acc_path, "service", "qos", "qos-profile"),
                        _dev_path(device, "qos", f"qos-profile[name={qos_prof}]"),
                        "SPLIT", qos_prof,
                        "G4: QoS profile is split to the device.",
                    )

                # ---- R6-04 security SPLIT (IPsec) ----
                sec = nva.get("service", {}).get("security", {})
                enc = sec.get("encryption", {})
                if enc.get("encryption-profile-id"):
                    devices[device].setdefault("ipsec", {}).setdefault("ike", []).append({
                        "name": f"IKE-{acc_id}",
                        "encryption-profile-id": enc["encryption-profile-id"],
                    })
                    trace.record(
                        "R6-04", "#9",
                        _ntw_path(acc_path, "service", "security", "encryption"),
                        _dev_path(device, "ipsec", f"ike[name=IKE-{acc_id}]"),
                        "SPLIT", enc["encryption-profile-id"],
                        "G9: encryption is split to device IPsec/IKE.",
                    )

                # ---- R6-05 perf-mon + schedule SPLIT (STAMP) ----
                perf = nva.get("ietf-l3vpn-ntw-ext:perf-mon")
                if perf:
                    devices[device].setdefault("stamp", {}).setdefault(
                        "session", []).append({
                            "name": f"STAMP-{acc_id}",
                            "vpn": vpn_id,
                            "interval": perf.get("interval", 60),
                            "metrics": perf.get("metrics", []),
                        })
                    trace.record(
                        "R6-05", "#9",
                        _ntw_path(acc_path, "ietf-l3vpn-ntw-ext:perf-mon"),
                        _dev_path(device, "stamp", f"session[name=STAMP-{acc_id}]"),
                        "SPLIT", perf.get("metrics", []),
                        "G8/G10: schedule and perf-mon aggregation are split to "
                        "STAMP sessions.",
                    )

            # ---- R6-04b SR policy SPLIT (underlay) ----
            if vs.get("cloud-accesses") or any(
                nva.get("ietf-l3vpn-ntw-ext:perf-mon")
                for nva in vnas
            ):
                devices[device].setdefault("sr-policies", {}).setdefault(
                    "sr-policy", []).append({
                        "name": f"SR-{vpn_id}-{node_id}",
                        "vpn": vpn_id,
                    })
                trace.record(
                    "R6-04", "#9",
                    _ntw_path(vs_path, "cloud-accesses"),
                    _dev_path(device, "sr-policies", f"sr-policy[name=SR-{vpn_id}-{node_id}]"),
                    "SPLIT", vpn_id,
                    "G11: underlay SR policy is split to the device.",
                )

    return devices


# ---------------------------------------------------------------------------
# Full pipeline
# ---------------------------------------------------------------------------

class MappingResult:
    """Result of a full mapping run."""

    def __init__(
        self,
        l3sm: Dict[str, Any],
        l3nm: Dict[str, Any],
        devices: Dict[str, Any],
        trace: TraceRecorder,
    ) -> None:
        self.l3sm = l3sm
        self.l3nm = l3nm
        self.devices = devices
        self.trace = trace

    def to_dict(self) -> Dict[str, Any]:
        return {
            "l3sm": self.l3sm,
            "l3nm": self.l3nm,
            "devices": self.devices,
            "trace": self.trace.to_dict_list(),
        }


def run_mapping(l3sm: Dict[str, Any]) -> MappingResult:
    """Run the full L3SM -> L3NM -> device mapping pipeline."""
    trace = TraceRecorder()
    l3nm = map_l3sm_to_l3nm(l3sm, trace)
    devices = map_l3nm_to_device(l3nm, trace)
    return MappingResult(l3sm, l3nm, devices, trace)