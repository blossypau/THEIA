# NASA Space Apps demonstration — 3–5 minutes

Run the launcher from the README and open its printed THEIA URL. Start with a normal local workspace; no demonstration measurements are added there. Use fictional profiles only. Internet is optional for the core replay and pinned NASA POWER reference; public CT download needs the network unless a verified sample was previously downloaded.

| Time | Action | Evidence to show |
|---|---|---|
| 0:00–0:30 | Enable **Synthetic scenario workspace**, select **Astra / Recovery scenario**, open Mission Scenario Mode. | Yellow synthetic banner, isolated SQLite, 150 seeded observations; 30 artificial prior days. |
| 0:30–1:00 | Select replay, set 10 days/tick, **Start automatic scenario**. Pause/resume if desired, then stop at completion. | Actual SQLite inserts: 100 new measurements, 180 context rows, 250 total observations. Text labels identify software data; no live sensor claim. |
| 1:00–1:45 | Mission Overview, then Intelligence Center > fatigue > Independent historical reference. | Final artificial fatigue90 / pulse130 / sleep3; explain reference IDs strictly before the evaluated day, sample count, change and limitations. It is a designed software example, not a physiological model. |
| 1:45–2:30 | Mission Timeline; filter gravity/radiation/wellbeing/communications/environment. | Recorded or simulated context only. Gy/Sv separate; no predicted harm or assumed missing exposure. Distance panel offers theoretical light time and an explicitly local test queue. |
| 2:30–3:15 | Human Body Explorer; select a real structure, rotate/zoom, isolate, opacity and reset. | Existing 826 identifiers. Educational atlas, not an individual's digital twin; linked scalar context is not a measured anatomical change. |
| 3:15–4:15 | Mission Scenario Mode > Generate scenario PDF; inspect/download it. | Same selected profile and stored inputs; quality/provenance, independent reference, HRV demo, context, methods and NASA references. No missing section filled with invented values. |
| 4:15–4:45 | Reset synthetic scenario, verify 150 rows, disable scenario mode. | Normal workspace/provenance unchanged; only isolated seed restored. |

Optional imaging segment: Medical Visualization Lab > public CT expander > fetch verified sample > download > OHIF Upload files > open study. One anonymized CT slice is a viewer test, not radiological interpretation. An OHIF failure leaves all other pages available; recheck/restart the viewer without terminating unknown processes.

Reproducible browser check (development environment additionally needs Playwright Chromium):

```powershell
.venv\Scripts\python.exe scripts/verify_mission_demo.py --url http://127.0.0.1:8507 --output tmp/theia51/browser
```

The check drives the actual automatic replay, profile switch, provenance, anatomy controls, public CT, PDF, all18 pages, reset and responsive viewports. It writes screenshots/results only for synthetic/public fixtures. No physical hardware is required. Do not select real patient files for a public demonstration.
