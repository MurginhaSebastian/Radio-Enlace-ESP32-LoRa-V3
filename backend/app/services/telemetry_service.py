from collections import deque
from datetime import datetime
from typing import Optional
from app.models.telemetry_model import TelemetryPacket

BUFFER_SIZE = 1000


class TelemetryService:
    def __init__(self):
        self.buffer: deque[TelemetryPacket] = deque(maxlen=BUFFER_SIZE)
        self.latest: Optional[TelemetryPacket] = None
        self.latest_latency_ms: Optional[float] = None
        self.packets_sent: int = 0
        self.packets_received: int = 0
        self.packets_lost: int = 0
        self.start_time = datetime.now()
        self._last_packet_id: Optional[int] = None
        self._rx_observed: int = 0
        self._tx_online: bool = True
        self._rx_online: bool = True

    def add_packet(self, packet: TelemetryPacket):
        self.buffer.append(packet)
        self.latest = packet
        if packet.latency_ms is not None:
            self.latest_latency_ms = packet.latency_ms
        self._rx_online = True
        self._tx_online = True

        # Los contadores y la perdida solo usan el flujo "rx" (DATA del otro nodo).
        # Los "ack" traen IDs del contador propio del nodo: mezclarlos inflaba la perdida.
        if packet.source != "rx":
            return

        self.packets_received += 1
        self._rx_observed += 1

        if self._last_packet_id is not None:
            expected = self._last_packet_id + 1
            gap = packet.packet_id - expected
            if gap > 0:
                self.packets_lost += gap

        self._last_packet_id = packet.packet_id
        self.packets_sent = packet.packet_id

    def get_history(self, limit: int = 100) -> list[TelemetryPacket]:
        items = list(self.buffer)
        return items[-limit:]

    def get_latest(self) -> Optional[TelemetryPacket]:
        return self.latest

    @property
    def packet_loss_pct(self) -> float:
        # Perdidos / esperados desde que arranco el backend (acotado a 0-100 %).
        expected = self._rx_observed + self.packets_lost
        if expected == 0:
            return 0.0
        return round((self.packets_lost / expected) * 100, 1)

    @property
    def uptime_seconds(self) -> int:
        return int((datetime.now() - self.start_time).total_seconds())

    @property
    def link_state(self) -> str:
        if self.latest is None:
            return "SIN_DATOS"
        rssi = self.latest.rssi
        if rssi >= -60:
            return "EXCELENTE"
        if rssi >= -80:
            return "BUENA"
        if rssi >= -100:
            return "REGULAR"
        if rssi >= -115:
            return "MARGINAL"
        return "CRITICA"

    def get_system_state(self) -> dict:
        return {
            "tx_online": self._tx_online,
            "rx_online": self._rx_online,
            "packets_sent": self.packets_sent,
            "packets_received": self.packets_received,
            "packets_lost": self.packets_lost,
            "packet_loss_pct": self.packet_loss_pct,
            "uptime_seconds": self.uptime_seconds,
            "latest_rssi": self.latest.rssi if self.latest else None,
            "latest_snr": self.latest.snr if self.latest else None,
            "latest_latency_ms": self.latest_latency_ms,
            "link_state": self.link_state,
        }
