#! /usr/bin/env python
'''login to janeway and get data'''
from calendar import monthrange
import re
import requests
import sys
import logging
import yaml

logging.basicConfig(level=logging.INFO)
logger=logging.getLogger(__name__)

def mw_token(response)-> str:
  '''get the so called csrfmiddlewaretoken that Django puts as a hidden field in every form - its part of the security
  if there are no forms, then returns None'''
  regex="'csrfmiddlewaretoken' value='([a-zA-Z0-9]*)'"
  pattern=re.compile(regex)
  matches=pattern.findall(response.text)
  tok=None
  for match in matches: # the same middleware token is placed on every form
    tok=match
  return tok

def login() -> requests.Session:
  '''login and return a Session'''
  login_url='https://bok.idpro.org/login/'
  errors={'Forbidden <span>(403)</span>':'CSRF verification failed. Request aborted.'}
  # TODO protect credentials
  payload = {
    'csrfmiddlewaretoken':'',
    'captcha': ''
  }
  # keep credentials in the private (excluded from git) folder.
  with open('private/config.yaml') as cfg:
    try:
      config=yaml.safe_load(cfg)
    except yaml.YAMLError as exc:
      logger.error(exc)
      sys.exit(-1)

  for key,val in config.items():
    if key.startswith('user_'):
      payload[key]=val

  session= requests.Session()
  response=session.get(login_url)
  tok=mw_token(response)
  if tok:
    payload['csrfmiddlewaretoken']=tok
  p = session.post(login_url, data=payload,headers=dict(Referer=login_url))
  for err,msg in errors.items():
    if err in p.text:
      logger.error(msg)
      sys.exit(-1)
  logger.info('Login successful')
  return session




def read_data(session,year,month) -> str:
  '''read CSV data for a month.
  Assumes already logged in'''
  geo_rpt_page='https://bok.idpro.org/plugins/reporting/geo/'
  parms=dict()
  for ix,parm in enumerate(['start_date','end_date']):
    first_last=[1,monthrange(year,month)[1]][ix]
    val='%d-%02d-%02d'%(year,month,first_last)
    parms[parm]=val
  r = session.get(geo_rpt_page,params=parms)
  payload={}
  tok=mw_token(r)
  if tok:
    payload['csrfmiddlewaretoken']=tok
  p = session.post(r.url, data=payload,headers=dict(Referer=r.url))
  logger.info('Read CSV data for %d-%02d'%(year,month))
  encoded_str=p.content.decode('utf-8')
  return encoded_str

def write_data(data,path,year,month):
  '''writes the data to a file at path using the year and month as part of the file name'''
  filename=path+'bok_geo_use_%d%02d.csv'%(year,month)
  with open(filename,'w',encoding='utf-8') as f:
    f.write(data)
  logger.info('Wrote: %s'%filename)

def main():
  session=login()
  out_path='data/'
  yms=range((3+12*2020),(7+12*2022))
  #yms=range((5+12*2021),(6+12*2021))
  for ym in yms:
    y,m=divmod(ym,12)
    m+=1
    data=read_data(session,y,m)
    write_data(data,out_path,y,m)
  session.close()

if __name__=='__main__':
  main()
