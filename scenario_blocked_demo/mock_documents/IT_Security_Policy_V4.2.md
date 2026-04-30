# IT Security Policy v4.2

**Document ID:** ISP-001
**Version:** 4.2
**Effective Date:** April 4, 2026
**Classification:** INTERNAL USE
**Document Owner:** K. Whitfield — Chief Information Security Officer
**Approved By:** Executive Leadership Team
**Review Cycle:** Annual (next review: April 4, 2027)
**Distribution:** All Lichen employees and contractors

> CONFIDENTIALITY NOTICE: This document contains proprietary and confidential information belonging to Lichen Manufacturing, Inc. Unauthorized disclosure, reproduction, or distribution is strictly prohibited.

---

## Document Control

| Version | Date | Author | Description of Change |
|---------|------|--------|-----------------------|
| 4.0 | 2023-01-15 | K. Whitfield, CISO | Major revision: added cloud and SaaS controls |
| 4.1 | 2023-09-08 | K. Whitfield, CISO | Section 12 expanded — third-party security requirements updated post-audit finding |
| 4.2 | 2024-03-01 | K. Whitfield, CISO | Added ERP integration tier classification; updated DPA trigger alignment language |

---

## 1. Purpose

This Information Security Policy ("Policy") establishes the framework by which Lichen Manufacturing, Inc. ("Lichen" or "the Company") protects the confidentiality, integrity, and availability of its information assets, systems, and data. The Policy reflects the Company's commitment to maintaining a secure operating environment consistent with applicable legal and regulatory obligations, contractual commitments, and industry best practices.

This Policy applies in conjunction with supporting standards, procedures, and guidelines published by the IT Security Team. In the event of conflict, this Policy takes precedence unless a specific regulatory requirement mandates otherwise.

---

## 2. Scope

This Policy applies to:

- All Lichen employees, officers, and directors
- All contractors, consultants, temporary workers, and agents operating on behalf of Lichen Manufacturing
- All third-party vendors and suppliers who access, process, store, or transmit Lichen information assets
- All information assets owned, leased, or managed by Lichen Manufacturing, regardless of location or form
- All Lichen systems, networks, and infrastructure, including cloud-hosted environments and third-party SaaS platforms

Geographic scope is global. All Lichen facilities, including manufacturing plants, distribution centers, and corporate offices, fall within scope. Subsidiaries operating under the Lichen Manufacturing parent entity are subject to this Policy unless a separate, equivalent policy has been approved by the CISO.

---

## 3. Policy Statement

Lichen Manufacturing is committed to protecting its information assets against unauthorized access, disclosure, alteration, and destruction. The Company will:

**3.1** Implement and maintain controls proportionate to the classification level and risk profile of each information asset.

**3.2** Comply with all applicable legal, regulatory, and contractual information security obligations, including but not limited to GDPR, CCPA, SOX data-integrity provisions, and sector-specific requirements applicable to manufacturing operations.

**3.3** Ensure that all personnel with access to Lichen information assets receive appropriate security awareness training commensurate with their role.

**3.4** Apply the principle of least privilege to all access provisioning decisions.

**3.5** Maintain an incident response capability sufficient to detect, contain, eradicate, and recover from security incidents in a timely manner.

**3.6** Subject all third-party entities to security requirements appropriate to the sensitivity of the information they will access or process.

**3.7** Review and update this Policy at least annually, and in response to material changes in the threat landscape, regulatory environment, or business operations.

---

## 4. Roles and Responsibilities

| Role | Responsible Party | Key Obligations |
|------|-------------------|----------------|
| Chief Information Security Officer (CISO) | K. Whitfield | Policy ownership, annual review, exception approval, board reporting |
| IT Security Team | IT Department | Control implementation, vulnerability management, access review, incident response |
| Department Heads / Business Owners | All Departments | Asset classification within their domain, ensuring staff compliance, escalating incidents |
| Procurement / Vendor Management | Procurement Dept. | Enforce §12 requirements during vendor selection; collect and validate security attestations |
| Legal & Compliance | General Counsel Office | DPA trigger assessment, regulatory mapping, contract clause enforcement |
| All Employees & Contractors | Individual | Acceptable use compliance, incident reporting, completion of mandatory security training |

