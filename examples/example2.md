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

Source URL: https://www.finditparts.com/products/3942092/pewag-chains-h4247sc?srsltid=AfmBOop24IaqTXbRXemHkmVIyWxifOWMDMH5CVRyK5zGuUhXqiJHyV7c
Source tier (heuristic): ecommerce
Weak prior hint (SERP title, optional): PEWAG CHAINS H4247SC Tire Snow Chain - Dual
Weak prior hint (SERP snippet, optional): PEWAG CHAINS H4247SC Tire Snow Chain - Dual. (0) Write a Review. H4247SC by PEWAG CHAINS - Tire Snow Chain - Dual. MSRP: $842.02. $282.99.
Rule-based MPN detected in scrape: True
Rule-based manufacturer match in scrape: True

Scraped PDP content (markdown excerpt):
[![FinditParts Logo](https://d2jocyn8o0ggnq.cloudfront.net/static-assets/frontend/finditparts_logo_large-6b924bd65f6921c676abbb116a76133c65e373c410cce6bcdfeb5fa3ad10b164.svg)](https://www.finditparts.com/)Find a Part[Shop by Manufacturer](https://www.finditparts.com/t/2/manufacturer/) [Shop by Category](https://www.finditparts.com/categories/) [Shop by Truck](https://www.finditparts.com/fits/)

[Track/Return Order](https://www.finditparts.com/orders/lookup) [Contact Us](https://www.finditparts.com/contact) [About FinditParts](https://www.finditparts.com/about) [Join FinditParts Pro](https://www.finditparts.com/pro) [Industry News & Insights](https://www.finditparts.com/products/3942092/pewag-chains-h4247sc#)

Need help? We're here!

[(888) 312-8812](tel:888-312-8812)

[Login](https://www.finditparts.com/login) [Signup](https://www.finditparts.com/signup)

[Back to Main Menu](https://www.finditparts.com/products/3942092/pewag-chains-h4247sc#)

[Average Truck Driver Salaries](https://www.finditparts.com/blog/average-truck-driver-salary) [Truck Stop Safety](https://www.finditparts.com/blog/are-truck-stops-safe) [Dangerous Truck Roads](https://www.finditparts.com/blog/dangerous-truck-roads) [Safe Driving Around Semi Trucks](https://www.finditparts.com/blog/safe-driving-around-semi-trucks) [Truck Accident Statistics](https://www.finditparts.com/blog/truck-accident-statistics) [Semi Truck Repair & Maintenance](https://www.finditparts.com/blog/categories/semi-truck-repair-maintenance) [Trucking Business Tips](https://www.finditparts.com/blog/categories/trucking-business-tips) [View All Articles →](https://www.finditparts.com/blog)

[Electrical & Lighting](https://www.finditparts.com/top-sellers/electrical-lighting) [Engine & Drivetrain](https://www.finditparts.com/top-sellers/engine-drivetrain) [Brakes, Suspension, & Steering](https://www.finditparts.com/top-sellers/brakes-suspension-steering) [Body](https://www.finditparts.com/top-sellers/body) [Tire & Wheel](https://www.finditparts.com/top-sellers/tire-wheel) [Other Parts & Supplies](https://www.finditparts.com/top-sellers/other-parts-supplies) [Top Searches](https://www.finditparts.com/d)

[Electrical, Lighting and Body](https://www.finditparts.com/categories/electrical-lighting-and-body/)

- [Air Bag System](https://www.finditparts.com/categories/electrical-lighting-and-body/air-bag-system/)
- [Anti-Theft System](https://www.finditparts.com/categories/electrical-lighting-and-body/anti-theft-system/)
- [Body Actuators and Motors](https://www.finditparts.com/categories/electrical-lighting-and-body/body-actuators-and-motors/)
- [Body Wiring Harness and Components](https://www.finditparts.com/categories/electrical-lighting-and-body/body-wiring-harness-and-components/)
- [Brackets, Flanges and Hangers](https://www.finditparts.com/categories/electrical-lighting-and-body/brackets-flanges-and-hangers/)
- [Control Modules](https://www.finditparts.com/categories/electrical-lighting-and-body/control-modules/)
- [Electrical ConnectorsTOP SELLER](https://www.finditparts.com/categories/electrical-lighting-and-body/electrical-connectors/)
- [Electrical Sockets](https://www.finditparts.com/categories/electrical-lighting-and-body/electrical-sockets/)
- [Flasher Units, Fuses, and Circuit Breakers](https://www.finditparts.com/categories/electrical-lighting-and-body/flasher-units-fuses-and-circuit-breakers/)
- [Floor](https://www.finditparts.com/categories/electrical-lighting-and-body/floor/)
- [Gaskets and Sealing Systems](https://www.finditparts.com/categories/electrical-lighting-and-body/gaskets-and-sealing-systems/)
- [Glass, Windows and Related Components](https://www.finditparts.com/categories/electrical-lighting-and-body/glass-windows-and-related-components/)
- [Hardware, Fasteners and Fittings](https://www.finditparts.com/categories/electrical-lighting-and-body/hardware-fasteners-and-fittings/)
- [Lighting - ExteriorTOP SELLER](https://www.finditparts.com/categories/electrical-lighting-and-body/lighting-exterior/)
- [Lighting - Instrumentation](https://www.finditparts.com/categories/electrical-lighting-and-body/lighting-instrumentation/)
- [Lighting - Interior](https://www.finditparts.com/categories/electrical-lighting-and-body/lighting-interior/)
- [Mobile Multi-Media](https://www.finditparts.com/categories/electrical-lighting-and-body/mobile-multi-media/)
- [Power Outlets](https://www.finditparts.com/categories/electrical-lighting-and-body/power-outlets/)
- [Relays](https://www.finditparts.com/categories/electrical-lighting-and-body/relays/)
- [Resistors](https://www.finditparts.com/categories/electrical-lighting-and-body/resistors/)
- [Sensors](https://www.finditparts.com/categories/electrical-lighting-and-body/sensors/)
- [Steering Wheel](https://www.finditparts.com/categories/electrical-lighting-and-body/steering-wheel/)
- [Switches, Solenoids and ActuatorsTOP SELLER](https://www.finditparts.com/categories/electrical-lighting-and-body/switches-solenoids-and-actuators/)
- [Towing](https://www.finditparts.com/categories/electrical-lighting-and-body/towing/)
- [Trunk Lid and Compartment](https://www.finditparts.com/categories/electrical-lighting-and-body/trunk-lid-and-compartment/)
- [Warning Buzzers](https://www.finditparts.com/categories/electrical-lighting-and-body/warning-buzzers/)
- [Wire, Cable and Related Components](https://www.finditparts.com/categories/electrical-lighting-and-body/wire-cable-and-related-components/)

[Electrical, Charging and Starting](https://www.finditparts.com/categories/electrical-charging-and-starting/)

- [Alternator / Generator and Related Components](https://www.finditparts.com/categories/electrical-charging-and-starting/alternator-generator-and-related-components/)
- [Battery and Related Components](https://www.finditparts.com/categories/electrical-charging-and-starting/battery-and-related-components/)
- [Brackets, Flanges and Hangers](https://www.finditparts.com/categories/electrical-charging-and-starting/brackets-flanges-and-hangers/)
- [Electrical ConnectorsTOP SELLER](https://www.finditparts.com/categories/electrical-charging-and-starting/electrical-connectors/)
- [Hardware, Fasteners and Fittings](https://www.finditparts.com/categories/electrical-charging-and-starting/hardware-fasteners-and-fittings/)
- [Relays](https://www.finditparts.com/categories/electrical-charging-and-starting/relays/)
- [Sensors](https://www.finditparts.com/categories/electrical-charging-and-starting/sensors/)
- [Starter and Related Components](https://www.finditparts.com/categories/electrical-charging-and-starting/starter-and-related-components/)
- [Switches, Solenoids and ActuatorsTOP SELLER](https://www.finditparts.com/categories/electrical-charging-and-starting/switches-solenoids-and-actuators/)
- [Voltage Regulator](https://www.finditparts.com/categories/electrical-charging-and-starting/voltage-regulator/)

Close

[Engine](https://www.finditparts.com/categories/engine/)

- [PAI Engine Kits](https://www.finditparts.com/pai-engine-kits/)
- [Cylinder Block Components](https://www.finditparts.com/categories/engine/cylinder-block-components/)
- [FiltersTOP SELLER](https://www.finditparts.com/categories/engine/filters/)
- [Gaskets and Sealing Systems](https://www.finditparts.com/categories/engine/gaskets-and-sealing-systems/)
- [Hardware, Fasteners and Fittings](https://www.finditparts.com/categories/engine/hardware-fasteners-and-fittings/)
- [Switches, Solenoids and Actuators](https://www.finditparts.com/categories/engine/switches-solenoids-and-actuators/)
- [Valve Train Components](https://www.finditparts.com/categories/engine/valve-train-components/)

[Driveline and Axles](https://www.finditparts.com/categories/driveline-and-axles/)

- [Bearings](https://www.finditparts.com/categories/driveline-and-axles/bearings/)
- [Differential](https://www.finditparts.com/categories/driveline-and-axles/differential/)
- [Drive Shaft](https://www.finditparts.com/categories/driveline-and-axles/drive-shaft/)
- [Gaskets and Sealing Systems](https://www.finditparts.com/categories/driveline-and-axles/gaskets-and-sealing-systems/)
- [Hardware, Fasteners and Fittings](https://www.finditparts.com/categories/driveline-and-axles/hardware-fasteners-and-fittings/)
- [Hubs and Related Components](https://www.finditparts.com/categories/driveline-and-axles/hubs-and-related-components/)
- [Power Take Off (PTO) and Components](https://www.finditparts.com/categories/driveline-and-axles/power-take-off-pto-and-components/)
- [Service Kits](https://www.finditparts.com/categories/driveline-and-axles/service-kits/)
- [Switches, Solenoids and Actuators](https://www.finditparts.com/categories/driveline-and-axles/switches-solenoids-and-actuators/)
- [Wheel Bearings, Seals, and Related Components](https://www.finditparts.com/categories/driveline-and-axles/wheel-bearings-seals-and-related-components/)

[Air and Fuel Delivery](https://www.finditparts.com/categories/air-and-fuel-delivery/)

- [Carburetion](https://www.finditparts.com/categories/air-and-fuel-delivery/carburetion/)
- [FiltersTOP SELLER](https://www.finditparts.com/categories/air-and-fuel-delivery/filters/)
- [Fuel Injection System and Related Components](https://www.finditparts.com/categories/air-and-fuel-delivery/fuel-injection-system-and-related-components/)
- [Fuel Pumps and Related Components](https://www.finditparts.com/categories/air-and-fuel-delivery/fuel-pumps-and-related-components/)
- [Fuel Storage](https://www.finditparts.com/categories/air-and-fuel-delivery/fuel-storage/)
- [Hardware, Fasteners and Fittings](https://www.finditparts.com/categories/air-and-fuel-delivery/hardware-fasteners-and-fittings/)

[Transmission](https://www.finditparts.com/categories/transmission/)

- [Gaskets and Sealing Systems](https://www.finditparts.com/categories/transmission/gaskets-and-sealing-systems/)
- [Hardware, Fasteners and Fittings](https://www.finditparts.com/categories/transmission/hardware-fasteners-and-fittings/)
- [Manual Transmission Components](https://www.finditparts.com/categories/transmission/manual-transmission-components/)
- [Transmission Hard Parts](https://www.finditparts.com/categories/transmission/transmission-hard-parts/)

[Exhaust](https://www.finditparts.com/categories/exhaust/)

- [Exhaust and Tail Pipes](https://www.finditparts.com/categories/exhaust/exhaust-and-tail-pipes/)
- [Hardware, Fasteners and Fittings](https://www.finditparts.com/categories/exhaust/hardware-fasteners-and-fittings/)

[Ignition](https://www.finditparts.com/categories/ignition/)

- [Secondary Ignition](https://www.finditparts.com/categories/ignition/secondary-ignition/)

[Emission Control](https://www.finditparts.com/categories/emission-control/)

- [Emission Components](https://www.finditparts.com/categories/emission-control/emission-components/)
- [Sensors](https://www.finditparts.com/categories/emission-control/sensors/)

[Belts and Cooling](https://www.finditparts.com/categories/belts-and-cooling/)

- [Accessory Drive Belt System ComponentsTOP SELLER](https://www.finditparts.com/categories/belts-and-cooling/accessory-drive-belt-system-components/)
- [Cooling Fan, Clutch and Motor](https://www.finditparts.com/categories/belts-and-cooling/cooling-fan-clutch-and-motor/)
- [Gaskets and Sealing Systems](https://www.finditparts.com/categories/belts-and-cooling/gaskets-and-sealing-systems/)
- [Hardware, Fasteners and Fittings](https://www.finditparts.com/categories/belts-and-cooling/hardware-fasteners-and-fittings/)
- [Hoses and Pipes](https://www.finditparts.com/categories/belts-and-cooling/hoses-and-pipes/)
- [Radiators, Coolers and Related Components](https://www.finditparts.com/categories/belts-and-cooling/radiators-coolers-and-related-components/)
- [Thermostat and Housing](https://www.finditparts.com/categories/belts-and-cooling/thermostat-and-housing/)
- [Water Pump and Related Components](https://www.finditparts.com/categories/belts-and-cooling/water-pump-and-related-components/)

[HVAC](https://www.
