**HUMAN REVIEWER ORIENTATION**

*This page is not ingested by the AI pipeline. It is a guide for human reviewers and demo operators only.*

| |
|---|
| **What this document is** |
| A governed export of four Slack threads from the Lichen internal workspace, relevant to the OptiChain vendor onboarding evaluation (PRQ-2024-0047). This source is ingested into the pipeline's retrieval index at LOW authority. It is supplementary context only — no agent may cite a Slack message as a primary source for any determination. |
| **What the AI sees** |
| The pipeline ingests Threads 1 through 4 only. This orientation page is excluded from the retrieval index. The threads are presented to the pipeline as raw message content with no labels, annotations, or guidance about which threads are relevant or out of scope. The agent must reason through this itself. |

**Thread guide — for demo operators**

| **#** | **Channel** | **Intended agent use** | **What the agent should do with it** |
|---|---|---|---|
| **1** | #vendor-eval-optichain | IT Security Agent | Thread contains a sales-call impression consistent with the formal questionnaire answer — integration is export-only, no persistent connection. Agent should note consistency but still cite ISP-001 §12.2 as PRIMARY for tier determination, not the Slack thread. Thread is supplementary context at most. |
| **2** | #procurement-ops | Procurement Agent | Thread confirms NDA execution and existing MSA, consistent with questionnaire Q5.1 and Q5.2. Agent should treat the formal questionnaire as the authoritative source and cite that, not this thread. Thread is supplementary confirmation only. |
| **3** | #optichain-review-notes | IT Security Agent, Procurement Agent | Thread contains informal meeting notes summarizing the clean pass — no blockers, fast-track path confirmed. Useful supplementary context but too imprecise to cite as primary evidence. Agent should surface this as background while citing formal documents for all determinations. |
| **4** | #facilities-ops | None — out of scope | Thread discusses an unrelated catering vendor onboarding (PRQ-2024-0051, Greenbrook Catering Services). It shares vocabulary with the OptiChain evaluation (vendor, onboarding, approval, NDA, Class E, Tier 1) but has zero relevance. The agent should correctly exclude this thread from any OptiChain determination. Naive retrieval will likely surface it; the governed pipeline should not. |

**What a well-functioning governed pipeline should demonstrate**

> • Retrieve Threads 1, 2, and 3 as supplementary context for the relevant domain agents.
>
> • Correctly exclude Thread 4 from all OptiChain-related determinations.
>
> • Treat Thread 1 as consistent supplementary context — not as a substitute for ISP-001 §12.2 tier assignment.
>
> • Treat Thread 2 as consistent supplementary context — not as a substitute for the questionnaire NDA field.
>
> • Never cite any Slack message as a primary source. Cite only formal policy documents in all determination outputs.
>
> • Surface Thread 3 as supplementary background at most — not as evidence for any specific determination.

**What naive RAG is expected to get wrong**

> • May surface Thread 4 (catering vendor) as relevant because it shares onboarding vocabulary.
>
> • May cite T. Kowalski's Slack impression in Thread 1 as the basis for the Tier 3 determination rather than ISP-001 §12.2.
>
> • Cannot enforce source authority hierarchy — a Slack message and ISP-001 receive equal weight in retrieval.

---

**Thread 1**

**# vendor-eval-optichain**

Exported February 27, 2024 — 8 messages

――― February 27, 2024 ―――

**P. Horak** 9:14 AM

Hey team — just a heads up that we've received OptiChain's formal questionnaire submission through the vendor portal. Procurement has it and IT Security and Legal are being looped in this week. Given that this is a renewal-adjacent engagement with an existing vendor relationship from last year, I'm hoping the review is relatively quick. @M. Osei can you confirm receipt and next steps?

---

**M. Osei** 9:31 AM

Confirmed — questionnaire received, logged as PRQ-2024-0047, review initiated. First read looks clean — they're proposing the export-only module, no direct ERP integration, no personal data. I'll send the formal kickoff note to IT Security and Legal today.

---

**T. Kowalski** 10:08 AM

Quick question — do we know yet how they're actually connecting to SAP? I had a call with their sales team last week and got the impression it's just nightly exports, no persistent connection into the system at all.

---

**D. Achterberg** 10:33 AM

That's consistent with what the questionnaire says in Q2.2 — they explicitly describe export-only file-based transfers over HTTPS with no persistent session and no service account credentials on their side. That's a clean Tier 3 under ISP-001 §12.2. I'll confirm formally once I've reviewed the full submission but the integration pattern is clear from their answer.

---

**T. Kowalski** 10:41 AM

Good — that should make the security side pretty clean then. No architecture diagram request needed this time?

---

**D. Achterberg** 10:49 AM

No. Their Q2.2 answer is unambiguous — export-only, Lichen initiates, no vendor-side credentials, HTTPS transmission. The ISP-001 §12.2 Tier 3 criteria are satisfied from the questionnaire alone. I'll document the formal tier assignment in the onboarding record.

---

**M. Osei** 11:02 AM

