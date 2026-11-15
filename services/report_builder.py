"""Scientific PDF built from one SQLite read snapshot, with no fabricated missing values."""
from datetime import datetime,timezone
import json
import hashlib
from typing import Any,cast
from pathlib import Path
from xml.sax.saxutils import escape
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet,ParagraphStyle
from reportlab.platypus import SimpleDocTemplate,Paragraph,Spacer,Table,TableStyle,PageBreak,KeepTogether
from reportlab.graphics.shapes import Drawing,String
from reportlab.graphics.charts.lineplots import LinePlot
from database.database import SessionLocal
from database.models import AstronautProfile,ScientificAnalysisRecord
from database.repository import ensure_astronaut,save_scientific_report
from database.measurements import measurement_frame
from intelligence.engine import analyze
from intelligence.historical import historical_analysis
from services.scientific_health import longitudinal_analysis
from services.space_context import context_rows,radiation_summary,HAZARDS
from config.settings import ROOT_DIR

INK=colors.HexColor('#0b263b');CYAN=colors.HexColor('#087f8c');PALE=colors.HexColor('#edf5f8')


def report_input_fingerprint(session,astronaut_id,start=None,end=None):
    core=analyze(session,astronaut_id,start,end,persist=False)
    historical=historical_analysis(session,astronaut_id,start,end,persist=False)
    context=[r.identity_key for r in context_rows(session,astronaut_id)]
    nn=[(r.id,r.result_summary) for r in session.query(ScientificAnalysisRecord).filter_by(analysis_type='nn_time_domain').all() if (r.dataset_source or '').startswith(f'profile:{astronaut_id}:')]
    return hashlib.sha256(json.dumps([core['fingerprint'],historical['fingerprint'],context,nn,'report5']).encode()).hexdigest()


