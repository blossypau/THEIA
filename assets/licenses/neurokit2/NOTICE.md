# Limited NeuroKit2 adaptation

`integrations/cardiovascular.py` adapts four temporal statistics from NeuroKit2 0.3.0, `neurokit2/hrv/hrv_time.py` (MIT, Dominique Makowski and contributors): MeanNN, sample SDNN (ddof=1), RMSSD and pNN50. The last uses the upstream denominator N intervals, not N-1 differences. See LICENSE.

Source: https://github.com/neuropsychology/NeuroKit/blob/v0.3.0/neurokit2/hrv/hrv_time.py

The full package is not executed. A compatibility trial on this Windows/Python 3.14 environment failed because Application Control blocked a PyWavelets DLL. No policy was changed or bypassed. This explicitly scoped NumPy adaptation avoids that unrelated dependency, rejects missing/invalid intervals, and does not implement ECG/PPG cleaning, beat detection, artifact correction, frequency-domain HRV or clinical interpretation.

Independent analytic tests verify constant/alternating sequences and the documented formula conventions. Those tests do not imply equivalence of the full NeuroKit pipeline or clinical validation.
