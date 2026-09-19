"""Small manufacturer-neutral HTTP client. It never commands motors.
Feed it actual, timestamped drone telemetry from a vendor SDK or read-only adapter.
Network deployment needs an authenticated TLS gateway; default is local development.
"""
from dataclasses import dataclass
import time
import requests

@dataclass(frozen=True)
class Measurement:
    lat: float
    lon: float
    alt: float
    battery: float
    captured_at: float  # Unix seconds of acquisition, not time of retransmission

class HubClient:
    def __init__(self, base_url='http://127.0.0.1:8000'):
        self.base_url=base_url.rstrip('/')
        self.session=requests.Session()
        self.drone_id=None

    def register(self, pilot_name, measurement, capabilities):
        response=self.session.post(self.base_url+'/api/swarm/register_volunteer',json={
            'pilot_name':pilot_name,'lat':measurement.lat,'lon':measurement.lon,'alt':measurement.alt,
            'capabilities':capabilities},timeout=5)
        response.raise_for_status()
        self.drone_id=response.json()['drone_id']
        return self.drone_id

    def update(self, measurement):
        """Call on NEW samples (>=1 Hz). A missing/expired response means no guidance."""
        if self.drone_id is None:
            raise RuntimeError('Register the volunteer first')
        if not 0 <= time.time()-measurement.captured_at <= 3:
            return None
        try:
            response=self.session.post(f'{self.base_url}/api/volunteer/{self.drone_id}/telemetry',
                                       json=vars(measurement),timeout=2)
            response.raise_for_status()
            response=self.session.get(f'{self.base_url}/api/volunteer/{self.drone_id}/guidance',timeout=2)
            response.raise_for_status()
            data=response.json()
            return data if data.get('telemetry_fresh') and data.get('guidance') else None
        except (requests.RequestException, ValueError):
            return None
