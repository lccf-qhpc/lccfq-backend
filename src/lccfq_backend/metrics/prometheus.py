"""
Filename: prometheus.py
Author: Santiago Nunez-Corrales
Date: 2025-10-27
Description:
    Prometheus metric exporter for QPU observables and backend events.

License: Apache 2.0
"""

from prometheus_client import Gauge, Counter, start_http_server
from threading import Lock
from datetime import datetime
import time
import threading

from ..config.metrics import (
    prometheus_export_port,
    metrics_export_interval,
)
from ..logging.logger import setup_logger
from ..model.observables import QPUObservables

logger = setup_logger("lccfq.prometheus")


class PrometheusMetricExporter:
    """
    Exposes QPU observables and backend metrics to Prometheus via HTTP.

    Supports periodic and event-driven update modes.
    """

    def __init__(self):
        self._lock = Lock()

        # Gauges for per-qubit observables
        self.gauges = {
            "t1": Gauge("qpu_t1", "T1 relaxation time (μs)", ["qubit"]),
            "t2": Gauge("qpu_t2", "T2 dephasing time (μs)", ["qubit"]),
            "anharmonicity": Gauge("qpu_anharmonicity", "Anharmonicity (GHz)", ["qubit"]),
            "frequency": Gauge("qpu_frequency", "Qubit frequency (GHz)", ["qubit"]),
            "gate_fidelity_1q": Gauge("qpu_gate_fidelity_1q", "1Q gate fidelity", ["qubit"]),
            "gate_fidelity_2q": Gauge("qpu_gate_fidelity_2q", "2Q gate fidelity", ["qubit"]),
            "rx_duration": Gauge("qpu_rx_duration", "RX gate duration (ns)", ["qubit"]),
            "ry_duration": Gauge("qpu_ry_duration", "RY gate duration (ns)", ["qubit"]),
            "sqrt_iswap_duration": Gauge("qpu_sqrt_iswap_duration", "√iSWAP gate duration (ns)", ["qubit"]),
            "reset_duration": Gauge("qpu_reset_duration", "Reset duration (ns)", ["qubit"]),
            "measurement_duration": Gauge("qpu_measurement_duration", "Measurement duration (ns)", ["qubit"]),
            "max_circuit_depth": Gauge("qpu_max_circuit_depth", "Maximum allowed circuit depth", ["qubit"]),
        }

        # Uptime gauge (binary: 1 if online, 0 if offline)
        self.uptime_gauge = Gauge("qpu_uptime", "QPU availability state (1=online, 0=offline)")

        # Backend scheduling counters
        self.scheduling_events = {
            "tasks_accepted": Counter("qpu_tasks_accepted", "Tasks accepted by backend"),
            "tasks_executed": Counter("qpu_tasks_executed", "Tasks executed on QPU"),
            "tasks_failed": Counter("qpu_tasks_failed", "Tasks that failed execution"),
        }

        logger.info(f"Exporter initialized on port {prometheus_export_port}")
        start_http_server(prometheus_export_port)

    def export_qpu_observables(self, observables: QPUObservables):
        """Update per-qubit gauges from current observables."""
        with self._lock:
            for idx, qobs in observables.qubits.items():
                label = {"qubit": str(idx)}
                self.gauges["t1"].labels(**label).set(qobs.t1)
                self.gauges["t2"].labels(**label).set(qobs.t2)
                self.gauges["anharmonicity"].labels(**label).set(qobs.anharmonicity)
                self.gauges["frequency"].labels(**label).set(qobs.frequency)
                self.gauges["gate_fidelity_1q"].labels(**label).set(qobs.gate_fidelity_1q)
                self.gauges["gate_fidelity_2q"].labels(**label).set(qobs.gate_fidelity_2q)
                self.gauges["rx_duration"].labels(**label).set(qobs.rx_duration)
                self.gauges["ry_duration"].labels(**label).set(qobs.ry_duration)
                self.gauges["sqrt_iswap_duration"].labels(**label).set(qobs.sqrt_iswap_duration)
                self.gauges["reset_duration"].labels(**label).set(qobs.reset_duration)
                self.gauges["measurement_duration"].labels(**label).set(qobs.measurement_duration)
                self.gauges["max_circuit_depth"].labels(**label).set(qobs.max_circuit_depth)

            logger.debug(f"Exported observables for {len(observables.qubits)} qubits")

    def update_uptime(self, online: bool):
        """Expose QPU availability status as a Prometheus metric."""
        self.uptime_gauge.set(1.0 if online else 0.0)
        logger.debug(f"QPU online={online} exported as uptime metric")

    def record_scheduling_event(self, event_type: str):
        """Increment backend scheduling counters."""
        if event_type in self.scheduling_events:
            self.scheduling_events[event_type].inc()
            logger.debug(f"Recorded scheduling event: {event_type}")
        else:
            logger.warning(f"Unknown scheduling event type: {event_type}")

    def start_periodic_export(self, fetch_observables_fn):
        """Background thread to periodically export observables."""

        def loop():
            while True:
                try:
                    obs = fetch_observables_fn()
                    if obs:
                        self.export_qpu_observables(obs)
                except Exception as e:
                    logger.error(f"Error during periodic export: {e}")

                time.sleep(metrics_export_interval)

        threading.Thread(target=loop, daemon=True).start()
        logger.info("Periodic exporter thread launched.")