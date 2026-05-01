# Slack Thread Export — SLK-001

**Document ID:** SLACK-EXPORT-001  
**Version:** 1.0  
**Export Date:** March 5, 2024  
**Classification:** INTERNAL USE  
**Source ID:** SLK-001  
**Authority Tier:** 4  
**Citation Class:** SUPPLEMENTARY  
**Domain:** Procurement-scoped  

---

## Thread 01 — #vendor-eval-optichain

**Thread ID:** SLK-001-THREAD-01  
**Export Date:** 2024-02-27  
**Messages:** 9  

**P. Horak** 2024-02-27 09:14:00
> Hey team — just a heads up that we've received OptiChain's formal questionnaire submission through the vendor portal. Procurement has it and IT Security and Legal are being looped in this week. We're on a 30-day clock for the go/no-go so let's keep this moving. @M. Osei can you confirm receipt and next steps?

**M. Osei** 2024-02-27 09:31:00
> Confirmed — questionnaire received, logged as PRQ-2024-0047, review initiated. I'll send the formal kickoff note to IT Security and Legal today. Based on a quick first read there are a few things to work through but nothing that looked like a showstopper at first glance.

**T. Kowalski** 2024-02-27 10:08:00
> Quick question — do we know yet how they're actually connecting to SAP? I had a call with their sales team last week and I got the impression it's just a nightly export, no persistent connection into the system. If that's the case it should be pretty straightforward from a security standpoint, right?

**D. Achterberg** 2024-02-27 10:44:00
> I'll be reviewing the technical side. I've seen their questionnaire answer on Q2.2 and honestly it's a bit unclear — they mention a 'lightweight extraction agent' that 'may operate with service account credentials depending on customer configuration.' That language doesn't land cleanly in Tier 2 or Tier 3. I'm going to need to see an architecture diagram before I can make a formal call on the integration tier.

**T. Kowalski** 2024-02-27 10:52:00
> Ah got it, that's more nuanced than what their sales deck implies. Good catch. Happy to defer to your assessment once you've seen the diagram.

**P. Horak** 2024-02-27 11:03:00
> Thanks both. @D. Achterberg — once you know what you need from OptiChain to make the tier call, can you flag it and we'll route the request through Procurement? Want to make sure any asks go through the formal channel, not informally through me or the sales contact.

**D. Achterberg** 2024-02-27 11:17:00
> Agreed. I'll document the specific information request and send it to @M. Osei to route formally. Won't make a tier determination until I have the architecture diagram in hand.

**M. Osei** 2024-02-27 11:22:00
> Perfect. I'll flag the onboarding as PROVISIONAL pending IT Security's tier determination and make sure that's reflected in the onboarding record.

**P. Horak** 2024-02-27 14:05:00
> One more thing — I want to make sure the business side doesn't start sharing any data or doing any integration planning with OptiChain until the formal process is done. Even if conversations have happened at the sales level, nothing moves until Procurement and IT Security sign off. Please make sure the ops team knows this.

---

## Thread 02 — #procurement-ops

**Thread ID:** SLK-001-THREAD-02  
**Export Date:** 2024-03-04  
**Messages:** 7  

**M. Osei** 2024-03-04 08:47:00
> OptiChain questionnaire just came in through the portal — PRQ-2024-0047. Starting my review now. One thing I'm trying to confirm: does anyone know if we have a current NDA with OptiChain? I want to check before I log the NDA status in the onboarding record.

**T. Kowalski** 2024-03-04 09:02:00
> I think we might? I feel like we had some conversations with them earlier this year, maybe even a pilot or something. Could be worth checking with Legal.

**M. Osei** 2024-03-04 09:18:00
> I'll check with Legal to be sure. Don't want to assume — if the NDA isn't confirmed executed we can't move to the information-exchange phase.

**R. Lim** 2024-03-04 09:41:00
> I've checked our contract records. There is no executed NDA with OptiChain, Inc. on file. Their questionnaire (Q5.1) indicates they transmitted a draft NDA to us on February 19th and it hasn't come back countersigned. That's an open item — I'm flagging it as PROVISIONAL per ISP-001 §12.1.4. No information exchange until we have a signed copy confirmed.

**T. Kowalski** 2024-03-04 09:55:00
> Ah, I was probably thinking of a different vendor. Good that we checked properly rather than assumed.

