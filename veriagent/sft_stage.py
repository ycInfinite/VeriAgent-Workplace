"""Frozen whole-trajectory corpus admission and deterministic SFT schedules."""
import gzip,hashlib,json,random
from pathlib import Path
from .teacher_data import CanonicalTeacherEncoder,export_teacher_turns
from .sft_data import content_sha256

ROOT=Path(__file__).resolve().parents[1]
PLAN='configs/sft_comparison_plan.json'


def sha(path):
    with path.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def read(path):return json.loads(path.read_text(encoding='utf-8'))
def require(condition,message):
    if not condition:raise ValueError(message)


def validate_example(e,limit=8192):
    ids=e['input_ids'];labels=e['labels'];prefix=e['prefix_tokens']
    require(0<prefix<len(ids)<=limit,'Empty target,invalid prefix or over-context example')
    require(all(type(x)is int and x>=0 for x in ids),'Invalid token IDs')
    require(all(type(x)is int for x in labels),'Invalid label types')
    require(len(ids)==len(labels)==len(e['attention_mask']),'Unequal tensor lengths')
    require(labels[:prefix]==[-100]*prefix,'Context tokens must have labels=-100')
    require(labels[prefix:]==ids[prefix:],'Assistant targets changed or selectively masked')
    require(e['attention_mask']==[1]*len(ids),'Unspecified packing/padding mask')
    require(e['supervised_tokens']==len(ids)-prefix and e['processed_tokens']==len(ids),'Token counters mismatch')
    require(e['training_eligible'] is True and e['source_pool']=='training_candidate','Nontraining input')
    return True


def schedule(count,epochs,seed):
    result=[]
    for epoch in range(epochs):
        order=list(range(count));random.Random(seed+epoch).shuffle(order)
        result.extend({'epoch':epoch+1,'example_index':i} for i in order)
    return result


def load_inputs(arm,reencode=True):
    require(arm in ('S1','S2'),'Unknown arm')
    cfg=read(ROOT/PLAN)
    require(cfg['status']=='PREPARED_NOT_EXECUTED' and cfg['epochs']==2 and cfg['seed']==42,'Frozen plan changed')
    require(cfg['max_context_tokens']==8192 and cfg['model_revision']=='b968826d9c46dd6066d109eabc6255188de91218','Model/context changed')
    for path,expected in cfg['input_artifact_sha256'].items():
        resolved=(ROOT/path).resolve();require(resolved.is_relative_to(ROOT),'Artifact outside workspace')
        require(sha(resolved)==expected,'Input artifact identity mismatch: '+path)
    selection=read(ROOT/cfg['selection_manifest'])[arm]
    with gzip.open(ROOT/selection['data_path'],'rt',encoding='utf-8') as f:examples=[json.loads(line) for line in f]
    require(sha(ROOT/selection['data_path'])==selection['data_sha256'],'Selected dataset hash mismatch')
    expected_turns=[(t['task_uid'],i) for t in selection['tasks'] for i in range(1,t['turns']+1)]
    require([(e['task_uid'],e['turn']) for e in examples]==expected_turns,'Whole-trajectory order or membership changed')
    approvals=read(ROOT/cfg['quality_approvals'])['approved'];approved={r['task_uid']:r for r in approvals}
    for e in examples:
        validate_example(e,cfg['max_context_tokens'])
        require(e['student_model_revision']==cfg['model_revision'],'Student revision changed')
        require(e['quality_review']==approved[e['task_uid']],'Example approval differs from reviewed artifact')
        require(e['source_run']==cfg['source_run'],'Unexpected source run')
    for key,field in [('turns',None),('processed_tokens','processed_tokens'),('supervised_tokens','supervised_tokens')]:
        actual=len(examples) if field is None else sum(e[field] for e in examples)
        require(actual==selection['totals'][key],'Selection token/turn accounting mismatch')
    if reencode:
        source=ROOT/'experiments'/cfg['source_run'];teacher=read(source/'config.json')
        cohort=read(ROOT/teacher['cohort_manifest']);tasks={t['task_uid']:t for t in cohort['tasks']}
        rows={r['task_uid']:r for r in map(json.loads,(source/'trajectories.jsonl').read_text(encoding='utf-8').splitlines())}
        encoder=CanonicalTeacherEncoder(cfg['max_context_tokens']);reconstructed=[]
        for t in selection['tasks']:
            record=rows[t['task_uid']]
            require(content_sha256(record)==t['trajectory_sha256'],'Source whole trajectory changed')
            reconstructed.extend(export_teacher_turns(record,approved[t['task_uid']],tasks,encoder,teacher,
                source_provider='deepseek',required_decision='approved_for_sft'))
        for expected,actual in zip(reconstructed,examples):
            for field in ['input_ids','labels','attention_mask','prefix_sha256','canonical_target_sha256']:
                require(expected[field]==actual[field],'Re-encoding failed: '+field)
    order=schedule(len(examples),cfg['epochs'],cfg['seed'])
    require(len(order)==cfg['optimizer_steps_per_arm']==310,'Update count changed')
    require(content_sha256(order)==cfg['schedule_sha256'],'Sample order changed')
    return cfg,selection,examples,order


def validate_deployment(required_files):
    build=read(ROOT/'bundle_manifest.json')
    require(build.get('code_transport')=='GitHub fixed-ref temporary raw-file downloads','Unpinned deployment')
    files={e['path']:e for e in build['files']}
    require(set(required_files)<=set(files),'Missing deployed stage execution file')
    for path,e in files.items():
        resolved=(ROOT/path).resolve();require(resolved.is_relative_to(ROOT),'Deployment path outside root')
        require(sha(resolved)==e['sha256'],'Deployment bytes changed: '+path)
    return build


def verify_weights(cfg):
    root=ROOT/cfg['weights_path']
    for name,expected in cfg['weight_and_tokenizer_sha256'].items():
        path=(root/name).resolve();require(path.is_relative_to(root.resolve()),'Model path escape')
        require(sha(path)==expected,'Pinned model/tokenizer bytes changed: '+name)
    index=read(root/'model.safetensors.index.json')
    expected={n for n in cfg['weight_and_tokenizer_sha256'] if n.endswith('.safetensors')}
    require(set(index['weight_map'].values())==expected,'Unexpected weight index files')
    return {'revision':cfg['model_revision'],'files_verified':len(cfg['weight_and_tokenizer_sha256']),'all_match':True}
