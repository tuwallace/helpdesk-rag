"""Tracing: every pipeline stage becomes a span in Phoenix (http://localhost:6006)."""
import os, socket, sys
from urllib.parse import urlparse
from opentelemetry import trace
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter

_provider = TracerProvider(resource=Resource.create({"openinference.project.name": "helpdesk-rag"}))   # Phoenix project
_endpoint = os.getenv("PHOENIX_ENDPOINT", "http://localhost:6006/v1/traces")

def _reachable(url, timeout=0.5):
    u = urlparse(url)
    try:
        socket.create_connection((u.hostname, u.port or 80), timeout).close(); return True
    except OSError:
        return False

if _reachable(_endpoint):
    _provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter(endpoint=_endpoint)))
else:   # no exporter: spans are dropped silently instead of spamming retry errors
    print(f"[tracing] Phoenix not reachable at {_endpoint}; tracing is OFF for this run (docker compose up -d)", file=sys.stderr)
trace.set_tracer_provider(_provider)
tracer = trace.get_tracer("helpdesk-rag")
