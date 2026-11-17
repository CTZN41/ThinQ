"""Deterministic UI fixture server; no AI or physical device calls."""
from thinq_demo import washer
from thinq_demo.web import create_app
from thinq_demo.engine import Engine
from aiohttp import web
async def fixture(source,experience):
 return {'source':source,'token':None,'facts':dict(purpose='general',temperature_c=40,rinse_count=3,spin='high',time_min=40,time_max=50,time_kind='observed_total',course='표준')}
washer.analyze=fixture
web.run_app(create_app(engine=Engine(),port=8770),host='127.0.0.1',port=8770)