**M. Osei** 2024-03-04 10:03:00
> Logging NDA status as PROVISIONAL in the onboarding record. @P. Horak — flagging for awareness. This means the business team cannot share any Lichen data with OptiChain until Legal confirms the NDA is signed.

**P. Horak** 2024-03-04 10:22:00
> Understood. I'll make sure ops knows. Thanks for catching this early.

---

## Thread 03 — #optichain-review-notes

**Thread ID:** SLK-001-THREAD-03  
**Export Date:** 2024-03-05  
**Messages:** 5  

**M. Osei** 2024-03-05 15:15:00
> Posting the notes from today's OptiChain review kickoff (30 min call, attendees: P. Horak, D. Achterberg, R. Lim, M. Osei): Status: Questionnaire received, review underway. Three open items identified: 1. ERP integration — DA needs architecture diagram from OptiChain before IT Security can make a formal tier call. Classified as PROVISIONAL for now. 2. DPA — R. Lim confirmed a GDPR Art. 28 DPA is required given the EU employee data in scope. Legal will initiate drafting. DPA is a blocker before any data exchange. 3. NDA — not yet executed. R. Lim has flagged this as PROVISIONAL. Data exchange blocked until confirmed. Procurement path: standard enhanced (Class A, T3). No fast-track. No executive approval needed at this value. Next steps: DA to send architecture diagram request to Procurement by EOD Thursday. Legal to initiate DPA drafting. Procurement to notify OptiChain of open items and expected timelines.

**D. Achterberg** 2024-03-05 15:28:00
> Confirmed — I'll have the formal information request to @M. Osei by Thursday EOD. The key thing I need from them is clarity on whether their extraction agent holds its own SAP service account credentials or whether it uses a Lichen-managed credential broker. That's the hinge point for the tier call.

**R. Lim** 2024-03-05 15:35:00
> DPA drafting initiated. I'm working from our standard GDPR Art. 28 template. I'll also confirm the EU data residency setup — their questionnaire mentions eu-west-1 for EU data which is good, but I want to verify the OptiChain Europe B.V. entity is the contracting counterpart for the DPA. That affects how we structure the SCCs question.

**M. Osei** 2024-03-05 15:41:00
> Good point on the entity. I'll flag that for the DPA negotiation. For the record: Procurement has logged overall onboarding status as ESCALATED pending resolution of the three open items. No implementation activity is authorized until all three are resolved and Legal and IT Security have signed off.

**P. Horak** 2024-03-05 16:02:00
> Thanks all — this is exactly the kind of early clarity we need. I've let the ops team know nothing moves until the process is complete. OptiChain's sales team is asking about timeline — I'm telling them 10 business days assuming they're responsive on the architecture diagram and NDA. Sound right? Also — just to be clear, none of this goes back to OptiChain directly through this channel. All vendor comms go through Procurement.

---

## Thread 04 — #facilities-ops

**Thread ID:** SLK-001-THREAD-04  
**Export Date:** 2024-03-05  
**Messages:** 6  

**C. Oduya** 2024-03-05 10:05:00
> Heads up — we're kicking off the onboarding process for Greenbrook Catering Services for the Dortmund facility cafeteria contract (PRQ-2024-0051). They're replacing Compass Group effective May 1. Contract value is about €48,000 annually. No data or system access required, just a facilities services agreement.

**N. Papadopoulos** 2024-03-05 10:18:00
> Does this need to go through the full vendor approval process or is there a lighter-weight path for facilities vendors?

**C. Oduya** 2024-03-05 10:31:00
> Class E, Tier 1 — so it's the streamlined path. No IT Security review required, no DPA, just standard NDA and Procurement sign-off at Manager level. Should be done in a few days.

**N. Papadopoulos** 2024-03-05 10:39:00
> Perfect, and I assume no ERP integration or data access for a catering vendor?

**C. Oduya** 2024-03-05 10:44:00
> Correct — zero system access. They're providing catering services only. The only thing we're sharing with them is the headcount by facility for meal planning, which is aggregate non-personal data. No DPA needed.

**C. Oduya** 2024-03-05 11:02:00
> NDA is already drafted, sending to Greenbrook today. Should have this wrapped up by end of week. I'll post the final approval confirmation here once it's done.

---
