"""Bluetooth SIG HRS: explicit discovery, notifications and bounded reconnection."""
import asyncio
from datetime import datetime,timezone
from integrations.sensor_interface import SensorInterface
from integrations.acquisition import Batch

HRS='0000180d-0000-1000-8000-00805f9b34fb'
HRM='00002a37-0000-1000-8000-00805f9b34fb'


def parse_heart_rate(data):
    data=bytes(data)
    if len(data)<2:raise ValueError('Truncated HRS packet')
    flags=data[0];width=2 if flags&1 else 1;offset=1+width
    if len(data)<offset:raise ValueError('Truncated heart-rate value')
    value=int.from_bytes(data[1:offset],'little')
    if flags&8:
        offset+=2
        if len(data)<offset:raise ValueError('Truncated energy-expended field')
    rr=[]
    if flags&16:
        if len(data)<=offset or (len(data)-offset)%2:raise ValueError('Invalid RR interval payload')
        rr=[int.from_bytes(data[i:i+2],'little')*1000/1024 for i in range(offset,len(data),2)]
    elif len(data)!=offset:raise ValueError('Unexpected HRS bytes')
    return {'heart_rate':value,'rr_ms':rr,'quality':'REVIEW' if flags&4 and not flags&2 else 'VALID'}


class BluetoothSensor(SensorInterface):
    def __init__(self,address,characteristic_uuid=HRM,simulated=False):
        self.address=address;self.characteristic_uuid=characteristic_uuid or HRM
        self.simulated=simulated;self.state='DISCONNECTED';self.errors=[];self.rr_ms=[]
    @staticmethod
    async def discover(timeout=5):
        from bleak import BleakScanner
        devices=await BleakScanner.discover(timeout=timeout,return_adv=True,service_uuids=[HRS])
        return [{'address':device.address,'name':device.name or 'Unnamed HRS device'} for device,_ in devices.values()]
    async def collect(self,seconds=5,client_factory=None,retries=2,on_state=None):
        if not 0<seconds<=3600:raise ValueError('Collection duration must be 0-3600 seconds')
        if client_factory is None:
            from bleak import BleakClient
            client_factory=BleakClient
        batches=[]
        def state(value):
            self.state=value
            if on_state:on_state(value)
        def notification(sender,data):
            try:
                if self.state!='CONNECTED':return
                item=parse_heart_rate(data);self.rr_ms.extend(item['rr_ms'])
                now=datetime.now(timezone.utc).replace(tzinfo=None)
                row=dict(metric_name='heart_rate',value=item['heart_rate'],unit='bpm',timestamp=now,data_quality_status=item['quality'])
                batches.append(Batch('ble-hrs',self.address,[row],'SIMULATED_DATA' if self.simulated else 'REAL_SENSOR_DATA',now.isoformat(),not self.simulated))
            except ValueError as exc:self.errors.append(str(exc))
        try:
            for attempt in range(retries+1):
                try:
                    state('CONNECTING')
                    async with client_factory(self.address) as client:
                        if not client.is_connected:raise ConnectionError('BLE connection not established')
                        state('CONNECTED')
                        await client.start_notify(self.characteristic_uuid,notification)
                        remaining=seconds
                        while remaining>0:
                            if not client.is_connected:raise ConnectionError('BLE disconnected')
                            delay=min(.2,remaining);await asyncio.sleep(delay);remaining-=delay
                        await client.stop_notify(self.characteristic_uuid)
                    break
                except Exception as exc:
                    if not isinstance(exc,(OSError,ConnectionError,RuntimeError)) and not type(exc).__module__.startswith('bleak'):
                        raise
                    self.errors.append(str(exc));state('RECONNECTING')
                    if attempt==retries:raise
                    await asyncio.sleep(min(attempt+.1,2))
        finally:state('DISCONNECTED')
        return batches
    def read_measurement(self):
        raise RuntimeError('Use async collect() with a selected compatible HRS device')
    def get_metadata(self):
        return {'sensor_name':'Bluetooth HRS','state':self.state,'hardware_validated':False,'errors':self.errors}
