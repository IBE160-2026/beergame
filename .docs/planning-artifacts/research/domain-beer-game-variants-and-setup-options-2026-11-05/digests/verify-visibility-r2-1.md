# Verification r2-1: downstream vs upstream inventory visibility in Beer Game experiments

Accessed 2026-11-05. Each finding: {claim, source URL, publisher, publication date, accessed, confidence, fetched|snippet-only}.

## Overall verdict on the claim: verified, with qualifications (see end)

## F1. Management Science 2006 (Croson & Donohue), manipulation: ALL four inventory positions shown to ALL players
- Claim: Study II was identical to Study I "except that the participants also had access to dynamic inventory information. This information was displayed in a bar chart with four bars representing the inventory positions of the four members of their group. The chart was automatically updated at the beginning of each period so all members had access to the same information." So this paper did NOT separate downstream from upstream visibility; it compared no inventory information vs full inventory information (44 participants in Study II).
- Source: https://faculty.wharton.upenn.edu/wp-content/uploads/2012/04/%5B34%5D.pdf (full text, doi 10.1287/mnsc.1050.0436)
- Publisher: INFORMS, Management Science 52(3), pp. 323-336 (author-hosted PDF at Wharton); March 2006
- Accessed 2026-11-05 | confidence: high | fetched (PDF downloaded and text-extracted locally with pdftotext)

## F2. Management Science 2006: findings (abstract, verbatim)
- "In the second experiment, we find that the bullwhip, and the underlying tendency of underweighting, remains when information on inventory levels is shared. However, we observe that inventory information helps somewhat to alleviate the bullwhip effect by helping upstream chain members better anticipate and prepare for fluctuations in inventory needs downstream. These experimental results support the theoretically suggested notion that upstream chain members stand to gain the most from information-sharing initiatives."
- Body: order variance significantly lower with inventory shown (n=44, m=44, z=1.92, p=0.028); amplification "reduced, but still present" (69% of links vs 82% in Study I); Hypothesis 4 (decreased amplification) rejected overall; Hypothesis 5 (no longer underweight supply line) rejected: 42 of 44 participants underweighted the supply line, avg supply-line weight -0.0288 vs inventory weight -0.1939; "participants' underweighting of the supply line is robust to the additional information". Upstream (distributor+manufacturer) variance reduction significant (p=0.043); retailer+wholesaler not significant (p=0.110).
- The discussion contains a CONJECTURE, not a test: "the critical part of an inventory-sharing information system is not communicating the inventory position of the manufacturer to the retailer, but rather communicating the inventory position of the retailer to the manufacturer."
- Total cost: no total-cost result for Study II found in the retrieved text (the paper measures order variance; chain cost appears only as the incentive basis). Not verified from this source.
- Source: same as F1; abstract also on https://econpapers.repec.org/RePEc:inm:ormnsc:v:52:y:2006:i:3:p:323-336 (paraphrase only: snippet-only) and https://repository.upenn.edu/oid_papers/172 (403, not fetched)
- Accessed 2026-11-05 | confidence: high | fetched (full text)

## F3. System Dynamics Review 2005 (Croson & Donohue), "Upstream versus downstream information and its impact on the bullwhip effect": the direct test
- Manipulation (verbatim): "In treatment one (our baseline case) participants only saw their own inventory levels (i.e., one bar in the chart)... In treatment two (upstream only) participants saw their own inventory level as well as the inventory levels of all upstream members (e.g., the distributor saw inventory levels for himself and the manufacturer). In treatment three (downstream only) participants had access to their own inventory level as well as the inventory levels of all downstream customers (e.g., the distributor now sees his own as well as the retailer and wholesaler inventory levels)." Note "upstream" = all upstream members, not only the one-step-up supplier. 96 Carlson MBA students: 28 (7 teams) baseline, 36 (9 teams) upstream, 32 (8 teams) downstream.
- Abstract (verbatim): "We first independently test whether sharing upstream or downstream inventory information helps reduce bullwhip behavior, and find that only downstream information sharing leads to significantly lower order oscillations throughout the supply chain. We then compare the reduction in order oscillations experienced by supply chain level and find that upstream supply chain members benefit the most from downstream information sharing."
- Results: average order variance baseline 80.66; upstream-only 55.10 (not significant: n=28, m=36, U=49, z=0.81, p=0.234); downstream-only 30.10 (significant vs baseline: p=0.044; vs upstream-only p=0.026). Quote: "sharing only upstream information offers no significant performance improvement in our setting." Bullwhip persisted in all treatments (sign tests reject no-amplification). Upstream info "actually increases average order oscillations for the retailer and wholesaler, relative to the baseline case" (not significant). Downstream info: manufacturer/distributor reduction significant (p=0.026), retailer/wholesaler not (p=0.167).
- Total cost: the abstract names "its associated costs" as the research question, but the retrieved text reports order variance, not a total-cost comparison. Cost/profit result NOT verified.
- Caveats: small samples (7-9 teams per cell); different cohort per treatment; the 55.10-vs-80.66 gap is large in absolute terms but not significant, so "does not reduce" means "no statistically significant reduction", not "no change". Upstream visibility showed a lower mean variance than baseline.
- Source: https://faculty.wharton.upenn.edu/wp-content/uploads/2012/04/%5B32%5D.pdf (author-hosted full text; Wiley page https://onlinelibrary.wiley.com/doi/abs/10.1002/sdr.320 returned 403)
- Publisher: John Wiley & Sons, Syst. Dyn. Rev. 21(3), 249-260; 2005; doi 10.1002/sdr.320
- Accessed 2026-11-05 | confidence: high | fetched (full text via curl + pdftotext). Independent secondary snippets (zendy.io, peeref.com, synapsesocial) agree: snippet-only.

