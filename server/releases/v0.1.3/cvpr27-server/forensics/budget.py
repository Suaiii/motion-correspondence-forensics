"""Admission ledger, not a cloud billing or shutdown API."""
import math
from pathlib import Path
from .common import read,write,exclusive,now

CATEGORIES={'storage':500,'profile':200,'mechanism':1000,'method':1000,'recovery':300}


def init(path):
    write(path,{'cap_cny':3000,'gpu_hour_cap':180,'category_caps':CATEGORIES,'entries':[]})


def reserve(path,identifier,category,hours,rate,fixed,quote_reference):
    if not identifier or not quote_reference:raise ValueError('ID and provider quote reference required')
    if not all(math.isfinite(v) and v>=0 for v in (hours,rate,fixed)):raise ValueError('Invalid costs')
    if hours>0 and rate<=0:raise ValueError('A paid GPU quote must have a positive hourly rate')
    with exclusive(str(path)+'.lock'):
        ledger=read(path)
        if category not in ledger['category_caps']:raise ValueError(category)
        if any(r['id']==identifier for r in ledger['entries']):raise ValueError('Reservation ID already exists')
        costs=[r.get('actual_cny',r['reserved_cny']) for r in ledger['entries']]
        used_hours=sum(r.get('actual_gpu_hours',r['reserved_gpu_hours']) for r in ledger['entries'])
        amount=hours*rate+fixed
        cat=sum(r.get('actual_cny',r['reserved_cny']) for r in ledger['entries'] if r['category']==category)
        if sum(costs)+amount>ledger['cap_cny'] or cat+amount>ledger['category_caps'][category] or used_hours+hours>ledger['gpu_hour_cap']:
            raise ValueError('Budget or GPU-hour cap exceeded')
        ledger['entries'].append({'id':identifier,'category':category,'reserved_cny':amount,'reserved_gpu_hours':hours,
            'rate_cny_per_hour':rate,'quote_reference':quote_reference,'status':'reserved','created':now()})
        write(path,ledger,replace=True)


def settle(path,identifier,actual,hours,receipt):
    if not receipt or not all(math.isfinite(v) and v>=0 for v in (actual,hours)):raise ValueError('Actual bill and receipt required')
    with exclusive(str(path)+'.lock'):
        ledger=read(path);r=next(r for r in ledger['entries'] if r['id']==identifier)
        if r['status']=='settled':raise ValueError('Already settled; preserve the receipt')
        r.update(status='settled',actual_cny=actual,actual_gpu_hours=hours,receipt_reference=receipt)
        # Record reality even if the external provider charged over the estimate.
        r['over_reservation']=actual>r['reserved_cny'] or hours>r['reserved_gpu_hours']
        write(path,ledger,replace=True)


def admit(path,identifier,run_dir,category):
    if not path or not identifier:raise ValueError('Paid server work requires a budget reservation')
    with exclusive(str(path)+'.lock'):
        ledger=read(path);r=next(r for r in ledger['entries'] if r['id']==identifier)
        if sum(v.get('actual_cny',v['reserved_cny']) for v in ledger['entries'])>ledger['cap_cny'] or sum(v.get('actual_gpu_hours',v['reserved_gpu_hours']) for v in ledger['entries'])>ledger['gpu_hour_cap']:
            raise ValueError('Recorded project spending exceeds cap')
        if r['status']=='settled' or r['category']!=category:raise ValueError('Inactive or wrong-stage reservation')
        if 'run_id' in r and r['run_id']!=Path(run_dir).name:raise ValueError('Reservation already belongs to another run')
        r['run_id']=Path(run_dir).name
        r.setdefault('started_utc',now());write(path,ledger,replace=True)
        return dict(r)