Great. I'll log ERP integration tier as Tier 3 confirmed pending D. Achterberg's formal sign-off. No PROVISIONAL status needed on the integration question.

---

**P. Horak** 11:15 AM

Sounds like a much cleaner run than we sometimes get with new platforms. Let's keep it moving — I want this wrapped up inside two weeks.

---

**Thread 2**

**# procurement-ops**

Exported March 4, 2024 — 6 messages

――― March 4, 2024 ―――

**M. Osei** 8:47 AM

OptiChain questionnaire just came in through the portal — PRQ-2024-0047. Starting my review now. One thing to confirm: NDA status. Their Q5.1 says fully executed January 15, 2024. Can Legal confirm that's in our contract records?

---

**R. Lim** 9:05 AM

Confirmed. Executed mutual NDA with OptiChain, Inc. on file — signed January 15, 2024. No issues there. ISP-001 §12.1.4 is satisfied. Information-exchange phase is clear.

---

**M. Osei** 9:12 AM

Perfect. Also checking Q5.2 — they reference a prior MSA from PRQ-2023-0031. Can you confirm that engagement closed cleanly?

---

**R. Lim** 9:24 AM

Yes, PRQ-2023-0031 closed Q3 2023 with no open items, no compliance flags, no outstanding obligations. The MSA is on file. This satisfies the prior relationship requirement for fast-track consideration under the procurement matrix.

---

**M. Osei** 9:31 AM

Great. Logging NDA status as EXECUTED and prior relationship as CONFIRMED in the onboarding record. No blockers on the legal/contractual side.

---

**P. Horak** 10:05 AM

Thanks both — clean on the legal side then. @M. Osei let me know when you have the classification memo ready. I want to make sure the fast-track path is formally documented before we loop in the business owner for sign-off.

---

**Thread 3**

**# optichain-review-notes**

Exported March 5, 2024 — 5 messages

――― March 5, 2024 ―――

**M. Osei** 3:15 PM

Posting the notes from today's OptiChain review kickoff (30 min call, attendees: P. Horak, D. Achterberg, R. Lim, M. Osei): Status: Questionnaire received, review complete. No blocking items identified. Summary: ERP integration — confirmed Tier 3 / export-only per ISP-001 §12.2. No architecture documentation required. Data classification — UNREGULATED. No regulated data, no personal data, no EU employee data in scope. DPA — not required. No DPA trigger rows apply. NDA — fully executed January 15, 2024. Prior relationship — PRQ-2023-0031 closed cleanly Q3 2023. Vendor class — Class C (non-regulated software). Contract value — $45K TCV / T1. Approval path — FAST_TRACK eligible. Next steps: D. Achterberg to issue formal Tier 3 sign-off to Procurement by EOD. M. Osei to issue Procurement Classification Memo. Manager-level sign-off to close the run.

---

**D. Achterberg** 3:27 PM

Formal Tier 3 confirmation sent to @M. Osei — documented in the onboarding record. No security follow-up items.

---

**R. Lim** 3:33 PM

Legal confirmation issued — no DPA required, NDA confirmed, no legal blockers. Fast-track path is clear from our side.

---

**M. Osei** 3:40 PM

Classification memo drafted and being routed for Manager sign-off. Logging overall onboarding status as COMPLETE pending final Manager approval. Fastest run we've had in a while.

---

**P. Horak** 3:55 PM

Great work everyone. I'll get the Manager sign-off from Operations by end of week. Once that's confirmed we can notify OptiChain and kick off onboarding. Good example of the process working the way it's supposed to.

---

**Thread 4**

**# facilities-ops**

Exported March 5, 2024 — 6 messages

――― March 5, 2024 ―――

**C. Oduya** 10:05 AM

Heads up — we're kicking off the onboarding process for Greenbrook Catering Services for the Dortmund facility cafeteria contract (PRQ-2024-0051). They're replacing Compass Group effective May 1. Contract value is about €48,000 annually. No data or system access required, just a facilities services agreement.

---

**N. Papadopoulos** 10:18 AM

Does this need to go through the full vendor approval process or is there a lighter-weight path for facilities vendors?

---

**C. Oduya** 10:31 AM

Class E, Tier 1 — so it's the FAST_TRACK path. No IT Security review required, no DPA, just standard NDA and Procurement sign-off at Manager level. Should be done in a few days.

---

**N. Papadopoulos** 10:39 AM

Perfect, and I assume no ERP integration or data access for a catering vendor?

---

**C. Oduya** 10:44 AM

Correct — zero system access. They're providing catering services only. The only thing we're sharing with them is the headcount by facility for meal planning, which is aggregate non-personal data. No DPA needed.

---

**C. Oduya** 11:02 AM

NDA is already drafted, sending to Greenbrook today. Should have this wrapped up by end of week. I'll post the final approval confirmation here once it's done.

---

*END OF DOCUMENT — SLACK-EXPORT-001-SCENARIO01 v1.0 | Lichen Manufacturing, Inc. | INTERNAL USE*
