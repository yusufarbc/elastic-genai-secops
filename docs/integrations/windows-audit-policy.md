[← Back to README](../../README.md)

# Windows audit and PowerShell logging policy

Windows logs very little security detail by default. This Group Policy makes servers (domain
controllers and critical servers first) record what the detection rules in
`content/detection-rules` and the triage pipeline need. Apply it before rolling out the collectors
([windows-endpoints.md](windows-endpoints.md)).

## 1. Create the GPO

1. On a domain controller open **Group Policy Management** (`gpmc.msc`).
2. Right-click **Group Policy Objects** → **New** → `ESM-Server-Audit-Policy`.
3. Link it to the OUs that hold your servers. For domain controllers, link a separate GPO to the
   Domain Controllers OU above the *Default Domain Controllers Policy* instead of editing the default.

## 2. Advanced audit policy

**Computer Configuration → Policies → Windows Settings → Security Settings → Advanced Audit Policy
Configuration → System Audit Policies**

| Category | Subcategory | Setting | Why | Event IDs |
| --- | --- | --- | --- | --- |
| Account Logon (DCs) | Kerberos Authentication Service | Success, Failure | Kerberos abuse (golden/silver tickets, roasting) | 4768, 4771 |
| Account Logon (DCs) | Credential Validation | Success, Failure | NTLM password guessing | 4776 |
| Logon/Logoff | Logon | Success, Failure | Who logged on, how (RDP, network, console) | 4624, 4625 |
| Logon/Logoff | Special Logon | Success | Privileged logons | 4672 |
| Account Management | User Account Management | Success, Failure | Created, changed, reset, locked accounts | 4720–4740 |
| Account Management | Security Group Management | Success, Failure | Additions to privileged groups | 4728, 4732, 4756 |
| Detailed Tracking | Process Creation | Success | Process starts (backup for Sysmon) | 4688 |
| Policy Change | Audit Policy Change | Success, Failure | Attackers disabling auditing | 4719 |
| System | Security State Change | Success, Failure | Clock changes, shutdowns | 4608, 4616 |
| Object Access | Other Object Access Events | Success, Failure | Scheduled task creation | 4698–4702 |
| System | Security System Extension | Success | Service installation | 4697 |

Also set **Computer Configuration → Policies → Windows Settings → Security Settings → Local
Policies → Security Options → Audit: Force audit policy subcategory settings to override audit
policy category settings** = Enabled, so the advanced settings win over legacy ones.

## 3. Command lines in process events

**Computer Configuration → Policies → Administrative Templates → System → Audit Process Creation →
Include command line in process creation events** = Enabled (adds the command line to 4688).

## 4. PowerShell logging

**Computer Configuration → Policies → Administrative Templates → Windows Components → Windows
PowerShell**

| Setting | Value | Result |
| --- | --- | --- |
| Turn on PowerShell Script Block Logging | Enabled | De-obfuscated script blocks, event 4104 (rules WIN-010, WIN-013) |
| Turn on Module Logging | Enabled, module names `*` | Pipeline execution details, event 4103 |

Script block logs can contain secrets typed on the command line. They are stored in Elasticsearch
only; the triage pipeline never forwards command lines or script text to the LLM.

## 5. Apply and check

```cmd
gpupdate /force
auditpol /get /category:*
```

`auditpol` should show *Success and Failure* for the subcategories above. Run
`Write-Host "audit test"` in PowerShell and look for event 4104 under **Applications and Services
Logs → Microsoft → Windows → PowerShell → Operational**.

Winlogbeat already collects the Security, System and PowerShell channels
(`integrations/sources/windows/winlogbeat.yml`); no extra configuration is needed.

## 6. DNS server logging (optional, domain controllers)

Sysmon event 22 covers DNS queries on endpoints. To see queries resolved by the DNS server itself,
enable the **Microsoft-Windows-DNSServer/Analytical** channel (Event Viewer → View → Show Analytic
and Debug Logs → enable the log) and add it to `winlogbeat.yml` on the DNS servers:

```yaml
  - name: Microsoft-Windows-DNSServer/Analytical
    ignore_missing_channel: true
```

The analytical log is high volume; enable it only where you need C2 detection on DNS.

## Summary: where each signal comes from

| Signal | Source | Configured by |
| --- | --- | --- |
| Logon success and failure | Security log | This audit policy |
| Malicious scripts | PowerShell/Operational (4104) | This PowerShell policy |
| Processes, network, registry, LSASS access | Sysmon | `integrations/sources/windows/sysmon/sysmon.xml` |
| DNS resolution | Sysmon 22, DNS analytical log | Sysmon, section 6 |
