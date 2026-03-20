# Presentation Script

## Slide 1. Title
- State the project goal: replacing a conventional data-center cooling load with LNG cold energy.
- Emphasize that the project was rebuilt as a reproducible code-based study.

## Slide 2. Why This Problem Matters
- Data centers concentrate electrical load and cooling demand.
- LNG regasification discards large amounts of cold energy.
- The project asks whether that cold energy can reduce cooling power demand.

## Slide 3. Design Basis
- Total modeled cooling load is 13,476.0 kW.
- Base transport distance is 10 km and the challenge case is 35 km.
- The study keeps explicit source and assumption traceability.

## Slide 4. Baseline Benchmark
- Theoretical minimum power is 1,215.8 kW.
- Reference R-134a compressor power is 4,185.4 kW.
- This baseline is the anchor for judging LNG-system benefit.

## Slide 5. Proposed LNG Cooling Concept
- LNG cold energy cools a secondary-loop refrigerant through a shell-and-tube vaporizer.
- The secondary loop transports cooling duty from the terminal to the IDC.
- The final base-case fluid is ammonia.

## Slide 6. Coolant Screening Result
- Among the feasible fluids, ammonia gives the lowest loop pumping power in the base case.
- Propane and isobutane remain feasible alternatives but are materially weaker in pump power.
- The selection is not arbitrary because the full ranking is reproduced by code.

## Slide 7. Heat Exchanger Design
- The LNG vaporizer is solved with a segmented enthalpy-based model.
- The selected geometry is 500 tubes x 14 m with a shell diameter of about 0.723 m.
- The minimum pinch is held at 10 K.

## Slide 8. Pipeline Result
- Base-case LNG loop pumping power is 13.1 kW.
- Estimated maximum feasible one-way distance is 29.6 km.
- Therefore the 35 km case is not feasible at the base design point.

## Slide 9. Sensitivity Insight
- Distance sensitivity shows where the thermal margin collapses.
- Supply-temperature sensitivity shows that 35 km can be recovered by moving to a warmer supply temperature.
- At -43.1 C supply temperature, the design becomes feasible at 35 km with R-600a (Isobutane).

## Slide 10. Annual Impact
- Annual electricity saving is 36,549.0 MWh/year.
- Annual electricity cost saving is 3,839.5 million KRW/year.
- Annual avoided indirect emissions are 16,757.7 tCO2/year.

## Slide 11. Closing Message
- The 10 km LNG cold-energy design is technically feasible and energetically attractive.
- The 35 km case is the real design boundary test, not a simple extension of the base case.
- The codebase now supports traceable report writing and future design refinement.