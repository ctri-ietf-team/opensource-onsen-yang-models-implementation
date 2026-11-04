"""CLI entry point: run the mapping engine over test cases and report
lossless metrics (TC-MAP-001/002/003) plus yangson validation."""

from __future__ import annotations

import json
import os
import sys
from typing import Any, Dict, List

from yangson import DataModel

from .mapper import run_mapping
from .metrics import compute_all
from .rules import RULES

YANG_DIR = "yang"
LIBRARY = "yang/yang-library.json"

# ---------------------------------------------------------------------------
# Test case instances (RFC 7951 style, module-prefixed keys)
# ---------------------------------------------------------------------------

L3SM_TC: Dict[str, Any] = {
    "ietf-l3vpn-svc:l3vpn-svc": {
        "vpn-profiles": {
            "valid-provider-identifiers": {
                "cloud-identifier": [{"id": "CLOUD-1"}],
                "qos-profile-identifier": [{"id": "QOS-PROF-1"}],
            },
            "ietf-l3vpn-svc-dynamic-ext:maximum-adjustment-profiles": {
                "maximum-adjustment-profile": [
                    {"id": "MAP-1", "max-bandwidth": "1000000000", "max-latency": 50}
                ]
            },
            "ietf-l3vpn-svc-dynamic-ext:slo-sle-profiles": {
                "slo-sle-profile": [
                    {"id": "SLO-1", "latency": 20, "jitter": 5, "packet-loss": 10}
                ]
            },
        },
        "vpn-services": {
            "vpn-service": [
                {
                    "vpn-id": "VPN1",
                    "vpn-name": "Enterprise VPN",
                    "vpn-description": "Primary enterprise VPN",
                    "customer-name": "ACME Corp",
                    "vpn-type": "ietf-l3vpn-svc:l3vpn",
                    "vpn-service-topology": "ietf-l3vpn-svc:any-to-any",
                    "cloud-accesses": {
                        "cloud-access": [
                            {
                                "cloud-access-id": "CA1",
                                "cloud-provider": "alibaba",
                                "cloud-identifier": "CLOUD-1",
                            }
                        ]
                    },
                    "sites": {
                        "site": [
                            {
                                "site-id": "SITE1",
                                "site-name": "HQ",
                                "site-role": "ietf-l3vpn-svc:hub-role",
                                "locations": {
                                    "location": [
                                        {
                                            "location-id": "LOC1",
                                            "address": "Beijing",
                                            "latitude": "39.9",
                                            "longitude": "116.4",
                                        }
                                    ]
                                },
                                "devices": {
                                    "device": [
                                        {"device-id": "CE1", "location": "LOC1"}
                                    ]
                                },
                                "management": "ietf-l3vpn-svc:provider-managed",
                                "site-diversity": {
                                    "diversity-groups": {
                                        "group": [{"group-id": "DG1"}]
                                    }
                                },
                                "ietf-l3vpn-svc-dynamic-ext:temporary-connection-indicator": False,
                                "ietf-l3vpn-svc-dynamic-ext:service": {
                                    "qos": {
                                        "qos-profile": {"slo-sle-profile": "SLO-1"}
                                    }
                                },
                                "site-network-accesses": {
                                    "site-network-access": [
                                        {
                                            "site-network-access-id": "ACC1",
                                            "site-network-access-type": "ietf-l3vpn-svc:point-to-point",
                                            "ip-connection": {
                                                "ipv4": {
                                                    "addresses": {
                                                        "address": [
                                                            {
                                                                "address-id": "a1",
                                                                "address": "10.0.0.1",
                                                                "prefix-length": 24,
                                                            }
                                                        ]
                                                    }
                                                },
                                                "ipv6": {
                                                    "addresses": {
                                                        "address": [
                                                            {
                                                                "address-id": "a6",
                                                                "address": "2001:db8::1",
                                                                "prefix-length": 64,
                                                            }
                                                        ]
                                                    }
                                                },
                                            },
                                            "routing-protocols": {
                                                "routing-protocol": [
                                                    {
                                                        "type": "ietf-l3vpn-svc:bgp",
                                                        "bgp": {
                                                            "autonomous-system": 65000,
                                                            "address-family": "ietf-l3vpn-svc:ipv4",
                                                        },
                                                    },
                                                    {
                                                        "type": "ietf-l3vpn-svc:static",
                                                        "static": {
                                                            "prefix": "192.168.1.0/24"
                                                        },
                                                    },
                                                ]
                                            },
                                            "service": {
                                                "svc-input-bandwidth": "100000000",
                                                "svc-output-bandwidth": "200000000",
                                                "mtu": 1500,
                                                "qos": {
                                                    "qos-profile": {
                                                        "qos-profile-id": "QOS-PROF-1",
                                                        "custom": {
                                                            "class": [
                                                                {
                                                                    "class-id": "C1",
                                                                    "rate": "50000000",
                                                                    "isolation": ["C2"],
                                                                }
                                                            ]
                                                        },
                                                    }
                                                },
                                                "security": {
                                                    "encryption": {
                                                        "encryption-profile-id": "EP1"
                                                    }
                                                },
                                            },
                                            "ietf-l3vpn-svc-dynamic-ext:service": {
                                                "dynamic-l3vpn": {
                                                    "dynamic-l3vpn-id": "DL3VPN-1",
                                                    "adjustment-mode": "automatic",
                                                },
                                                "classification-policy": [
                                                    {
                                                        "rule-id": "R1",
                                                        "match-flow": {"dscp": 46},
                                                        "target-class-id": "EF",
                                                        "target-sites": ["SITE2"],
                                                    }
                                                ],
                                                "qos": {
                                                    "qos-profile": {
                                                        "slo-sle-profile": "SLO-1"
                                                    }
                                                },
                                            },
                                            "ietf-l3vpn-svc-dynamic-ext:ip-connection-security": {
                                                "security-policy-id": "SP1",
                                                "allowed-ipv4-prefixes": ["10.0.0.0/8"],
                                            },
                                        }
                                    ]
                                },
                            },
                            {
                                "site-id": "SITE2",
                                "site-name": "Branch",
                                "site-role": "ietf-l3vpn-svc:spoke-role",
                                "site-network-accesses": {
                                    "site-network-access": [
                                        {
                                            "site-network-access-id": "ACC2",
                                            "site-network-access-type": "ietf-l3vpn-svc:multipoint",
                                            "ip-connection": {
                                                "ipv4": {
                                                    "addresses": {
                                                        "address": [
                                                            {
                                                                "address-id": "a1",
                                                                "address": "10.0.1.1",
                                                                "prefix-length": 24,
                                                            }
                                                        ]
                                                    }
                                                }
                                            },
                                            "routing-protocols": {
                                                "routing-protocol": [
                                                    {
                                                        "type": "ietf-l3vpn-svc:ospf",
                                                        "ospf": {
                                                            "address-family": "ietf-l3vpn-svc:ipv4",
                                                            "area": "0.0.0.0",
                                                        },
                                                    }
                                                ]
                                            },
                                            "service": {
                                                "svc-input-bandwidth": "50000000",
                                                "svc-output-bandwidth": "100000000",
                                                "mtu": 1400,
                                            },
                                        }
                                    ]
                                },
                            },
                        ]
                    },
                }
            ]
        },
    }
}