## F4. Production and Operations Management 2003 (Croson & Donohue), POS data sharing
- Abstract (verbatim, via iaorifors.com abstract record): "We find, using a controlled simulation experiment, that sharing POS information does help reduce some components of the bullwhip effect in a stable demand setting, namely the order oscillation of upstream members." Also: "Theoretical studies have shown that exposure to POS data can lead to a reduction in the bullwhip effect when suppliers have no prior knowledge of the demand distribution. The benefit of sharing POS data in stable industries, where the demand distribution is commonly known, is less clear."
- Manipulation: POS = retail (end-customer) demand shared with upstream players. The abstract describes no upstream-visibility treatment; this paper did not test a supplier's inventory being visible downstream. Detailed design not retrieved.
- Total cost: not in the abstract.
- Source: https://iaorifors.com/paper/43290 (abstract index; title there reads "point of scale" in error). POM vol. 12(1), pp. 1-11, March 2003.
- Accessed 2026-11-05 | confidence: medium-high for abstract, low for design details | fetched (abstract record only, not the paper)

## F5. Other experiments testing visibility of another echelon
- Steckel, Gupta & Banerji (2004), Management Science 50(4), 458-464, "Supply Chain Decision Making: Will Shorter Cycle Times and Shared Point-of-Sale Information Necessarily Help?" Manipulated shared POS (end-customer demand), cycle length, demand pattern. Reported (paraphrase of the abstract): sharing POS data does not always help; with continually changing demand (S-shaped) it can distract upstream decision makers from orders from the nearest downstream partner and the supply line. This qualifies the claim: downstream (POS) visibility is not uniformly beneficial. Source: https://econpapers.repec.org/RePEc:inm:ormnsc:v:50:y:2004:i:4:p:458-464 | INFORMS | 2004 | accessed 2026-11-05 | confidence medium | fetched but only a paraphrase returned (treat as snippet-level).
- Wu & Katok (2006), J. Operations Management 24(6), 839-850, "Learning, communication, and the bullwhip effect". Manipulates training and team communication, not inventory visibility. Reported: variability falls with hands-on experience followed by joint team strategy formulation. Not a test of another echelon's inventory visibility. Source: search result summary (bib-bvb.de record), snippet-only. confidence medium.
- Not checked (budget): Gonçalves & Moshtari, Cantor & Katok, Ancarani. No claim made about them.

## Disagreement and qualifications (not averaged)
1. The claim attributes the downstream-vs-upstream contrast to all three papers. Only SDR 2005 tested it. MS 2006 tested full-vs-no inventory sharing and only conjectured the downstream-is-key point; POM 2003 tested POS (retail demand) sharing. SDR 2005 itself says Croson and Donohue (2004/2006) "speculate that downstream inventory information may be more beneficial than upstream, [but] their paper does not provide evidence of this."
2. "Upstream visibility" in SDR 2005 means seeing ALL upstream members' inventories, not specifically the supplier one step up. A claim limited to "the supplier one step upstream" is an extrapolation.
3. "Does NOT reduce" = no statistically significant reduction (mean variance 80.66 to 55.10, p=0.234) in a small-sample design. Upstream info slightly raised retailer/wholesaler variance (non-significant); the authors attribute this to frustration at not being able to act on what they saw.
4. Total cost: none of the retrieved texts reports a total-cost result for these visibility treatments. Unverified.
5. Supply-line part: verified from MS 2006 full text for full sharing; SDR 2005 did not analyse supply-line weights in the retrieved text.

## Verdicts
- Downstream inventory sharing reduces order oscillation; upstream-only visibility does not significantly reduce it: verified (SDR 2005 full text; one study, one cohort).
- Attribution of that finding to POM 2003 and MS 2006: disputed (they did not run the upstream-only treatment; MS 2006 only conjectured it).
- Sharing inventory info reduces bullwhip only partly and does not fix supply-line underweighting: verified (MS 2006 full text and abstract).
- Total-cost effect of visibility: unverified.
