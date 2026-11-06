<?php
declare(strict_types=1);
require __DIR__.'/gateway.php';
$root=sys_get_temp_dir().'/dxtalker-gateway-'.bin2hex(random_bytes(8));mkdir($root,0700);
$checks=0;
function check(bool $condition,string $name): void {global $checks;if(!$condition)throw new RuntimeException('FAIL: '.$name);$checks++;}
function clean(string $path): void {if(is_dir($path)){foreach(scandir($path) as $item)if($item!=='.' && $item!=='..')clean($path.'/'.$item);rmdir($path);}else unlink($path);}
function request_body(array $plan,string $voice='voiceA'): string {return json_encode(['schema'=>'dxtalker-speech-request','version'=>1,'voice_id'=>$voice,'plan'=>$plan],JSON_THROW_ON_ERROR);}
$config=['enabled'=>true,'api_key'=>'PRIVATE_UPSTREAM_KEY','pilot_token'=>str_repeat('a',40),'voices'=>[['id'=>'voiceA','name'=>'Pilot voice']],
         'model_id'=>'eleven_multilingual_v2','storage'=>$root.'/state','daily_characters'=>30,'daily_requests'=>100,'hourly_requests_per_ip'=>50,'cache_bytes'=>100000];
$auth='Bearer '.$config['pilot_token'];$now=1800000000;$calls=[];
$provider=static function($key,$voice,$model,$text) use (&$calls): string {check($key==='PRIVATE_UPSTREAM_KEY','provider receives private key');$calls[]=$text;return str_repeat("\x00\x10",100);};
try{
    $result=dx_service($config,'GET','wrong','', '127.0.0.1',$provider,$now);check($result[0]===401,'requires pilot admission');check(!is_dir($root.'/state'),'unauthorized request has no state');
    $result=dx_service($config,'GET',$auth,'','127.0.0.1',$provider,$now);check($result[0]===200,'catalog succeeds');check(!str_contains($result[2],'PRIVATE_UPSTREAM_KEY'),'catalog excludes account key');check(!str_contains($result[2],$config['pilot_token']),'catalog excludes pilot token');check(count($calls)===0,'catalog is not a billed generation');
    $result=dx_service($config,'POST',$auth,request_body([['Alpha',100],['Alpha',0]]),'127.0.0.1',$provider,$now);check($result[0]===200,'renders plan');check(count($calls)===1,'duplicate plan text generated once');check(strlen($result[2])===400+4410,'inserts exact PCM pause');
    $state=json_decode(file_get_contents($root.'/state/usage.json'),true);check($state['characters']===5,'reserves unique uncached text before billing');check(count($state['jobs'])===0,'releases request slot');check(!str_contains(file_get_contents($root.'/state/usage.json'),'127.0.0.1'),'stores hashed IP only');check(!str_contains(file_get_contents($root.'/state/usage.json'),'Alpha'),'does not log text');
    $again=dx_service($config,'POST',$auth,request_body([['Alpha',0]]),'127.0.0.1',$provider,$now);check($again[0]===200 && count($calls)===1,'cache avoids another billed request');
    $quota=dx_service($config,'POST',$auth,request_body([[str_repeat('X',26),0]]),'127.0.0.1',$provider,$now);check($quota[0]===429 && count($calls)===1,'quota blocks before provider');
    foreach([request_body([['hello',0]],'unapproved'),request_body([['hello',-1]]),request_body([["hello\nsecret",0]]),request_body([[str_repeat('x',1001),0]]),'{}','not JSON'] as $bad){$r=dx_service($config,'POST',$auth,$bad,'127.0.0.1',$provider,$now);check($r[0]>=400 && count($calls)===1,'rejects malformed or unauthorized speech');}
    $failure=static function(...$args): string {throw new RuntimeException('PRIVATE_UPSTREAM_KEY response text');};
    $r=dx_service($config,'POST',$auth,request_body([['Bravo',0]]),'127.0.0.1',$failure,$now);check($r[0]===502 && !str_contains($r[2],'PRIVATE'),'redacts upstream errors');
    $state=json_decode(file_get_contents($root.'/state/usage.json'),true);check($state['characters']===10,'failed generation remains reserved');check(count($state['jobs'])===0,'failure releases slot');
    $limited=$config;$limited['hourly_requests_per_ip']=1;
    check(dx_service($limited,'GET',$auth,'','127.0.0.1',$provider,$now)[0]===429,'enforces per IP hourly requests');
    $disabled=$config;$disabled['enabled']=false;check(dx_service($disabled,'GET',$auth,'','127.0.0.1',$provider,$now)[0]===503,'owner kill switch');
    $tiny=$config;$tiny['storage']=$root.'/tiny';$tiny['cache_bytes']=1;
    $before=count($calls);check(dx_service($tiny,'POST',$auth,request_body([['Alpha',0],['Alpha',0]]),'127.0.0.2',$provider,$now)[0]===200,'tiny cache does not affect output');check(count($calls)===$before+1,'never bills unreserved duplicate when cache cannot retain clip');
    $state=json_decode(file_get_contents($root.'/state/usage.json'),true);$state['jobs']=['one'=>$now+100,'two'=>$now+100];dx_write_json($root.'/state/usage.json',$state);
    check(dx_service($config,'POST',$auth,request_body([['Charlie',0]]),'127.0.0.2',$provider,$now)[0]===429,'bounds concurrent upstream jobs');
    $state['jobs']=['old'=>$now-1];dx_write_json($root.'/state/usage.json',$state);
    check(dx_service($config,'POST',$auth,request_body([['Charlie',0]]),'127.0.0.2',$provider,$now)[0]===200,'recovers expired reservations');
    check(dx_service($config,'GET',$auth,'','127.0.0.1',$provider,$now+86400)[0]===200,'rolls daily budget forward');
    if(function_exists('pcntl_fork')){
        $parallel=$config;$parallel['storage']=$root.'/parallel';$parallel['daily_characters']=10;
        $children=[];
        for($i=0;$i<2;$i++){
            $pid=pcntl_fork();
            if($pid===0){
                $slow=static function(...$args): string {usleep(100000);return str_repeat("\x00\x10",100);};
                $r=dx_service($parallel,'POST',$auth,request_body([['Parallel',0]]),'127.0.0.'.($i+5),$slow,$now);
                file_put_contents($root.'/child'.$i,(string)$r[0]);exit(0);
            }
            $children[]=$pid;
        }
        foreach($children as $pid)pcntl_waitpid($pid,$status);
        $statuses=[(int)file_get_contents($root.'/child0'),(int)file_get_contents($root.'/child1')];sort($statuses);
        check($statuses===[200,429],'parallel requests cannot overrun the global character cap');
    }
    echo 'PASS: '.$checks." gateway checks. Synthetic provider only.\n";
}finally{clean($root);}
