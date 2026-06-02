from django.utils import timezone


class RemoteProbeAgent:
    """Uzak şubelerde çalışacak probe/agent mantığını temsil eder."""

    def __init__(self, name, ip_address, location=None, version='1.0.0'):
        self.name = name
        self.ip_address = ip_address
        self.location = location
        self.version = version
        self.last_heartbeat = None
        self.status = 'unknown'

    def heartbeat(self):
        self.last_heartbeat = timezone.now()
        self.status = 'online'
        return {
            'name': self.name,
            'ip_address': self.ip_address,
            'location': self.location,
            'version': self.version,
            'last_heartbeat': self.last_heartbeat,
            'status': self.status,
        }

    def collect_inventory(self):
        """Uzak probe'un kendi ortamından kısa bir envanter özetini döndürür."""
        return {
            'hostname': self.name,
            'ip_address': self.ip_address,
            'location': self.location,
            'agent_version': self.version,
            'last_seen': self.last_heartbeat or timezone.now(),
        }


class RemoteProbeManager:
    """Centralized manager for distributed probe agents."""

    def __init__(self, probes=None):
        self.probes = probes or []

    def register_probe(self, probe):
        self.probes.append(probe)
        return probe

    def get_online_probes(self):
        return [p for p in self.probes if p.status == 'online']

    def poll_all(self):
        results = []
        for probe in self.probes:
            heartbeat_info = probe.heartbeat()
            results.append(heartbeat_info)
        return results
