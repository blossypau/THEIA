# Scientific methods and limits

THEIA is an experimental descriptive platform. Software verification with synthetic/analytic fixtures is not clinical validation, sensor validation, flight qualification or evidence that a hazard caused an individual's change. No diagnosis, treatment, cancer prediction or personalized anatomical reconstruction is implemented.

| Method | Definition and verification | Limit |
|---|---|---|
| Median / IQR | UTC daily means; median and 75th minus 25th percentile, no imputation. Closed-form linear fixtures verify units and values. | Daily aggregation does not recover unobserved sampling or control acquisition conditions. |
| Theil–Sen | Median pairwise slope against actual elapsed days; >=5 observed days. Above 1000 days, disclosed deterministic subsampling bounds quadratic cost. | Descriptive trend, not a prospective clinical forecast. |
| Period comparison | >=5 days per disjoint chosen period; B−A medians; relative change / A only when A != 0. | Missing days retained; zero denominator yields unavailable, not infinity. |
| Historical reference | Exact source AND provenance class strictly before evaluation; >=5 samples on >=5 days. Mean, median, SD(ddof=0), IQR and observed-day coverage disclosed. | No evaluated ID enters its reference. Zero-SD changes flag without infinite z. Coverage measures observed days, not continuous sensor uptime. |
| Retrospective flags | |z|>2.5 and/or Isolation Forest from >=20 samples / >=5 unique values; seed42, contamination auto. | Reference includes evaluated records; explicitly separate from independent baseline. Discrete small distributions can flag many points; flags are not medical abnormalities. |
| Correlation | Pearson r on >=5 paired UTC daily means with variable signals; sources/evidence remain separate. | Exploratory, unadjusted for confounding, autocorrelation or multiple comparisons. No causal interpretation. |
| NN HRV | MeanNN; sample SDNN(ddof=1); RMSSD=sqrt(mean(diff(NN)^2)); pNN50=100*count(abs(diff)>50ms)/N. >=120 intervals, >=120s, 200–3000ms, finite. | NeuroKit convention divides pNN50 by N, not N−1. Four MIT-adapted NumPy formulas; full NeuroKit is not executed. NN classification must be reviewed; optional timestamps check continuity within1ms; marked artifacts/gaps are rejected, not repaired. Never computed from daily bpm. |
| Radiation | Compatible-unit interval integrals/sums per source/instrument/origin/basis; counter differences only if monotonic/consistent; coverage hours exposed. | Gy ≠ Sv. No conversion without radiation/tissue weighting model. Overlap refuses totals. Unknown uncertainty is not zero. No biological risk estimate. |
| Gravity | Recorded phases with explicit interval for physiological comparison; conventional Earth / approximate Moon / mean Mars values; orbital microgravity described as freefall. | Not local acceleration measurement or proof of bone/muscle/ocular change. Point contexts cannot define a comparison period. |
| Light propagation | Explicit assumed path / exact SI c; round trip is twice one-way. | Not real spacecraft latency, ephemeris, link state or communications verification. |

Findings distinguish OBSERVED CHANGE, STATISTICAL ANOMALY, EXPLORATORY ASSOCIATION, INSUFFICIENT DATA and NO VERIFIED SOURCE. Missing observations remain missing. No EEG/PSG/cognitive/omics processing, validated recovery score or clinical risk model is supplied.

## NASA sources: consulted, downloaded and used

- [NASA HRP five hazards](https://www.nasa.gov/hrp/hazards/): consulted; educational framework and report references, not telemetry.
- [NASA POWER data methodology](https://power.larc.nasa.gov/docs/faqs/data/): consulted. Actual fixed-period request downloaded/parsed, plus the checksum-verified Jan1–7 2024 KSC fixture: 21 terrestrial T2M/RH2M/PS values, UTC, C/%/kPa, MERRA2/POWER. Public Earth reanalysis does not measure cabin conditions, radiation dose or astronaut physiology. The pinned manifest contains request/provenance/attribution; use source terms for redistribution.
- [OSD-1 metadata API](https://osdr.nasa.gov/osdr/data/osd/meta/1): actually downloaded and parsed during this release verification: 18 sample rows, study **Expression data from drosophila melanogaster**, adult male Oregon-R fruit flies, whole-organism research, STS-121 factors. Metadata is not human physiology, gene expression analysis or a completed GeneLab pipeline. Returned metadata contains no explicit license field: no blanket reuse license is asserted; consult accession/source terms and cite DOI10.25966/t6db-f633 and the linked publication. Raw assay files are not redistributed by this release.
- [OSD-569](https://osdr.nasa.gov/bio/repo/data/studies/OSD-569), identified by [NASA Inspiration4 dataset catalogue](https://www.nasa.gov/osdr-latest-news-i4-mission-datasets/): human whole-blood research accession link/reference only. No subject files downloaded or processed. Dataset access/reuse conditions are not established by a link.
- GeneLab processing repository: methodological link only. No FASTQ, expression or methylation pipeline was run.
- OHIF public single-slice CT: actually downloaded, byte/pixel hashes verified and rendered; public Barré/OHIF codec-test sample, NOT NASA or a complete diagnostic study. Terms/provenance pinned in `assets/testdata/ohif-gray-ct.json`.

NASA references are not NASA endorsement. No scientific model is claimed validated merely because its calculations pass software tests.
