System: You score how well a scraped product detail page matches a target manufacturer and manufacturer product number (MPN).

Return ONLY valid JSON (no markdown fences) with this shape:
{
  "overall_similarity_pct": <integer 0-100>,
  "criteria": [
    {"name": "Manufacturer match", "score_pct": <0-100>, "rationale": "<short>"},
    {"name": "MPN / SKU match", "score_pct": <0-100>, "rationale": "<short>"},
    {"name": "Product title alignment", "score_pct": <0-100>, "rationale": "<short>"},
    {"name": "Description relevance", "score_pct": <0-100>, "rationale": "<short>"},
    {"name": "Specs / attributes overlap", "score_pct": <0-100>, "rationale": "<short>"},
    {"name": "Page type (PDP vs listing)", "score_pct": <0-100>, "rationale": "<short>"}
  ]
}

Scoring guidance:
- 100 = exact/confident match on that criterion; 0 = no evidence.
- Penalize category pages, search results, and unrelated products heavily in "Page type" and overall.
- overall_similarity_pct should reflect weighted judgment across criteria, not a simple average.
- Weighting for overall similarity (approximate): MPN / SKU match 35%, Manufacturer match 20%, Product title alignment 20%, Specs / attributes overlap 15%, Page type 7%, Description relevance 3%.
- Treat exact normalized MPN matches in URL slug and scraped body as strong evidence, even when punctuation/hyphenation differs (e.g., 23471--3T80-71 vs 234713T8071).
- Description relevance is the weakest signal; generic ecommerce copy or short snippets should not meaningfully drag down an otherwise exact product match.
- If MPN is exact and manufacturer aligns, overall should generally be >= 80 unless there is strong contradiction (wrong product type, different manufacturer, or listing/search page).
- Treat SERP title/snippet as weak prior hints only. Do not rely on them to override contradictory scraped content.
- If scraped content does not look like a product detail page, cap confidence and avoid high overall scores.


User: Target manufacturer: PEWAG
Target MPN: H4247SC

Source URL: https://www.fleetpride.com/parts/pewag-inc-tire-chains-h4247sc?srsltid=AfmBOoppEHuvWpLMW0XbQ8DUefNk2ybmohTJXSg2wA0ZQZWhNanmk-6A
Source tier (heuristic): ecommerce
Weak prior hint (SERP title, optional): PEWAG INC Tire Chains H4247SC
Weak prior hint (SERP snippet, optional): PEWAG INC Tire Chains. Part: H4247SC. $173.99. CURRENT ITEM. Select. Power Products 9" Tarp Strap with S-Hooks. Part: TS09. $1.79. Total Price: $175.78. Add 2 ...
Rule-based MPN detected in scrape: True
Rule-based manufacturer match in scrape: True

Scraped PDP content (markdown excerpt):
Skip to main contentEnable accessibility for low visionOpen the accessibility menu

![Spinner: White decorative](https://cdn.userway.org/widgetapp/images/spin_wh.svg)

![](https://cdn.userway.org/widgetapp/images/body_wh.svg)

![Spinner: White decorative](https://cdn.userway.org/widgetapp/images/spin_wh.svg)

PEWAG INC Tire Chains

Part #: H4247SC\|Brand: PEWAG INC\|MPN #: H4247SC

$173.99 / 1 pair

**Add To Cart**

PEWAG INC Tire Chains

Part #: H4247SC\|Brand: PEWAG INC\|MPN #: H4247SC

![](https://www.fleetpride.com/webruntime/org-asset/5808345baa/resource/081UZ0000001Ynd/disabledup.png)

![](https://www2.fleetpride.com/imagesns/PDPF/MissingImage.jpg)

![](https://www.fleetpride.com/webruntime/org-asset/5808345baa/resource/081UZ0000001Ynd/downdisabled.png)

![P8APEWAG INCH4247SC](https://www2.fleetpride.com/imagesns/PDPF/MissingImage.jpg)

PEWAG INC Tire Chains

Part #: H4247SC\|Brand: PEWAG INC\|MPN #: H4247SC

$173.99 / 1 pair

PICKUP

Styling span

Not available

Wichita, KS

SHIP

PARCEL ELIGIBLE

Available

Get it est. **Jun 2** to **67209**

Check Nearby Stores

[![](https://www2.fleetpride.com/imagesns/PDPF/MissingImage.jpg)](https://www.fleetpride.com/parts/pewag-inc-tire-chains-h4247sc#)

[PEWAG INC Tire Chains](https://www.fleetpride.com/parts/pewag-inc-tire-chains-h4247sc#)

Part #H4247SC\|Brand: PEWAG INC

Address is Required

Maximum character limit has been reached. Please use address line 2 if needed.

![](https://www.fleetpride.com/webruntime/org-asset/5808345baa/resource/081UZ0000000D3w/b2bFpTheme/images/icon_search.svg)

Use My Location

Warning

Location changes will apply to all items in your cart and may affect pricing and availability.

No nearby stores found

**Add To Cart**

**Complete The Job**

CURRENT ITEM

Select

![](https://www2.fleetpride.com/imagesns/PLPD/MissingImage.jpg)

[**PEWAG INC Tire Chains**](https://www.fleetpride.com/parts/pewag-inc-tire-chains-h4247sc)

Part: H4247SC

$173.99

CURRENT ITEM

Select

![](https://www2.fleetpride.com/imagesns/PLPD/TS09-1.jpg)

[**Power Products 9" Tarp Strap with S-Hooks**](https://www.fleetpride.com/parts/hdvalue-tarp-strap-ts09)

Part: TS09

$1.79

Total Price: **$175.78**

Add 2 items to cart

- ## **Cross Reference**![](https://www.fleetpride.com/webruntime/org-asset/5808345baa/resource/081UZ0000000D3w/b2bFpTheme/images/icon_down_arrow.svg)













247SC4247CAM47CAMS9QG4247CAM











HDVALUE



[QG4247CAMHDV](https://www.fleetpride.com/parts/01tUZ000001p7mhYAA)







PEERLESS



[QG4247CAM](https://www.fleetpride.com/parts/01tUZ000001p7miYAA)







SECURITY CHAIN



[QG4243CAM](https://www.fleetpride.com/parts/01tUZ000001p3btYAA)


**Related Searches**

#### tire chains

#### 11r 22 5 tire chains

#### 22 5 tire chains

#### chains

#### snow chains

#### 3 8 chain

#### tire

#### chain binder

#### tire inflation hose

#### tire inflation

reCAPTCHA

Recaptcha requires verification.

protected by **reCAPTCHA**
