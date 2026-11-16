"""Read PyPI's published vulnerability metadata for exact lock versions (no installs)."""
import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime,timezone
import json
from pathlib import Path
import re
import requests


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--lock',default='requirements-lock-windows-py314.txt')
    parser.add_argument('--output',default='tmp/theia51/dependency-advisories.json')
    args=parser.parse_args()
    requirements=[]
    for line in Path(args.lock).read_text().splitlines():
        match=re.fullmatch(r'([\w.-]+)==([^\s]+)',line.strip())
        if match:requirements.append(match.groups())
    def check(item):
        name,version=item;url=f'https://pypi.org/pypi/{name}/{version}/json'
        try:
            response=requests.get(url,timeout=10);response.raise_for_status();payload=response.json()
            return dict(name=name,version=version,status='queried',advisories=[dict(id=v.get('id'),aliases=v.get('aliases'),link=v.get('link'),fixed_in=v.get('fixed_in')) for v in payload['vulnerabilities']])
        except (requests.RequestException,ValueError,KeyError) as exc:return dict(name=name,version=version,status='UNVERIFIED',error=type(exc).__name__)
    with ThreadPoolExecutor(max_workers=4) as pool:results=list(pool.map(check,requirements))
    report=dict(checked_at=datetime.now(timezone.utc).isoformat(),source='PyPI release JSON vulnerability metadata',
        scope='Published advisories for exact lock versions, not proof of absence of vulnerabilities or a source-code security audit',
        packages=results,unverified=sum(r['status']=='UNVERIFIED' for r in results),
        affected_packages=sum(bool(r.get('advisories')) for r in results))
    output=Path(args.output);output.parent.mkdir(parents=True,exist_ok=True);output.write_text(json.dumps(report,indent=2))
    print(json.dumps({k:v for k,v in report.items() if k!='packages'},indent=2),flush=True)
    if report['unverified'] or report['affected_packages']:raise SystemExit(1)


if __name__=='__main__':main()
