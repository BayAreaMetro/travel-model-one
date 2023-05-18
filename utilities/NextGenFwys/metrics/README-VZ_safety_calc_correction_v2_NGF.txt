Calculate Safe1 metrics from MTC model outputs
- Lowness correction: use CollisionLookupFINAL.xlsx to adjust fatalities and injuries based on VMT, ft (facility type), and at (area type)
  - The lowness correction is used for all scenrios
- Speed correction: use speed exponent to adjust fatalities and injuries based on the speed reduction from a base scenario
  - literature reviews of the speed correction: https://www.toi.no/getfile.php?mmfileid=13206; https://www.fhwa.dot.gov/publications/research/safety/17098/003.cfm
  - documentation of the speed correction: P.49 of the PBA performance report - https://www.planbayarea.org/sites/default/files/documents/Plan_Bay_Area_2050_Performance_Report_October_2021.pdf
  - it should be used to all scenrios involving speed reduction projects like Vision Zero

Histroical version of this script:
- The original R script was created by Raleigh and used for PBA 50. It is saved on Box (https://mtcdrive.app.box.com/file/748326296021?s=nzm9twmohfblc35vddlnv9wd6zw04zdv).
- The original R script was also pushed to MTC's GitHub: https://github.com/BayAreaMetro/travel-model-one/commit/731ee7495f22d13e83086ffade6ace3acd364b06

In Next Generation Freeway project, the project team decided to update the R script to the current version, including:
- the ability to separate freeway and non-freeway metrics
- the ability to separate EPC and non-EPC metrics

This updated is conducted by Lufeng Lin. Feel free to reach out for questions.

The entire script has three parts:
1. lowness correction for 2015 base scenario: the calculation for 2015 base year is based on some assumptions. The result of 2015 base year is used in the following parts.
2. lowness_correction_loop: this function ONLY has lowness correction. It should be used for No Project scenario and other scenarios without speed reduction.
3. lowness_speed_correction_loop: this function has both lowness and speed correction. In NGF, it is used for all pathways.