def generate_pdf_report(session=None,output_path=None,astronaut_id=None,start=None,end=None):
    own=session is None;session=session or SessionLocal()
    start=start.astimezone(timezone.utc).replace(tzinfo=None) if start is not None and start.tzinfo else start
    end=end.astimezone(timezone.utc).replace(tzinfo=None) if end is not None and end.tzinfo else end
    try:
        # Explicit BEGIN gives subsequent reads one SQLite snapshot even with concurrent acquisition.
        connection=session.connection()
        if connection.dialect.name=='sqlite' and not connection.connection.driver_connection.in_transaction:
            connection.exec_driver_sql('BEGIN')
        astronaut=ensure_astronaut(session) if astronaut_id is None else session.get(AstronautProfile,astronaut_id)
        if astronaut is None:raise ValueError('Unknown astronaut')
        analysis=analyze(session,astronaut.id,start,end,persist=False)
        frame=measurement_frame(session,astronaut.id,start=start,end=end)
        science=longitudinal_analysis(session,astronaut.id,persist=False,start=start,end=end)
        history=historical_analysis(session,astronaut.id,start=start,end=end,persist=False)
        context=[r for r in context_rows(session,astronaut.id) if (start is None or r.timestamp>=start.replace(tzinfo=None)) and (end is None or r.timestamp<=end.replace(tzinfo=None))]
        nn_rows=session.query(ScientificAnalysisRecord).filter_by(analysis_type='nn_time_domain').order_by(ScientificAnalysisRecord.run_timestamp.desc()).all()
        nn=[]
        for row in nn_rows:
            if not (row.dataset_source or '').startswith(f'profile:{astronaut.id}:'):continue
            payload=json.loads(row.result_summary)
            if session.info.get('scenario') and payload.get('source')!='SIMULATED_DATA':continue
            recording=payload.get('recording_start')
            if start is not None or end is not None:
                if not recording:continue
                when=datetime.fromisoformat(recording)
                if start is not None and when<start.replace(tzinfo=None):continue
                if end is not None and when>end.replace(tzinfo=None):continue
            nn.append(payload)
            if len(nn)==1:break
        root=Path(session.info['scenario_dir'])/'reports' if session.info.get('scenario') else ROOT_DIR/'data/processed'
        path=Path(output_path) if output_path else root/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%f')/'theia_report.pdf'
        path.parent.mkdir(parents=True,exist_ok=True)
        styles=getSampleStyleSheet()
        styles.add(ParagraphStyle(name='Caption5',fontName='Helvetica',fontSize=8,leading=11,textColor=colors.HexColor('#40566a'),spaceAfter=7))
        styles['Title'].textColor=INK;styles['Title'].fontSize=30;styles['Title'].leading=36
        styles['Heading1'].textColor=INK;styles['Heading1'].spaceBefore=14
        styles['Heading2'].textColor=CYAN;styles['BodyText'].fontSize=9;styles['BodyText'].leading=13
        story: list[Any]=[]
        def text(value,style='BodyText'):
            story.append(Paragraph(escape(str(value)),styles[style]));story.append(Spacer(1,5))
        def heading(value):text(value,'Heading1')
        def table(headers,rows,widths=None):
            if not rows:text('NO DATA for this section.');return
            data=[[Paragraph(escape(str(cell)),styles['Caption5']) for cell in row] for row in [headers]+rows]
            widget=Table(data,colWidths=widths or [528/len(headers)]*len(headers),repeatRows=1,hAlign='LEFT')
            widget.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),PALE),('LINEBELOW',(0,0),(-1,0),1,CYAN),
                ('ROWBACKGROUNDS',(0,1),(-1,-1),[colors.white,colors.HexColor('#f7fafb')]),('VALIGN',(0,0),(-1,-1),'TOP'),
                ('LEFTPADDING',(0,0),(-1,-1),7),('RIGHTPADDING',(0,0),(-1,-1),7),('TOPPADDING',(0,0),(-1,-1),6)]))
            story.append(widget);story.append(Spacer(1,10))
        text('THEIA / SPACE HUMAN HEALTH','Heading2')
        text('Mission research report','Title')
        text('EXPERIMENTAL / NOT FOR DIAGNOSTIC OR OPERATIONAL DECISIONS','Caption5')
        story.append(Spacer(1,24))
        table(['Profile','Mission','Mission day'],[[astronaut.name,astronaut.mission_id,astronaut.mission_day]])
        gravity=[json.loads(r.payload) for r in context if r.kind=='gravity']
        text('Latest recorded phase: '+(gravity[-1]['phase']+' / '+gravity[-1]['environment'] if gravity else 'NO RECORDED CONTEXT'))
        text('SYNTHETIC WORKSPACE: every simulated observation remains labeled.' if session.info.get('scenario') else 'LOCAL OBSERVATIONS: provenance labels are not independent clinical verification.','Heading2')
        text(f"Observed period UTC: {analysis['period'].get('first','NO DATA')} to {analysis['period'].get('last','NO DATA')}")
        text('Generated UTC: '+datetime.now(timezone.utc).isoformat(),'Caption5')
        heading('Executive research summary')
        total=analysis['quality']['total'];excluded=analysis['quality']['excluded']
        flags=sum(o['flagged'] for item in history['signals'] for o in item['observations'])
        text(f'{total} observations; {excluded} excluded by shared validation. {flags} historical deviations flagged for data review. These are statistical patterns, not diagnoses.')
        text('No missing exposure, sensor, anatomy, sleep-stage or clinical value is invented. NASA references provide educational context, not live telemetry.')
        text('Action plan','Heading2');text('Review provenance, acquisition conditions and missing coverage. Discuss material findings with qualified mission/research staff; this software does not prescribe treatment or autonomous mission decisions.')
        text('Analysis snapshot: '+analysis['fingerprint'],'Caption5')
        text('Historical snapshot: '+history['fingerprint'],'Caption5')
        bundle_hash=hashlib.sha256(json.dumps([analysis['fingerprint'],history['fingerprint'],[r.identity_key for r in context],nn,'report5.0-r1'],sort_keys=True).encode()).hexdigest()
        text('Report bundle SHA256: '+bundle_hash,'Caption5')
        story.append(PageBreak())
        heading('Data quality and provenance')
        table(['Source','Records'],[[k,v] for k,v in analysis['quality']['sources'].items()],[400,128])
        text('VALID means schema/range/unit checks. It does not certify calibration, artifact-free acquisition or clinical validity. Existing sensor-labeled records without capture receipts remain declared provenance.')
        heading('Independent personal reference')
        text(history['limitations'])
        table(['Signal / source','Reference (mean / median / SD)','Samples / days','Evaluated result'],[
            [f"{i['metric']} / {i['source']} ({i['unit']})",' / '.join(f'{v:.3f}' if v is not None else 'NO DATA' for v in [i['mean'],i['median'],i['std']]),
             f"{i['samples']} / {i['days']} ({i['status']})",'; '.join(f"{o['timestamp']}: {o['value']:g}; delta={o['delta']}; flagged={o['flagged']}" for o in i['observations'][-3:])]
            for i in history['signals']],[135,140,90,163])
        heading('Source-separated longitudinal context')
        text(science['method'])
        table(['Signal / source','Median / IQR','Observed days','Theil-Sen / day'],[
            [f"{i['metric']} / {i['source']} ({i['unit']})",f"{i['median']:.3f} / {i['iqr']:.3f}",f"{i['days']}/{i['span_days']}",i['theil_sen_per_day'] if i['theil_sen_per_day'] is not None else 'Insufficient days'] for i in science['signals']],[190,115,100,123])
        text(science['limitations'],'Caption5')
        for key,item in analysis['metrics'].items():
            block_start=len(story)
            text(f"{item['metric']} / {item['cohort']} / {item['unit']}",'Heading2')
            text(f"Samples: {item['samples']} | Latest: {item['latest']:.3f} {item['unit']} | Mean: {item['mean']:.3f} | Standard deviation: {item['std']:.3f}")
            rows=frame[frame.id.isin(item['measurement_ids'])]
            if len(rows)>=2:
                drawing=Drawing(510,165);chart=cast(Any,LinePlot());chart.x=45;chart.y=28;chart.width=445;chart.height=120
                origin=rows.timestamp.min();points=[((r.timestamp-origin).total_seconds()/86400,float(r.value)) for r in rows.itertuples()]
                chart.data=[points];chart.lines[0].strokeColor=CYAN;chart.lines[0].strokeWidth=1.3
                chart.xValueAxis.valueMin=0;chart.xValueAxis.valueMax=max(points[-1][0],1)
                chart.xValueAxis.labels.fontSize=7;chart.yValueAxis.labels.fontSize=7
                drawing.add(chart);drawing.add(String(45,5,'Days since first observation (UTC); '+item['unit'],fontSize=8))
                story.append(drawing)
            text(f"Retrospective flags: {len(item['anomalies'])}. This historical-compatible method includes the evaluated observation in the window distribution.",'Caption5')
            for flag in item['anomalies'][-3:]:text(f"{flag['timestamp']} / {flag['value']} {item['unit']} / |z|={flag['z_score']:.3f} / {', '.join(flag['methods'])}",'Caption5')
            story[block_start:]=[KeepTogether(story[block_start:])]
        nn_start=len(story)
        heading('Reviewed NN interval HRV')
        text('Latest compatible analysis shown; additional recordings remain in local SQLite.','Caption5')
        if not nn:text('NO COMPATIBLE NN ANALYSIS. HRV is never calculated from daily pulse. Date-scoped reports exclude recordings without known recording dates.')
        for item in nn:
            text(f"{item['source']} / {item['intervals']} NN intervals / {item['duration_seconds']:.1f} seconds / recording start {item.get('recording_start','not supplied')}")
            table(['Statistic','Value','Unit'],[[k,f'{v:.4f}','%' if k=='HRV_pNN50' else 'ms'] for k,v in item['metrics'].items()])
            text(item['quality']);text(item['limitations'],'Caption5');text('NN input SHA256: '+item['sha256'],'Caption5')
        story[nn_start:]=[KeepTogether(story[nn_start:])]
        heading('Recorded mission context')
        def context_description(row):
            p=json.loads(row.payload)
            if row.kind=='gravity':return p['environment']+' / '+p['phase']
            if row.kind=='communications':return p['state']+' / assumed path '+str(p.get('distance_km'))+' km (SIMULATED)'
            if row.kind=='radiation':return f"{p['origin']} / {p['basis']} / {p['quantity']}: {p['value']} {p['unit']}; uncertainty {p.get('uncertainty') if p.get('uncertainty') is not None else 'not supplied'}"
            return f"{p.get('metric','Recorded context')}: {p.get('value','NO DATA')} {p.get('unit','self-report units')}"
        table(['Kind / time UTC','Source / quality','Recorded observation'],[[f'{r.kind} / {r.timestamp}',f'{r.source} / {r.quality}',context_description(r)] for r in context[-15:]],[120,125,283])
        text(f'{len(context)} context records in selected scope; latest 15 shown. Instruments: '+', '.join(sorted({r.instrument for r in context}))+'. Full records remain in local SQLite.','Caption5')
        dose=radiation_summary([r for r in context if r.kind=='radiation'])
        if dose:
            text('Dosimetry (not a risk estimate)','Heading2')
            table(['Source / instrument / origin','Basis / unit','Integrated intervals','Cumulative change / quality'],[
                [f"{i['source']} / {i['instrument']} / {i['origin']}",f"{i['basis']} / {i['unit']}",i['interval_sum'] if i['interval_sum'] is not None else 'NO VALID SUM',
                 f"{i['cumulative_change']} / overlaps={i['overlap']}; counter inconsistency={i['counter_reset_or_inconsistent']}"] for i in dose],[180,85,100,163])
            text('Gy and Sv are not interconverted. Cumulative readings are differenced, not added; overlapping intervals refuse a sum. Unreported uncertainty is not zero.','Caption5')
            for item in dose:text(f"{item['origin']} / {item['source']}: recorded intervals {item['recorded_hours']} h within {item['window_hours']} h span. No exposure is inferred for uncovered time.",'Caption5')
        else:text('NO RECORDED DOSIMETRY. No radiation exposure or individual risk is inferred.')
        heading('Exploratory relationships')
        if not analysis['relationships']:text('Insufficient paired days for correlations.')
        table(['Signals','Source cohort','Paired days','Pearson r'],[[r['left']+' / '+r['right'],r['cohort'],r['paired_days'],f"{r['pearson_r']:.4f}"] for r in analysis['relationships']],[240,100,90,98])
        text('UTC daily means. Exploratory association, not causality; no adjustment for confounding or multiple comparisons.','Caption5')
        methods_start=len(story)
        heading('Methods, parameters and limitations')
        text(json.dumps(analysis['parameters']));text(analysis['limitations']);text(history['limitations'])
        text('Reference history is strictly earlier than evaluated timestamps and remains source-separated. Report read queries use one SQLite transaction. No global medical risk score, autonomous clinical recommendation or validated spacecraft alert is generated.')
        story[methods_start:]=[KeepTogether(story[methods_start:])]
        reference_start=len(story)
        heading('Scientific references')
        for definition in HAZARDS.values():text(definition['url'],'Caption5')
        for url in ['https://www.nasa.gov/hrp/risks/','https://www.nasa.gov/hrp/ongoing-hrp-research/',
            'https://www.nasa.gov/wp-content/uploads/2024/01/human-health-and-performance.pdf',
            'https://github.com/neuropsychology/NeuroKit/blob/v0.3.0/neurokit2/hrv/hrv_time.py',
            'https://scikit-learn.org/stable/modules/generated/sklearn.ensemble.IsolationForest.html']:text(url,'Caption5')
        story[reference_start:]=[KeepTogether(story[reference_start:])]
        def footer(canvas,doc):
            canvas.setStrokeColor(CYAN);canvas.line(42,39,570,39);canvas.setFillColor(INK);canvas.setFont('Helvetica',8)
            canvas.drawString(42,25,'THEIA 5.0 / experimental scientific observations');canvas.drawRightString(570,25,f'Page {doc.page}')
        SimpleDocTemplate(str(path),pagesize=letter,rightMargin=42,leftMargin=42,topMargin=38,bottomMargin=52,pageCompression=0).build(story,onFirstPage=footer,onLaterPages=footer)
        save_scientific_report(session,'mission_health_pdf',f'THEIA Mission Health Report - {astronaut.name}',
            json.dumps({'fingerprint':analysis['fingerprint'],'historical_fingerprint':history['fingerprint'],'report_bundle_sha256':bundle_hash,'astronaut_id':astronaut.id,
                'measurement_ids':frame.id.tolist(),'context_ids':[r.id for r in context]}),str(path),'NASA HRP hazards; local observations; documented statistical methods')
        return path
    finally:
        if own:session.close()
