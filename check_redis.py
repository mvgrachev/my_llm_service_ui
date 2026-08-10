#!/usr/bin/env python3
"""Check Redis cache status."""
import sys
from dotenv import load_dotenv

# Ensure '.' is on sys.path before importing project modules
sys.path.insert(0, '.')
load_dotenv()

from cache.redis_client import cache  # noqa: E402
print('Redis available:', cache.redis_available)
print('Cache type:', type(cache._cache).__name__)
