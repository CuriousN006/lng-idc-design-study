# Presentation Script

## Slide 1. Title and Core Message
- Open with the design question: can LNG cold energy replace a conventional data-center cooling duty?
- Emphasize that the project is now a reproducible, code-based engineering study rather than a one-off spreadsheet.
- Highlight the three anchor numbers immediately: cooling load 13,476.0 kW, baseline compressor power 4,185.4 kW, LNG pump power 13.1 kW.

## Slide 2. Design Question and Basis
- Frame the assignment constraints before showing any design result.
- Use the modeled cooling load and the transport-distance requirement as the two hardest assignment constraints.
- Call out that sources and assumptions are explicitly tracked inside the project repository.

## Slide 3. System Concept
- Explain the architecture in one sentence: LNG cold energy chills a secondary loop, and that loop transports duty to the IDC.
- Mention the two design bottlenecks: vaporizer pinch and long-distance transport penalty.
- State the current base-case fluid choice: R-717 (Ammonia).

## Slide 4. Benchmark Against the Reference Cycle
- Theoretical minimum power is 1,215.8 kW.
- Reference R-134a compressor power is 4,185.4 kW.
- The modeled LNG loop pump demand is only 13.1 kW, which defines the main energy argument.

## Slide 5. Coolant Selection
- Present R-717 (Ammonia) as the base-case winner, not as an arbitrary choice but as the best trade-off in the modeled ranking.
- Explain that the screening compares feasibility, pumping demand, heat-exchanger scale, and downstream annual benefit.
- Position propane and isobutane as useful alternatives rather than discarded options.

## Slide 6. Transport-Distance Constraint
- State the base result clearly: maximum feasible one-way distance is about 29.6 km.
- Therefore the 35 km case is not feasible at the current design point.
- Use this as a design insight, not as a failure: transport distance is the real system constraint after the base 10 km case closes.

## Slide 7. Temperature Trade-off
- Explain that a warmer supply temperature increases transport feasibility but also changes the fluid preference and pumping penalty.
- Show that recovering 35 km is possible only by moving the operating point, not by assuming the base design magically stretches that far.
- Mention the recovery point explicitly: at -43.1 C supply temperature, the design becomes feasible at 35 km with R-600a (Isobutane).

## Slide 8. Annual Impact
- Annual electricity saving is 36,549.0 MWh/year.
- Annual electricity cost saving is 3,839.5 million KRW/year.
- Annual avoided indirect emissions are 16,757.7 tCO2/year.

## Slide 9. Recommendation
- Close with a decision statement: the 10 km LNG cold-energy design is technically feasible and strongly attractive on an energy basis.
- Say explicitly that 35 km requires a changed operating point and should be treated as a design extension, not the base promise.
- End by positioning the project as a reusable design study with traceable sources, assumptions, and scenarios.