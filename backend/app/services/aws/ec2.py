"""
EC2 collector.

Read-only checks implemented:
  - Security groups open to 0.0.0.0/0 (or ::/0) on sensitive ports
  - Unused security groups (not attached to any ENI)
  - Instances with public IPs
  - Unencrypted EBS volumes
  - Instances not enforcing IMDSv2
"""

from __future__ import annotations

from botocore.client import BaseClient

from app.models.aws_account import AwsAccount
from app.models.enums import AwsService, Severity
from app.services.aws.base import CollectorResult, RawFinding
from app.services.aws.client_factory import get_client

_SENSITIVE_PORTS = {22: "SSH", 3389: "RDP", 3306: "MySQL", 5432: "PostgreSQL", 27017: "MongoDB", 6379: "Redis"}


def _check_security_groups(ec2: BaseClient, findings: list[RawFinding]) -> int:
    scanned = 0
    used_group_ids: set[str] = set()
    for eni in ec2.describe_network_interfaces()["NetworkInterfaces"]:
        for group in eni.get("Groups", []):
            used_group_ids.add(group["GroupId"])

    for sg in ec2.describe_security_groups()["SecurityGroups"]:
        scanned += 1
        group_id = sg["GroupId"]
        group_name = sg.get("GroupName", group_id)

        for perm in sg.get("IpPermissions", []):
            open_ranges = [r["CidrIp"] for r in perm.get("IpRanges", []) if r.get("CidrIp") in ("0.0.0.0/0",)]
            open_ranges += [r["CidrIpv6"] for r in perm.get("Ipv6Ranges", []) if r.get("CidrIpv6") in ("::/0",)]
            if not open_ranges:
                continue

            from_port = perm.get("FromPort")
            to_port = perm.get("ToPort")
            is_all_traffic = perm.get("IpProtocol") == "-1"
            matched_sensitive = None
            if is_all_traffic:
                matched_sensitive = "ALL PORTS"
            elif from_port is not None and to_port is not None:
                for port, name in _SENSITIVE_PORTS.items():
                    if from_port <= port <= to_port:
                        matched_sensitive = f"{name} ({port})"
                        break

            severity = Severity.CRITICAL if (is_all_traffic or matched_sensitive) else Severity.MEDIUM
            port_desc = "all ports/protocols" if is_all_traffic else f"port(s) {from_port}-{to_port}"
            findings.append(
                RawFinding(
                    service=AwsService.EC2,
                    title=f"Security group '{group_name}' open to the internet",
                    description=(
                        f"Security group {group_name} ({group_id}) allows inbound traffic "
                        f"from {', '.join(open_ranges)} on {port_desc}"
                        + (f", including {matched_sensitive}" if matched_sensitive and not is_all_traffic else "")
                        + "."
                    ),
                    severity_hint=severity,
                    resource_id=group_id,
                    cis_control="5.2 / 5.3",
                    nist_control="SC-7",
                    mitre_attack="T1190 (Exploit Public-Facing Application)",
                    remediation="Restrict the security group rule to specific trusted CIDR ranges instead of 0.0.0.0/0.",
                    estimated_remediation_time="10 min",
                )
            )

        if group_id not in used_group_ids and group_name != "default":
            findings.append(
                RawFinding(
                    service=AwsService.EC2,
                    title=f"Unused security group '{group_name}'",
                    description=f"Security group {group_name} ({group_id}) is not attached to any network interface.",
                    severity_hint=Severity.LOW,
                    resource_id=group_id,
                    remediation="Delete the unused security group to reduce attack surface and configuration drift.",
                    estimated_remediation_time="5 min",
                )
            )
    return scanned


def _check_instances(ec2: BaseClient, findings: list[RawFinding]) -> int:
    scanned = 0
    paginator = ec2.get_paginator("describe_instances")
    for page in paginator.paginate():
        for reservation in page["Reservations"]:
            for instance in reservation["Instances"]:
                if instance["State"]["Name"] == "terminated":
                    continue
                scanned += 1
                instance_id = instance["InstanceId"]

                if instance.get("PublicIpAddress"):
                    findings.append(
                        RawFinding(
                            service=AwsService.EC2,
                            title=f"EC2 instance '{instance_id}' has a public IP",
                            description=f"Instance {instance_id} is assigned public IP {instance['PublicIpAddress']}.",
                            severity_hint=Severity.MEDIUM,
                            resource_id=instance_id,
                            cis_control="5.1",
                            nist_control="SC-7",
                            remediation="Move the instance behind a load balancer/NAT and remove the direct public IP if not required.",
                            estimated_remediation_time="15 min",
                        )
                    )

                metadata_opts = instance.get("MetadataOptions", {})
                if metadata_opts.get("HttpTokens") != "required":
                    findings.append(
                        RawFinding(
                            service=AwsService.EC2,
                            title=f"EC2 instance '{instance_id}' does not enforce IMDSv2",
                            description=f"Instance {instance_id} allows IMDSv1, which is more susceptible to SSRF-based credential theft.",
                            severity_hint=Severity.MEDIUM,
                            resource_id=instance_id,
                            mitre_attack="T1552.005 (Cloud Instance Metadata API)",
                            remediation="Set HttpTokens=required on the instance metadata options to enforce IMDSv2.",
                            estimated_remediation_time="5 min",
                        )
                    )
    return scanned


def _check_ebs_encryption(ec2: BaseClient, findings: list[RawFinding]) -> int:
    scanned = 0
    paginator = ec2.get_paginator("describe_volumes")
    for page in paginator.paginate():
        for volume in page["Volumes"]:
            scanned += 1
            if not volume.get("Encrypted"):
                findings.append(
                    RawFinding(
                        service=AwsService.EC2,
                        title=f"EBS volume '{volume['VolumeId']}' is not encrypted",
                        description=f"Volume {volume['VolumeId']} ({volume.get('Size')} GiB) has no encryption at rest.",
                        severity_hint=Severity.HIGH,
                        resource_id=volume["VolumeId"],
                        cis_control="2.2.1",
                        nist_control="SC-28",
                        remediation="Enable EBS encryption by default at the account level and re-create the volume from an encrypted snapshot.",
                        estimated_remediation_time="30 min",
                    )
                )
    return scanned


def collect(account: AwsAccount) -> CollectorResult:
    findings: list[RawFinding] = []
    scanned = 0
    try:
        with get_client(account, "ec2") as ec2:
            scanned += _check_security_groups(ec2, findings)
            scanned += _check_instances(ec2, findings)
            scanned += _check_ebs_encryption(ec2, findings)
        return CollectorResult(service=AwsService.EC2, findings=findings, resources_scanned=scanned)
    except Exception as exc:  # noqa: BLE001
        return CollectorResult(service=AwsService.EC2, findings=findings, resources_scanned=scanned, error=str(exc))
