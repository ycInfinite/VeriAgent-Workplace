// Pure official config-resolver test: no client launch, key, network or model.
import fs from 'node:fs';
import path from 'node:path';
import {pathToFileURL} from 'node:url';
import assert from 'node:assert/strict';
const root = process.cwd();
const chunks = path.join(root,'.cache/qwen-code/node_modules/@qwen-code/qwen-code/chunks');
const {resolveCliGenerationConfig} = await import(pathToFileURL(path.join(chunks,'chunk-MFPAVOYJ.js')));
const {createMinimalSettings} = await import(pathToFileURL(path.join(chunks,'chunk-PVKEYO5D.js')));
const settings = JSON.parse(fs.readFileSync('configs/qwen_code_token_plan.example.json','utf8'));
const env = {OPENAI_API_KEY:'OFFLINE_CONFIG_FIXTURE_NOT_A_REAL_KEY'};
const argv = {model:'qwen3.8-max',openaiBaseUrl:settings.modelProviders.openai[0].baseUrl,openaiLogging:false};
function summary(cfg) {
  const g=cfg.generationConfig;
  return {contextWindowSize:g.contextWindowSize,enable_thinking:g.extra_body?.enable_thinking??null,
          output_tokens:g.samplingParams?.max_tokens??null,maxRetries:g.maxRetries??null};
}
const original=summary(resolveCliGenerationConfig({argv,settings:createMinimalSettings().merged,selectedAuthType:'openai',env}));
const fixed=summary(resolveCliGenerationConfig({argv,settings,selectedAuthType:'openai',env}));
assert.notEqual(original.contextWindowSize,8192);
assert.equal(original.enable_thinking,null);
assert.deepEqual(fixed,{contextWindowSize:8192,enable_thinking:false,output_tokens:256,maxRetries:0});
assert.equal(settings.ui.enableFollowupSuggestions,false);
assert.equal(settings.ui.enableSpeculation,false);
assert.equal(settings.disableAllHooks,true);
const launcher=fs.readFileSync('scripts/launch_interactive_client.py','utf8');
assert(!launcher.includes("receipt['qwen_cli'], '--bare'"));
const result={status:'passed',official_cli_version:'0.23.4',original_bare:original,fixed,
              followup_suggestions:false,source_inspected:'llm-PJU4VT3K.js:createMinimalSettings branch',
              scope:'pure config resolver; not a model payload/cost qualification',model_requests:0};
const output=process.argv[2];
if (!output) throw new Error('Provide a new result path');
fs.writeFileSync(output,JSON.stringify(result,null,2),{flag:'wx'});
process.stdout.write(JSON.stringify(result)+'\n');
