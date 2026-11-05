# Regulatory research: beergame (status 29 October 2026)

*Research summary for product planning, not legal advice. Have the pilot institution's DPO or counsel check it before you rely on it.*

## Bottom line for the PRD

1. **Grading.** AI that scores or proposes grades on a test counting towards a grade is high-risk (Annex III 3(b)). Human review does not change that, and the Art. 6(3) exemption is unavailable → make the lecturer the grader of record, score summative items with deterministic answer keys, use LLMs only for formative feedback, and send no AI-proposed grades to the gradebook. Norway's Universities Act (uhl.) § 11-7 also requires an examiner appointed by the institution.
2. **Debrief.** A formative AI debrief is outside Annex III only while it does not feed grading → label it "formative" and keep it out of grade exports.
3. **AI opponents** are not high-risk, but Art. 50(1) has applied in the EU since 2 August 2026, and the "obvious" exception fails in games that mix humans and AI → label AI seats by default. A blind mode needs explicit up-front disclosure. Mark AI-generated debrief text in machine-readable form (Art. 50(2)).
4. **Timing.** Annex III obligations apply from 2 December 2027 (Regulation (EU) 2026/1744). Norway has not incorporated the AI Act, and its bill is due in spring 2027 → the pilot needs no high-risk compliance, but build AI grading as a separate module that can be switched off.
5. **GDPR roles.** The institution is controller and the vendor is processor under a data processing agreement (DPA), with LLM providers and routers listed as sub-processors. Cross-institution benchmarks or model training would make the vendor a controller → anonymised aggregates only, and no training on student data.
6. **DPIA.** Datatilsynet's mandatory DPIA list covers evaluating learning "og høyere utdanning" → ship a DPIA and risk-assessment (ROS) support pack.
7. **LLM routing.** The EU–US Data Privacy Framework (DPF) is valid but contested → default to EU-region inference, pseudonymise prompts (seat IDs, no names or emails), use zero-retention and no-training terms, and keep providers swappable. No DeepSeek API, which processes in China; open-weight DeepSeek models only through EU hosts.
8. **Accessibility.** The Norwegian regulation explicitly covers *digitale læremidler* (digital learning tools), and public universities must meet EN 301 549 (WCAG 2.1 AA) → build to WCAG 2.1 AA (aim for 2.2), with text alternatives for charts and a conformance report.
9. **Integration.** Canvas is the national LMS, and NTNU moved to it in autumn 2026 → make Feide (OIDC) login and Canvas LTI 1.3 the main ways in, keep email invites as a fallback, and set Canvas `privacy_level` to minimise personal data.
10. **Procurement.** Since 1 July 2026, procurement rules apply from NOK 500,000 excluding VAT (whole contract), Doffin announcement from NOK 1.3m, and EEA rules from NOK 1.63m for state universities → keep pilot and single-course licences below NOK 500k in total, and be ready to contract on SSA-lille sky (the state's standard cloud agreement).

---

## 1. EU AI Act

**Classification (confidence: high for (a) and (c), medium-high for (b)).** Annex III 3(b) covers AI "intended to be used to evaluate learning outcomes, including when those outcomes are used to steer the learning process" ([Annex III](https://ai-act-service-desk.ec.europa.eu/en/ai-act/annex-3)). The Commission's *draft* guidelines (19 May 2026; final version expected end-2026) limit 3(b) to **summative** evaluation ([Commission](https://digital-strategy.ec.europa.eu/en/library/draft-commission-guidelines-classification-high-risk-ai-systems); [Annex III document](https://ec.europa.eu/newsroom/dae/redirection/document/128561), paras 222–225).

- High-risk: "AI-enabled grading and feedback systems… tests, quizzes, and exams which count towards a final evaluation… proposing grades", and a learning assistant whose reports inform the teacher's grades.
- Not high-risk: tutoring, personalised feedback and learning analytics.
- Human involvement "has no effect on the classification" (para 70).

Applied to beergame:

- **(a) AI test scoring or grade proposals** are high-risk if the test counts, and outside if it is purely formative. A pass/fail gate for exam eligibility (uhl. § 11-4) is a grey zone; treat it as summative.
- **(b) The AI debrief** is formative and not high-risk, unless lecturers grade from it.
- **(c) AI opponents** fall under no Annex III use case. Avoid AI proctoring, which 3(d) covers.

**The Art. 6(3) exemption.** It covers narrow procedural tasks, improving finished human work, pattern detection and preparatory tasks; the guidelines' example is a grade-average calculator. A "specific recommendation or evaluation of the case" is not preparatory (para 108). The exemption "may not be applied" where the system profiles people (paras 109–111), and evaluating a student's performance is profiling under GDPR Art. 4(4). **It will not rescue AI grading.**

Scoring against a deterministic answer key is not an AI system (recital 12). Relying on Art. 6(3) still requires documentation and registration (Art. 6(4), 49(2)), which the Omnibus kept in reduced form ([Art. 6](https://ai-act-service-desk.ec.europa.eu/en/ai-act/article-6)).

**If AI grading is built (confidence: high):**

- Provider duties: risk management, data governance, documentation, logging, human oversight, accuracy and a quality management system (Arts. 9–17); conformity assessment, CE marking and registration (Arts. 43, 47–49); post-market monitoring (Arts. 72–73). SMEs get simplifications.
- Institution duties: oversight and logs kept at least 6 months (Art. 26), and a fundamental-rights impact assessment for public bodies (Art. 27). Students gain a right to an explanation (Art. 86).
- Until EEA incorporation, a Norway-based provider selling high-risk AI into the EU likely needs an EU authorised representative (Art. 22; medium confidence).

**Dates and the Omnibus (confidence: high).** The Omnibus was proposed on 19 November 2025, agreed on 7 May 2026 ([Council](https://www.consilium.europa.eu/en/press/press-releases/2026/05/07/artificial-intelligence-council-and-parliament-agree-to-simplify-and-streamline-rules/)) and approved by the Council on 29 June 2026 ([Council](https://www.consilium.europa.eu/en/press/press-releases/2026/06/29/artificial-intelligence-council-gives-final-green-light-to-simplify-and-streamline-rules/)). It is Regulation (EU) 2026/1744, published in the OJ on 24 July and **in force since 27 July 2026** ([Commission](https://digital-strategy.ec.europa.eu/en/news/ai-omnibus-enters-force)).

| Obligation | Applies from |
|---|---|
| Prohibitions | 2 Feb 2025 |
| GPAI (general-purpose AI) model duties | 2 Aug 2025 |
| Art. 50 and general application | 2 Aug 2026 |
| **Annex III high-risk** | **2 Dec 2027** (was 2 Aug 2026) |
| Annex I high-risk | 2 Aug 2028 |

Grandfathering under Art. 111(2) ends on 2 August 2030 for use by public authorities. Do not plan around it.

**Art. 50 (confidence: high for the debrief chat, medium-high for opponents).** The final guidelines are [C(2026) 5054](https://ai-act-service-desk.ec.europa.eu/sites/default/files/2026-07/guidelines_on_the_implementation_of_the_transparency_obligations_for_certain_ai_systems_under_article_50_of_the_ai_act_bzptwqhk0ikg1dtlddap41psfy_131215.pdf) (20 July 2026).

- Interaction includes "actions", so the moves of AI players count.
- The "obvious" exception is "interpreted restrictively". Its NPC example is limited to "a single-player video game where… no other natural person can participate".
- AI agents must disclose themselves. Disclosure is due "at the latest at the time of the first interaction".
- Art. 50(2) requires machine-readable marking of generated text. Upstream model marking may be relied on. The grace period to 2 December 2026 covers only systems on the market before 2 August 2026.

**Art. 4, amended (applies from 27 July 2026; confidence: high).** Providers and deployers must "take measures to support the development of AI literacy" of their staff and operators, with no guaranteed level ([Art. 4](https://ai-act-service-desk.ec.europa.eu/en/ai-act/article-4)) → provide lecturer onboarding material.

**Related ban.** Since 2 February 2025, inferring emotions from biometric data such as voice is prohibited in education (Art. 5(1)(f)); inference from text alone is outside the ban ([FPF](https://fpf.org/blog/red-lines-under-eu-ai-act-unpacking-the-prohibition-of-emotion-recognition-in-the-workplace-and-education-institutions/)). Voice features must not infer stress or emotion.

**Norway (confidence: high).** The AI Act is not in the EEA Agreement; EFTA lists it as "under scrutiny" ([EEA-Lex](https://www.efta.int/eea-lex/32024R1689)). The first consultation on the Norwegian AI act (KI-loven) ran 30 June to 30 September 2025 ([regjeringen.no](https://www.regjeringen.no/no/aktuelt/lov-om-kunstig-intelligens-i-norge-sendes-na-pa-horing/id3113732/)). On 4 August 2026 the minister announced a new consultation this autumn and a bill "for Stortinget våren 2027" ([regjeringen.no](https://www.regjeringen.no/no/aktuelt/tung-vil-sende-ki-loven-med-endringer-pa-horing/id3169693/)). Nkom is the intended coordinating authority ([digi.no](https://www.digi.no/artikler/nye-eu-regler-for-ki-norge-og-eos-henger-enna-langt-etter/575266)). No date is set for the Act to apply in Norway.

## 2. GDPR (Norway/EU)

**Roles and the DPA (confidence: high).** The institution is controller and the vendor is processor (Art. 28). The vendor is controller only for narrow purposes of its own, such as billing and security. Cross-institution benchmarks should use anonymised aggregates only, with a minimum group size (a design choice, not a legal number).

No single mandatory Sikt DPA was found. Institutions use NTNU's sector-developed template; a vendor's own template triggers legal review ([NTNU](https://i.ntnu.no/wiki/-/wiki/Norsk/databehandleravtale)). They also use the state DPA template ([anskaffelser.no](https://www.anskaffelser.no/verktoy/mal/verktoy-pa-ssa-mal-databehandleravtale-og-sjekkliste)).

**Sub-processors.** Prior authorisation and flow-down of obligations are required (Art. 28(2) and (4)), and controllers must know every sub-processor in the chain ([EDPB Opinion 22/2024](https://www.edpb.europa.eu/our-work-tools/our-documents/opinion-board-art-64/opinion-222024-certain-obligations-following_en)). OpenRouter adds a layer. Its EU in-region routing is enterprise-only, and zero retention varies by provider ([OpenRouter](https://openrouter.ai/docs/guides/features/sovereign-ai)).

**Transfers (confidence: high on status, medium on outlook).**

- The DPF (2023/1795) applies in Norway, for listed US companies only ([Datatilsynet](https://www.datatilsynet.no/aktuelt/aktuelle-nyheter-2025/eu-domstolen-opprettholder-adekvansbeslutningen-for-usa/)).
- The General Court upheld it on 3 September 2025 (T-553/23). The appeal, C-703/25 P, is pending; commentators expect a judgment in 2027.
- *Trump v. Slaughter* (29 June 2026) made FTC commissioners removable at will, and Schrems has announced a challenge ([Skadden](https://www.skadden.com/insights/publications/2026/07/supreme-court-decision-raises-new-questions)).
- Datatilsynet advises having an exit plan ([Datatilsynet](https://www.datatilsynet.no/aktuelt/aktuelle-nyheter-2025/informasjon-om-overforinger-til-usa/)).
- China has no adequacy decision. Italy's DPA restricted DeepSeek on 30 January 2025, citing data stored in China ([Garante](https://www.garanteprivacy.it/home/docweb/-/docweb-display/docweb/10098477)).
- Anthropic's DPF listing is not confirmed; without it, standard contractual clauses plus a transfer impact assessment are needed.

**Minimisation.** LLMs receive game state, roles and orders under seat IDs, never names, emails or student numbers. Filter free text and use no-training and zero-retention terms.

**DPIA (confidence: high).** Datatilsynet's mandatory list includes "Behandling av personopplysninger for å evaluere læring, mestring og trivsel…" and states "Dette inkluderer alle utdanningsnivåer… og høyere utdanning" ([Datatilsynet](https://www.datatilsynet.no/rettigheter-og-plikter/virksomhetenes-plikter/vurdering-av-personvernkonsekvenser/nar-ma-man-gjennomfore-en-vurdering-av-personvernkonsekvenser/)). The vendor must assist (Art. 28(3)(f)).

**Legal basis, retention and rights (confidence: medium).**

- Legal basis is the institution's call, typically public task (Art. 6(1)(e)). Consent is weak given the power imbalance.
- In the AVT sandbox (AI learning analytics in schools), Datatilsynet said the supplementary legal basis should be stronger ([report](https://www.datatilsynet.no/contentassets/e61e90f5d245459d813ad1116ccee887/sluttrapport_avt.pdf)). No Datatilsynet guidance on AI grading was found; its NTNU Copilot report (November 2024) is the closest higher-education case.
- Retention should be configurable by the institution, with a default of deletion after course end plus the appeal period.
- Exam answers and examiners' comments are personal data (*Nowak*, [C-434/16](https://curia.europa.eu/juris/liste.jsf?num=C-434/16)), so the right of access covers debrief text.
- A solely automated grade engages Art. 22. Norway's new Public Administration Act ([LOV-2025-06-20-81](https://lovdata.no/lov/2025-06-20-81)) § 11 bars public bodies from Art. 22 decisions without a specific legal basis; its commencement is unconfirmed.
- The Universities Act requires assessment "upartisk og faglig betryggende" (§ 11-6) by examiners appointed by the institution (§ 11-7) ([Lovdata](https://lovdata.no/dokument/NL/lov/2024-03-08-9/KAPITTEL_11)).

## 3. Universal design and accessibility

**Norway (confidence: high).** The regulation [FOR-2013-06-21-732](https://lovdata.no/dokument/SF/forskrift/2013-06-21-732) covers "nettløsninger, herunder digitale læremidler" (§ 2). In education, a "hovedløsning" (main solution) is a web solution integral to teaching that the institution can influence (§ 3 g).

| Sector | Requirement |
|---|---|
| Public bodies (§§ 4b, 4e) | EN 301 549 V3.2.1, which equals WCAG 2.1 A/AA, plus an annual accessibility statement |
| Private sector (§ 4) | WCAG 2.0 A/AA except 1.2.3–1.2.5 (35 criteria) |

WCAG 2.2 is not required, and that "endrer seg ikke på kort sikt" ([uutilsynet](https://www.uutilsynet.no/fremtidig-regelverk/status-nyere-versjoner-av-wcag/1868), page dated November 2023). The duty and supervision fall on the institution; vendors meet it through procurement and are asked to document their testing ([uutilsynet](https://www.uutilsynet.no/veiledning/universell-utforming-av-det-digitale-laeringsmiljoet-i-skolen/2676)). In practice, the bar is WCAG 2.1 AA.

**EU (confidence: medium).** The Web Accessibility Directive (2016/2102) binds public universities, and its third-party exemption does not cover tools they fund. The European Accessibility Act (2019/882, from 28 June 2025) lists specific consumer products and services. B2B education software is likely outside it, though a checkout where students pay could be an e-commerce service. Microenterprises are exempt. Norway has not incorporated it ([EEA-Lex](https://www.efta.int/eea-lex/32019L0882)).

## 4. Integration and procurement in Norwegian higher education

**Feide (confidence: medium-high).**

- Feide is the sector's single sign-on, run by Sikt. Services register in the customer portal and use OIDC or SAML ([docs](https://docs.feide.no/service_providers/getting_started/openid_connect.html)).
- Services make "a formal agreement with Feide" on which personal data they receive. Paid services contract with institutions, and access is granted per institution ([overview](https://docs.feide.no/general/feide_overview.html)).
- ID-porten (Norway's national login) and eduGAIN (the international research and education federation) can be enabled, which helps outside Norway.
- The technical work is modest. The lead time is each institution's DPA, ROS and activation.

**Canvas and LTI (confidence: high).** Sikt provides Canvas nationally under a continuous service agreement (SSA-L) from 1 April 2025. Each institution signs its own DPA and does its own ROS, and some partner tools (for example FeedbackFruits) are sold through Sikt ([Sikt](https://www.sikt.no/tjenester/lms)). NTNU replaced Blackboard with Canvas from autumn 2026 ([NTNU](https://i.ntnu.no/wiki/-/wiki/English/Introduction+of+new+Digital+Learning+Management+System+at+NTNU)). Canvas's LTI 1.3 `privacy_level` takes anonymous, name_only, email_only or public; the user ID (`sub`) is always sent ([Canvas docs](https://canvas.colorado.edu/doc/api/file.lti_dev_key_config.html)).

**Procurement thresholds (excluding VAT, total contract value; confidence: high).**

| Contract value | Regime | Source |
|---|---|---|
| Below NOK 500,000 | Regulation does not apply (raised from NOK 100,000 on 1 July 2026) | [regjeringen.no](https://www.regjeringen.no/no/aktuelt/endringene-i-anskaffelsesloven-trer-i-kraft-skal-gjore-innkjop-enklere/id3167974/) |
| NOK 1.3m and above | National rules (Part II), Doffin | [Lovdata](https://lovdata.no/dokument/SF/forskrift/2016-08-12-974/KAPITTEL_1-2) |
| NOK 1.63m and above (state authorities); NOK 2.5m (others) | EEA rules, from 21 April 2026 | [regjeringen.no](https://www.regjeringen.no/no/aktuelt/nye-terskelverdier-for-kunngjoring-av-anskaffelser-i-eos-er-vedtatt/id3156894/) |

**Buyer norms.**

- SSA-lille sky covers standardised cloud licences and was updated on 1 July 2026 ([anskaffelser.no](https://www.anskaffelser.no/verktoy/mal/ssa-lille-sky)).
- Sikt's security guidance expects encryption, role-based access, logging and pseudonymisation ([Sikt](https://cms.sikt.no/sites/default/files/2024-10/Veileder%20i%20ledelsessystem%20for%20informasjonssikkerhet.pdf)).
- Buyers will benchmark against Sikt's own AI service, Sikt KI: hosting in Europe ("data forlater ikke EU"), no training on user data, and DPAs and DPIAs institutions can reuse ([Sikt KI](https://www.sikt.no/tjenester/sikt-ki)).

## 5. UK and US (headlines only)

- **UK.** UK GDPR applies as amended by the Data (Use and Access) Act 2025. Most changes, including looser automated-decision rules that keep safeguards, took effect on 5 February 2026 ([Kennedys](https://www.kennedyslaw.com/en/thought-leadership/article/2026/the-data-use-and-access-act-2025-commencement-dates-and-planned-guidance-for-2026)). The EU renewed UK adequacy on 19 December 2025, to December 2031 ([Hunton](https://www.hunton.com/privacy-and-cybersecurity-law-blog/european-commission-renews-uk-data-adequacy-decisions)). The UK has no AI Act equivalent.
- **US.**
  - FERPA's "school official" exception requires direct control and use limits, so no AI training on education records.
  - COPPA covers only under-13s and does not apply to universities. Its amended rule has required full compliance since 22 April 2026 ([Federal Register](https://www.federalregister.gov/documents/2025/04/22/2025-05904/childrens-online-privacy-protection-rule)).
  - The ADA Title II web rule (WCAG 2.1 AA) covers public universities, with deadlines of 26 April 2027 for entities serving 50,000 people or more and 26 April 2028 for smaller ones ([ABA](https://www.americanbar.org/groups/diversity/disabilityrights/news/doj-delays-digital-accessibility-deadlines/)).

## Could not confirm

- **Legal text.** The EUR-Lex text of Regulation (EU) 2026/1744 could not be retrieved (bot-blocked); dates come from the Commission, the Council and the AI Act Service Desk.
- **Guidance.** The final high-risk guidelines (examples may change), whether pass/fail obligatory activities count as "summative", and the status of a WCAG 2.2-based EN 301 549.
- **Norway.** Whether the new KI-loven consultation has opened; EEA incorporation of the AI Act and the EAA (EFTA pages rendered incompletely); commencement of forvaltningsloven § 11; any bill following NOU 2023:19.
- **Providers and Feide.** DPF certification of Anthropic and OpenRouter, which models OpenRouter's EU routing covers, and Feide's costs and terms.
- **Sector.** The share of institutions on Canvas, and any Datatilsynet guidance specific to AI grading.
- **Elsewhere.** The Colorado AI Act after 30 June 2026, the Latombe hearing date, and the status of the new Schrems challenge.