---

## 5. Information Asset Classification

All Lichen information assets must be classified according to the following framework. Classification determines applicable handling, storage, transmission, and disposal requirements.

| Classification | Definition | Examples |
|----------------|-----------|---------|
| **RESTRICTED** | Highest sensitivity. Unauthorized disclosure would cause severe financial, legal, or reputational harm. | ERP credentials, DPA-regulated personal data, M&A information, CISO-designated systems |
| **CONFIDENTIAL** | Significant sensitivity. Disclosure would cause material harm to Lichen Manufacturing or third parties. | Vendor contracts, financial forecasts, internal audit reports, employee PII |
| **INTERNAL USE** | Low sensitivity. Authorized employees only. Disclosure causes limited harm. | Internal procedures, project plans, non-sensitive emails, policy documents |
| **PUBLIC** | No restriction. Approved for external distribution. | Marketing materials, public job postings, published press releases |

**5.1** Asset owners are responsible for assigning and maintaining the classification of assets within their domain.

**5.2** When aggregated data would result in a higher sensitivity level than individual elements, the higher classification applies to the aggregate.

**5.3** Default classification is INTERNAL USE where no explicit classification has been assigned.

---

## 6. Access Control

### 6.1 Access Provisioning

**6.1.1** Access to Lichen systems and data must be requested through the IT Service Management platform and approved by the relevant asset owner and the requesting employee's line manager.

**6.1.2** Access rights must be provisioned on a least-privilege basis. Elevated or privileged access requires documented business justification and CISO review.

**6.1.3** All provisioned access must be reviewed quarterly by system owners. Dormant accounts (no activity for 60 days) must be disabled pending review.

### 6.2 Authentication

**6.2.1** Multi-factor authentication (MFA) is mandatory for all user accounts accessing Lichen systems, including remote access, cloud services, VPN, and administrative consoles.

**6.2.2** Password requirements: minimum 14 characters; combination of uppercase, lowercase, numeric, and special characters; password history of 12; maximum age of 90 days.

**6.2.3** Service accounts and API credentials must not use personal user credentials. Secrets must be stored in the approved secrets management solution (HashiCorp Vault or equivalent).

### 6.3 Third-Party Access

**6.3.1** Third-party access must be provisioned through the standard access request process with explicit CISO awareness for RESTRICTED data scope.

**6.3.2** Third-party accounts are subject to the same MFA requirements as internal accounts. Exceptions require documented compensating controls and CISO approval; see §16.

**6.3.3** All third-party access must be time-bounded. Access must be reviewed at each contract renewal and revoked within one business day of contract termination.

---

## 7. Acceptable Use

**7.1** Lichen information assets are provided for business purposes. Incidental personal use is permitted where it does not interfere with business operations, consume material resources, or violate any other provision of this Policy.

**7.2** Prohibited activities include but are not limited to: unauthorized data exfiltration; installation of unlicensed or unapproved software; use of Lichen systems to access, store, or transmit illegal content; deliberate circumvention of security controls; and sharing of credentials.

**7.3** Employees must not connect unapproved personal devices to the corporate network or to any Lichen endpoint. Approved BYOD configurations are governed by the Mobile Device Management Standard.

**7.4** Use of generative AI tools and large language model services must comply with the AI Acceptable Use Standard (AUS-003). Processing of RESTRICTED or CONFIDENTIAL data through unapproved external AI services is prohibited.

---

## 8. Data Protection and Privacy

**8.1** Lichen processes personal data as a controller and, in some contexts, as a processor. All personal data processing activities must be conducted in accordance with the Lichen Data Protection Policy (DPP-001) and applicable privacy regulations.

**8.2** Personal data subject to heightened regulatory requirements (including GDPR special-category data, CCPA sensitive personal information, and payment card data under PCI DSS) must be identified, inventoried, and afforded RESTRICTED classification as a minimum.

