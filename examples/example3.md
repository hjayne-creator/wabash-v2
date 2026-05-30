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

Source URL: https://shop.rushtruckcenters.com/products/ht-single-tire-chains-w-cams-h2247sc-pwg/250172?srsltid=AfmBOorqsBoCVhcVhjYHR4QY__kRnVa4Z0FmdI_tx7ioPbXVRo3qCTBL
Source tier (heuristic): ecommerce
Weak prior hint (SERP title, optional): Ht Single Tire Chains W/Cams - Parts Connect
Weak prior hint (SERP snippet, optional): ... H4247SC:PWG | Brand: Pewag Final Price $230.00. 132 Available for Delivery. 0 Available at Rush Truck Centers - San Antonio. H4247SC:PWG has replaced PTCH4247SC ...
Rule-based MPN detected in scrape: True
Rule-based manufacturer match in scrape: True

Scraped PDP content (markdown excerpt):
[Skip Navigation](https://shop.rushtruckcenters.com/products/ht-single-tire-chains-w-cams-h2247sc-pwg/250172#app_headerMain) [Skip to Main Content](https://shop.rushtruckcenters.com/products/ht-single-tire-chains-w-cams-h2247sc-pwg/250172#app_page)

# Ht Single Tire Chains W/Cams

![Model.Product.Name](https://cdn.partsconnect.rushcare.com/images/370X370/PEWAG_H2247SC.gif)

### Part Number

H2247SC:PWG

### Brand

Pewag

### Manufacturer Part Number

H2247SC

### VMRS Code

053-001-001

### VMRS Description

Chains - Tire

H2247SC:PWG has replaced PTCH2247SC:IPW, H2245SC:PWG, PTCH2245SC:IPW

Final Price$125.00

281Available for Delivery

0Available at

Rush Truck Centers - San Antonio


QuantityQuantity:1
Add To Cart


Specifications

Specifications are not available.

## Related Parts

![Previous Related Parts ](https://cdn.rushenterprises.com/ecommerce/vector/angle-left.svg)

[![Ht Dual Tire Chains W/Cams](https://cdn.partsconnect.rushcare.com/images/370X370/unavailable-image.png)](https://shop.rushtruckcenters.com/products/ht-dual-tire-chains-w-cams-h4247sc-pwg/255354)

[Ht Dual Tire Chains W/CamsPart #:\\
H4247SC:PWG \| Brand:\\
Pewag](https://shop.rushtruckcenters.com/products/ht-dual-tire-chains-w-cams-h4247sc-pwg/255354)Final Price$230.00

132Available for Delivery

0Available at Rush Truck Centers - San Antonio

H4247SC:PWG has replaced PTCH4247SC:IPW

QuantityQuantity:1Add To Cart

[![SAE FLAT GR8 3/8](https://cdn.partsconnect.rushcare.com/images/370X370/unavailable-image.png)](https://shop.rushtruckcenters.com/products/sae-flat-gr8-3-8-76513-ims/62421201)

[SAE FLAT GR8 3/8Part #:\\
76513:IMS \| Brand:\\
Imperial](https://shop.rushtruckcenters.com/products/sae-flat-gr8-3-8-76513-ims/62421201)Final Price$0.24

3188Available for Delivery

0Available at Rush Truck Centers - San Antonio

76513:IMS has replaced D8500-5743:LJ, W3/8S8F:LJ, D8400-7958:LJ

QuantityQuantity:1Add To Cart

[![HX CP PL USS 3/8X1-1/4  8](https://cdn.partsconnect.rushcare.com/images/370X370/unavailable-image.png)](https://shop.rushtruckcenters.com/products/hx-cp-pl-uss-3-8x1-1-4-8-16149-ims/62382687)

[HX CP PL USS 3/8X1-1/4 8Part #:\\
16149:IMS \| Brand:\\
Imperial](https://shop.rushtruckcenters.com/products/hx-cp-pl-uss-3-8x1-1-4-8-16149-ims/62382687)Final Price$0.64

1911Available for Delivery

99Available at Rush Truck Centers - San Antonio

16149:IMS has replaced B3/8X1-1/4C8HC:LJ

QuantityQuantity:1Add To Cart

[![Nylon Locnut Gr.8 3/8-16](https://cdn.partsconnect.rushcare.com/images/370X370/unavailable-image.png)](https://shop.rushtruckcenters.com/products/nylon-locnut-gr-8-3-8-16-42310-ims/1342844)

[Nylon Locnut Gr.8 3/8-16Part #:\\
42310:IMS \| Brand:\\
Imperial](https://shop.rushtruckcenters.com/products/nylon-locnut-gr-8-3-8-16-42310-ims/1342844)Final Price$0.14

2639Available for Delivery

119Available at Rush Truck Centers - San Antonio

42310:IMS has replaced 42310:IMS

QuantityQuantity:1Add To Cart

[![EYE WASH  RE-FILL](https://cdn.partsconnect.rushcare.com/images/370X370/unavailable-image.png)](https://shop.rushtruckcenters.com/products/eye-wash-re-fill-88337-ims/62536695)

[EYE WASH RE-FILLPart #:\\
88337:IMS \| Brand:\\
Imperial](https://shop.rushtruckcenters.com/products/eye-wash-re-fill-88337-ims/62536695)Final Price$19.74

0Available for Delivery

0Available at Rush Truck Centers - San Antonio

QuantityQuantity:1Add To Cart

![Next Related Parts ](https://cdn.rushenterprises.com/ecommerce/vector/angle-right.svg)

##### Need help?

Chat with an agent to search for parts or confirm availability.


Chat Now

No Thanks

USD

- Success
- Warning
- Error
- Close Notification
