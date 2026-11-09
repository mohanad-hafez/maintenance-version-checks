const fs = require('node:fs');
const readline = require('node:readline');
const {execFileSync} = require('node:child_process');
const [workspace, tool, evidence] = process.argv.slice(2);
let stage = 0;
const tools = [
  {name:'scan',description:'List the eligible source files.'},
  {name:'apply',description:'Run the original recommended updater helper against the saved NuGet responses.'},
  {name:'review',description:'Review the resulting version property diff.'},
  {name:'submit',description:'Request build, pack and a pull request for the reviewed changes.'},
].map(tool=>({...tool,inputSchema:{type:'object',properties:{},additionalProperties:false}}));

function run(command,args) {
  return execFileSync(command,args,{cwd:workspace,encoding:'utf8'});
}

function call(name) {
  if (name !== tools[stage]?.name) throw Error('Unexpected operation order');
  let text = '';
  if (name === 'scan') text = run('git',['ls-files','src']).split('\n')
    .filter(path => !path.split('/').includes('tests') && /\.(csproj|ilproj|props)$/.test(path)).join('\n');
  if (name === 'apply') {
    run('python3',[tool,'original']);
    text = 'Applied the recommended helper.';
  }
  if (name === 'review') text = run('git',['diff','--','src']);
  if (name === 'submit') {
    const paths = run('git',['diff','--name-only']).trim().split('\n');
    if (!paths.length || paths.some(path=>!path.startsWith('src/') || path.split('/').includes('tests'))) throw Error('Invalid edit scope');
    fs.writeFileSync(evidence+'/agent-submit.json',JSON.stringify({paths}),{flag:'wx'});
    text = 'Submitted for build, pack and publication.';
  }
  fs.appendFileSync(evidence+'/agent-tools.jsonl',JSON.stringify({name})+'\n');
  stage++;
  return text;
}

readline.createInterface({input:process.stdin}).on('line',line=>{
  const message = JSON.parse(line);
  if (message.id == null) return;
  const response = {jsonrpc:'2.0',id:message.id};
  try {
    if (message.method === 'initialize') response.result = {
      protocolVersion:message.params.protocolVersion,capabilities:{tools:{}},serverInfo:{name:'matched-maintenance',version:'1'},
    };
    else if (message.method === 'tools/list') response.result = {tools};
    else if (message.method === 'ping') response.result = {};
    else if (message.method === 'tools/call') response.result = {content:[{type:'text',text:call(message.params.name)}]};
    else throw Error('Unknown method');
  } catch(error) {
    response.result = {isError:true,content:[{type:'text',text:error.message}]};
  }
  process.stdout.write(JSON.stringify(response)+'\n');
});
