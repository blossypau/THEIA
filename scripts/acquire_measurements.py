"""Explicit local acquisition worker; does not start any public network listener."""
import argparse
import asyncio
import sys
import time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent.parent))
from database.database import init_db,SessionLocal
from database.models import AstronautProfile
from integrations.acquisition import FolderConnector,APIConnector,SyntheticConnector,ingest,record_error


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source',choices=['folder','api','ble','synthetic'],required=True)
    parser.add_argument('--address',help='Explicit folder, HTTPS URL or selected BLE address')
    parser.add_argument('--profile',type=int)
    parser.add_argument('--workspace',help='UUID of isolated synthetic workspace (required for synthetic)')
    parser.add_argument('--ticks',type=int,default=0,help='0 runs until Ctrl+C; otherwise bounded poll count')
    args=parser.parse_args()
    if args.source=='synthetic':
        if not args.workspace:parser.error('Synthetic acquisition requires --workspace UUID')
        from services.scenario import scenario_factory
        factory=scenario_factory(args.workspace);profile=args.profile or 1
        connector=SyntheticConnector();connector.command('start')
    else:
        if not args.address or not args.profile:parser.error('Normal acquisition requires --address and --profile')
        init_db();factory=SessionLocal;profile=args.profile
        connector=FolderConnector(args.address) if args.source=='folder' else APIConnector(args.address) if args.source=='api' else None
    try:
        tick=0
        while args.ticks==0 or tick<args.ticks:
            with factory() as session:
                if session.get(AstronautProfile,profile) is None:raise ValueError('Unknown target profile')
                try:
                    if args.source=='ble':
                        from integrations.bluetooth_sensor import BluetoothSensor
                        batches=asyncio.run(BluetoothSensor(args.address).collect(5))
                    else:
                        assert connector is not None
                        batches=connector.poll()
                    for batch in batches:
                        result=ingest(session,profile,batch)
                        if isinstance(connector,FolderConnector):connector.acknowledge(batch)
                        if args.source=='synthetic':
                            from datetime import datetime
                            from services.space_context import demo_context
                            demo_context(session,profile,(batch.records[0]['timestamp']-datetime(2026,1,31,8)).days)
                        print(f"{result['source']} / {len(result['measurement_ids'])} observations / receipt {result['receipt']}",flush=True)
                except Exception as exc:record_error(session,profile,args.source,exc);print(f'Acquisition error: {type(exc).__name__}',flush=True)
            tick+=1
            if args.ticks==0 or tick<args.ticks:time.sleep(2)
    except KeyboardInterrupt:print('Acquisition stopped; existing records preserved.')


if __name__=='__main__':main()