**8.3** Data minimization: systems and processes must be designed to collect, retain, and process only the minimum personal data necessary to fulfill the stated business purpose.

**8.4** Data subject requests (access, deletion, portability, correction) must be routed to the Legal & Compliance team and fulfilled within regulatory timeframes.

**8.5** Transfer of personal data outside the European Economic Area or other regulated jurisdictions requires a valid transfer mechanism as determined by Legal & Compliance prior to transfer.

---

## 9. Network Security

**9.1** All data in transit must be protected using TLS 1.2 at minimum. TLS 1.3 is preferred. TLS 1.0 and 1.1 are deprecated and prohibited on all Lichen-controlled infrastructure.

**9.2** Network segmentation: production, development, and test environments must be logically separated. Vendor and guest network segments must be isolated from internal corporate segments.

**9.3** Remote access to Lichen internal systems must use the approved VPN solution with MFA. Split-tunneling configurations require CISO approval.

**9.4** All internet-facing systems must be protected by web application firewalls (WAF) and intrusion detection/prevention systems. Security events must be forwarded to the SIEM in real time.

**9.5** Wireless networks: corporate Wi-Fi uses WPA3-Enterprise with certificate-based authentication. Guest Wi-Fi is isolated and subject to content filtering. Rogue access point detection is continuously monitored.

---

## 10. Cryptography Standards

| Use Case | Required Standard | Notes |
|----------|------------------|-------|
| Data at rest — RESTRICTED assets | AES-256 | Full-disk or volume-level encryption mandatory on all endpoints and servers handling RESTRICTED data |
| Data at rest — CONFIDENTIAL assets | AES-128 minimum (AES-256 preferred) | Database-level or file-level encryption acceptable |
| Data in transit — all classifications | TLS 1.2 minimum (TLS 1.3 preferred) | TLS 1.0 and 1.1 are prohibited. Self-signed certificates prohibited for production systems. |
| Email transmission — RESTRICTED | S/MIME or PGP encryption; TLS-enforced relay | Unencrypted transmission of RESTRICTED data via email is prohibited |
| Vendor data exchange — all tiers | TLS 1.2+ in transit; AES-256 at rest for stored transfers | Vendor must provide encryption confirmation prior to first data exchange |
| Password / secret storage | bcrypt, scrypt, or Argon2 (salted) | MD5 and SHA-1 are prohibited for credential hashing |

**10.1** Cryptographic keys must be managed through the approved key management system. Key rotation schedules: symmetric keys annually; TLS certificates annually (90-day certificates acceptable for automated renewal environments).

**10.2** Deprecated algorithms (DES, 3DES, RC4, MD5, SHA-1) are prohibited in all new implementations and must be removed from existing systems on a risk-prioritized remediation schedule approved by the CISO.

---

## 11. Physical and Environmental Security

**11.1** Access to data centers, server rooms, and secure areas must be controlled by electronic access systems with audit logging. Visitor access requires escort by an authorized employee.

**11.2** Clear desk and clear screen policies are mandatory in all Lichen facilities. Workstations must lock automatically after 10 minutes of inactivity.

**11.3** Equipment containing Lichen data must be securely decommissioned using NIST SP 800-88 media sanitization guidelines before disposal, repurposing, or return to vendor.

**11.4** Physical security events (tailgating, unauthorized access attempts, loss of access cards) must be reported to IT Security and Physical Security within 24 hours.

---

## 12. Third-Party and Supplier Security

This section governs the security requirements applicable to all third parties that access, process, store, or transmit Lichen information assets, or that connect to Lichen systems in any capacity. Compliance with this section is a contractual requirement and must be verified prior to contract execution and annually thereafter.

### 12.1 Pre-Engagement Requirements

**12.1.1** All prospective vendors with access to CONFIDENTIAL or RESTRICTED information must complete the Lichen Vendor Security Questionnaire (VSQ) prior to contract execution. Procurement is responsible for ensuring questionnaire submission and routing completed questionnaires to IT Security for review.