def validate_instance(dm: DataModel, instance: Dict[str, Any]) -> List[str]:
    """Validate an instance against the YANG data model; return errors."""
    try:
        dm.from_raw(instance)
        return []
    except Exception as e:  # noqa: BLE001 - report any validation error
        return [f"{type(e).__name__}: {e}"]


def run_tc(
    dm: DataModel, name: str, l3sm: Dict[str, Any]
) -> Dict[str, Any]:
    """Run one test case and return its report."""
    result = run_mapping(l3sm)
    metrics = compute_all(l3sm, result.l3nm, result.trace.to_dict_list())
    l3nm_errors = validate_instance(dm, result.l3nm)

    passed = True
    checks: Dict[str, bool] = {}
    if name == "TC-MAP-001":
        checks["coverage == 100%"] = metrics["coverage"]["rate"] == 1.0
    elif name == "TC-MAP-002":
        checks["roundtrip diff == 0"] = metrics["roundtrip_diff"]["diff_count"] == 0
    elif name == "TC-MAP-003":
        checks["traceability == 100%"] = metrics["traceability"]["rate"] == 1.0
    checks["L3NM valid"] = len(l3nm_errors) == 0
    passed = all(checks.values())

    return {
        "tc": name,
        "passed": passed,
        "checks": checks,
        "metrics": metrics,
        "l3nm_errors": l3nm_errors,
        "trace_count": len(result.trace),
        "l3nm": result.l3nm,
        "devices": result.devices,
        "trace": result.trace.to_dict_list(),
    }


def main() -> int:
    dm = DataModel.from_file(LIBRARY, [YANG_DIR])
    reports = []
    for tc_name in ("TC-MAP-001", "TC-MAP-002", "TC-MAP-003"):
        reports.append(run_tc(dm, tc_name, L3SM_TC))

    summary = {
        "engine": "l3vpn-mapping-engine",
        "rules": len(RULES),
        "test_cases": [
            {
                "tc": r["tc"],
                "passed": r["passed"],
                "checks": r["checks"],
                "metrics": {
                    "coverage_rate": r["metrics"]["coverage"]["rate"],
                    "roundtrip_diff": r["metrics"]["roundtrip_diff"]["diff_count"],
                    "traceability_rate": r["metrics"]["traceability"]["rate"],
                },
                "trace_count": r["trace_count"],
                "l3nm_valid": len(r["l3nm_errors"]) == 0,
            }
            for r in reports
        ],
        "all_passed": all(r["passed"] for r in reports),
    }

    print(json.dumps(summary, ensure_ascii=False, indent=2))

    # detailed report for the last (fullest) run
    os.makedirs(".tmp", exist_ok=True)
    with open(".tmp/mapping-report.json", "w", encoding="utf-8") as f:
        json.dump(reports[-1], f, ensure_ascii=False, indent=2)
    print("\nDetailed report: .tmp/mapping-report.json")

    return 0 if summary["all_passed"] else 1


if __name__ == "__main__":
    sys.exit(main())