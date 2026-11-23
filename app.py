"""Streamlit entry point for Aziziye Aşevi."""

import runpy

# Streamlit reruns this entrypoint on every interaction. A regular import would
# reuse the cached module and skip rebuilding the page after the first run.
runpy.run_module("src.app_runtime", run_name="__main__")