**12.1.2** IT Security must review and approve the VSQ response before Procurement may issue a purchase order or execute a contract. Review must be documented in the vendor onboarding record.

**12.1.3** Vendors handling RESTRICTED data must provide a valid SOC 2 Type II report or ISO 27001 certification dated within the preceding 12 months. Exceptions require CISO written approval.

**12.1.4** Where a non-disclosure agreement (NDA) is required by Lichen's data classification or by the nature of the information to be shared, the NDA must be fully executed prior to the disclosure of any CONFIDENTIAL or RESTRICTED information. Procurement must confirm NDA status in the onboarding record. **Onboarding may not proceed to the information-exchange phase until NDA execution is confirmed.**

### 12.2 ERP System Integration Requirements

Vendors that will integrate with or exchange data with Lichen's enterprise resource planning system (SAP S/4HANA, "the ERP") are subject to the following tier classification. The applicable tier determines the approval path and technical security requirements.

| Integration Tier | Definition | Approval Required | Additional Requirements |
|-----------------|-----------|------------------|------------------------|
| **Tier 1 — Direct** | Vendor system establishes a persistent authenticated session or API connection directly to Lichen ERP (SAP S/4HANA). | CISO + CIO written approval prior to contract execution | Mandatory penetration test; SOC 2 Type II required; quarterly access review |
| **Tier 2 — Mediated** | Vendor system exchanges data with Lichen ERP via an approved middleware layer or integration platform (e.g., MuleSoft). Vendor does not hold ERP credentials. | CISO approval; Procurement sign-off | SOC 2 Type II or equivalent required; data-handling agreement must define field-level scope |
| **Tier 3 — Indirect / File-Based** | Vendor receives or transmits structured data exports (CSV, XML, EDI) that are subsequently imported into ERP by Lichen personnel. No system-to-system authentication involved. | Standard vendor approval process | Data classification of export fields required; encryption-in-transit required |
| **Unclassified / Pending Review** | Integration pattern does not clearly fit Tier 1, 2, or 3 as described. Vendor has described data flow in terms that are ambiguous with respect to ERP credential handling or middleware involvement. | BLOCKED — integration cannot proceed until CISO formally assigns a tier | Vendor must provide architecture diagram and data-flow documentation within 10 business days of request. Onboarding status: PROVISIONAL pending tier determination. |

**12.2.1** Tier classification must be formally documented in the vendor onboarding record by the IT Security Team prior to contract execution. Procurement must not represent an integration tier to the vendor without IT Security confirmation.

**12.2.2** A vendor whose integration description does not clearly satisfy the criteria of Tier 1, 2, or 3 must be treated as "Unclassified / Pending Review". Onboarding status must be set to PROVISIONAL and the vendor notified that the integration cannot proceed until tier assignment is complete.

**12.2.3** Tier assignment may not be changed after contract execution without CISO approval and a corresponding contract amendment.

### 12.3 Ongoing Obligations

**12.3.1** Vendors must notify Lichen IT Security within 24 hours of discovering any security incident that may affect Lichen data or systems.

**12.3.2** Vendor security attestations (SOC 2, ISO 27001, or equivalent) must be renewed annually. Lapsed attestations trigger a review by IT Security and may result in suspension of data access pending remediation.

**12.3.3** Lichen reserves the right to conduct security assessments of vendors handling RESTRICTED data, including questionnaire reviews, document requests, and on-site audits with reasonable notice.

**12.3.4** Sub-processors: vendors must disclose any sub-processors that will handle Lichen data and obtain Lichen approval before engaging a new sub-processor. Sub-processors are subject to equivalent security requirements.

---

## 13. Incident Management and Response

**13.1** All actual or suspected security incidents must be reported to IT Security immediately via the Security Incident Hotline (+1-800-OPT-SECU) or the SIEM ticketing portal. Employees must not attempt independent remediation of suspected incidents.

**13.2** IT Security will classify incidents by severity (Critical / High / Medium / Low) within two hours of notification. Critical and High incidents trigger the Incident Response Plan (IRP-001) and require notification to the CISO within one hour.

