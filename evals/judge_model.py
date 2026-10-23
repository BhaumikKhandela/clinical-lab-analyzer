"""Own gateway clients until they are closed on the loop that created them.

DeepEval 4.3.0 constructs per-call clients but does not close them. Its sync
generation uses temporary event loops, so deferred async cleanup can fail.
"""
from contextvars import ContextVar
from deepeval.models import OpenRouterModel

_clients = ContextVar('eval_gateway_clients', default=None)


class ManagedOpenRouterModel(OpenRouterModel):
    def load_model(self, async_mode=False):
        client = super().load_model(async_mode=async_mode)
        owned = _clients.get()
        if owned is not None:
            owned.append(client)
        return client

    async def _owned_async(self, method, *args, **kwargs):
        owned = []
        token = _clients.set(owned)
        try:
            return await method(*args, **kwargs)
        finally:
            try:
                for client in owned:
                    await client.close()
            finally:
                _clients.reset(token)

    def _owned_sync(self, method, *args, **kwargs):
        owned = []
        token = _clients.set(owned)
        try:
            return method(*args, **kwargs)
        finally:
            try:
                for client in owned:
                    client.close()
            finally:
                _clients.reset(token)

    async def _a_generate(self, *args, **kwargs):
        return await self._owned_async(super()._a_generate, *args, **kwargs)

    async def _a_generate_raw_response(self, *args, **kwargs):
        return await self._owned_async(super()._a_generate_raw_response, *args, **kwargs)

    def _generate_raw_response(self, *args, **kwargs):
        return self._owned_sync(super()._generate_raw_response, *args, **kwargs)

    def _generate_samples(self, *args, **kwargs):
        return self._owned_sync(super()._generate_samples, *args, **kwargs)
