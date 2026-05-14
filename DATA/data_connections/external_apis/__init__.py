"""
DATA.data_connections.external_apis  — external API clients package.

Exports:
    BaseAPIClient  — Abstract base; all platform clients inherit from this.
    MockAPIClient  — Ready-to-use mock for non-YouTube platforms in Week 2.

Usage:
    from DATA.data_connections.external_apis import BaseAPIClient, MockAPIClient
"""

from DATA.data_connections.external_apis.base_client import BaseAPIClient, MockAPIClient

__all__ = ["BaseAPIClient", "MockAPIClient"]