**13.3** Regulatory notification obligations (e.g., GDPR 72-hour breach notification) are the responsibility of Legal & Compliance in coordination with IT Security. IT Security must provide Legal & Compliance with a preliminary incident assessment within four hours of a breach determination.

**13.4** Post-incident reviews are mandatory for all Critical and High incidents. Findings and remediation actions must be documented and reviewed by the CISO within 30 days of incident closure.

---

## 14. Business Continuity and Disaster Recovery

**14.1** Critical information systems must have documented recovery time objectives (RTO) and recovery point objectives (RPO) approved by the relevant business owner and IT Security.

**14.2** Backup procedures must be implemented for all CONFIDENTIAL and RESTRICTED data systems. Backup integrity must be tested quarterly. Off-site or cloud backup replication is required for systems with RTO under 4 hours.

**14.3** Business continuity plans must address cybersecurity incident scenarios, including ransomware and system compromise. BCP testing must include at least one tabletop exercise per year incorporating a security incident scenario.

---

## 15. Compliance and Audit

**15.1** Compliance with this Policy is subject to periodic internal audit. IT Security conducts an annual policy compliance review and reports findings to the Executive Leadership Team.

**15.2** Non-compliance identified through audit, incident investigation, or self-reporting must be tracked in the security risk register and remediated within timelines determined by risk severity.

**15.3** External audits (including customer audits and regulatory inspections) are coordinated by Legal & Compliance with IT Security support. All audit documentation requests must be routed through Legal & Compliance.

---

## 16. Policy Exceptions

Exceptions to this Policy may be granted in limited circumstances where compliance is technically infeasible or would cause disproportionate business disruption.

**16.1** Exception requests must be submitted to IT Security using the Policy Exception Request form (ITS-EXC-01) and must include: the specific control being excepted; the business justification; proposed compensating controls; and the requested exception duration.

**16.2** All exceptions require CISO written approval. Exceptions affecting RESTRICTED data additionally require approval from the General Counsel.

**16.3** Maximum exception duration is 12 months. Extensions require re-submission and re-approval. Exceptions may not be indefinitely renewed without a documented remediation plan.

**16.4** Active exception register (as of Policy effective date):

| ID | Control Reference | Exception Granted To | Justification | Expiry Date |
|----|------------------|---------------------|---------------|-------------|
| EX041 | §6.3 (MFA) | Legacy Warehouse Terminal System | Hardware incompatibility with MFA agent; compensating control: IP allowlisting + physical access restriction | 2024-09-30 |
| EX047 | §9.1 (TLS 1.2+) | Supplier EDI Gateway — Vendor: Hartmann GmbH | Legacy EDI partner; migration to TLS 1.2 in progress. Traffic isolated to dedicated VLAN. | 2024-06-30 |

---

## 17. Enforcement and Violations

**17.1** Violations of this Policy may result in disciplinary action up to and including termination of employment or contract, in accordance with applicable HR policies and contractual terms.

**17.2** Intentional or malicious violations may be referred to law enforcement. Lichen reserves all legal remedies.

**17.3** Third-party violations may result in suspension of data access, contract termination, and recovery of damages where applicable.

**17.4** Lichen Manufacturing will not retaliate against employees who report good-faith suspected policy violations.

---

## 18. Review and Maintenance

**18.1** This Policy is reviewed annually by the CISO and updated to reflect changes in the regulatory environment, threat landscape, and business operations.

**18.2** Material changes (those affecting compliance obligations, access control requirements, or third-party provisions) require Executive Leadership Team approval prior to publication.

**18.3** Minor changes (typographical corrections, clarifications that do not alter intent) may be published by the CISO without Executive approval, provided changes are logged in the Document Control table.

**18.4** All employees and contractors are notified of Policy updates via the internal compliance communications channel. Acknowledgment of updated Policy terms is required within 30 days of publication.

---

*END OF DOCUMENT — ISP-001 v4.2 | Lichen Manufacturing, Inc. | INTERNAL USE*
