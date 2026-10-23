import asyncio
import unittest
from unittest.mock import patch
from judge_model import ManagedOpenRouterModel, OpenRouterModel


class ClientOwnershipTests(unittest.TestCase):
    def test_async_clients_close_before_loop_exit_on_success_and_failure(self):
        for fail in (False, True):
            with self.subTest(failure=fail):
                closed=[]
                class Client:
                    async def close(self): closed.append(asyncio.get_running_loop())
                async def generate(model,*args,**kwargs):
                    model.load_model(async_mode=True)
                    if fail: raise ValueError('simulated generation failure')
                    return 'response',None
                model=object.__new__(ManagedOpenRouterModel)
                async def run():
                    loop=asyncio.get_running_loop()
                    if fail:
                        with self.assertRaises(ValueError): await model._a_generate('prompt')
                    else: self.assertEqual(await model._a_generate('prompt'),('response',None))
                    self.assertEqual(closed,[loop])
                with patch.object(OpenRouterModel,'load_model',return_value=Client()), patch.object(OpenRouterModel,'_a_generate',generate):
                    asyncio.run(run())

    def test_sync_clients_close_on_success_and_failure(self):
        for fail in (False, True):
            with self.subTest(failure=fail):
                closed=[]
                class Client:
                    def close(self): closed.append(True)
                def generate(model,*args,**kwargs):
                    model.load_model()
                    if fail: raise ValueError('simulated failure')
                    return 'response',None
                model=object.__new__(ManagedOpenRouterModel)
                with patch.object(OpenRouterModel,'load_model',return_value=Client()), patch.object(OpenRouterModel,'_generate_raw_response',generate):
                    if fail:
                        with self.assertRaises(ValueError): model._generate_raw_response('prompt')
                    else: self.assertEqual(model._generate_raw_response('prompt'),('response',None))
                self.assertEqual(closed,[True])


if __name__=='__main__': unittest.main()
