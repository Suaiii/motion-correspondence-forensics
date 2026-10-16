import hashlib,json,os,psutil,signal,subprocess,sys,shutil,time
from pathlib import Path
R=Path(__file__).resolve().parent;os.sched_setaffinity(0,{4,5})
def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(1048576),b''):h.update(b)
 return h.hexdigest()
def files_bytes():return sum(p.stat().st_size for p in R.rglob('*') if p.is_file())
def charged(path):
 logical=allocated=0
 for p in path.rglob('*'):
  try:s=p.stat()
  except FileNotFoundError:continue
  if p.is_file():logical+=s.st_size;allocated+=s.st_blocks*512
 return max(logical,allocated),logical,allocated
def group_rss(parent):
 total=0;members={}
 try:procs=[psutil.Process(parent)]+psutil.Process(parent).children(recursive=True)
 except psutil.NoSuchProcess:return 0,{}
 for p in procs:
  try:r=p.memory_info().rss;total+=r;members[str(p.pid)]={'rss':r,'create_time':p.create_time()}
  except psutil.NoSuchProcess:pass
 return total,members
def main():
 req=json.loads((R/'RUN_COMMAND_V2.json').read_text());cmd=req['argv'];env=dict(os.environ,CUDA_VISIBLE_DEVICES='',HF_HUB_OFFLINE='1',TRANSFORMERS_OFFLINE='1',HF_DATASETS_OFFLINE='1',HF_HUB_DISABLE_TELEMETRY='1',PYTHONDONTWRITEBYTECODE='1',OMP_NUM_THREADS='2',OPENBLAS_NUM_THREADS='2',MKL_NUM_THREADS='2',NUMEXPR_NUM_THREADS='2',TOKENIZERS_PARALLELISM='false',TMPDIR=str(R/'run_output_v2/tmp'),TEMP=str(R/'run_output_v2/tmp'),TMP=str(R/'run_output_v2/tmp'),HF_HOME=str(R/'run_output_v2/cache'),HF_HUB_CACHE=str(R/'run_output_v2/cache'),MPLCONFIGDIR=str(R/'run_output_v2/cache'),TORCH_HOME=str(R/'run_output_v2/cache'))
 start=time.time();stdout=R/'worker_v2.stdout.log';stderr=R/'worker_v2.stderr.log';
 with stdout.open('xb') as out,stderr.open('xb') as err:
  p=subprocess.Popen(cmd,cwd=R/'b8_source_v2',env=env,stdin=subprocess.DEVNULL,stdout=out,stderr=err,start_new_session=True)
  proc=psutil.Process(p.pid);create=proc.create_time();(R/'WORKER_HANDLE_V2.json').write_text(json.dumps({'PID':p.pid,'create_time':create,'start_unix':start,'CPU_affinity':[4,5],'argv':cmd}))
  peak=0;last={};violation=None
  while p.poll() is None:
   rss,last=group_rss(p.pid);peak=max(peak,rss);owned=files_bytes();charged_bytes,logical,allocated=charged(R)
   free=shutil.disk_usage(R).free
   if rss>4294967296:violation='RSS4GiB'
   elif charged_bytes>134217728:violation='C10_cloud128MiB'
   elif owned>33554432:violation='C10_output32MiB'
   elif free<21474836480:violation='free20GiB'
   (R/'WATCH_HEARTBEAT_V2.json').write_text(json.dumps({'server_unix':time.time(),'PID':p.pid,'rss':rss,'peak':peak,'owned_bytes':owned,'charged_bytes':charged_bytes,'logical_bytes':logical,'allocated_bytes':allocated,'free_bytes':free,'members':last,'violation':violation}))
   if violation:
    p.terminate();break
   time.sleep(.1)
  code=p.wait(timeout=30)
  if p.poll() is None:p.kill();code=p.wait()
 receipt={'PID':p.pid,'create_time':create,'start_unix':start,'end_unix':time.time(),'exit_code':code,'peak_group_RSS_bytes':peak,'violation':violation,'worker_stdout':stdout.name,'worker_stderr':stderr.name,'worker_stdout_SHA256':sha(stdout),'worker_stderr_SHA256':sha(stderr),'automatic_restart':False,'model_GPU_media_download':False,'final_output_bytes':files_bytes()}
 (R/'RUN_RECEIPT_V2.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(receipt));return code if code else (2 if violation else 0)
if __name__=='__main__':sys.exit(main())
