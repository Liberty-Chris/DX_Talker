<?php
declare(strict_types=1);
/* Private service code. Install outside the public website folder. */

function dx_reply(int $status, string $code): array {
    return [$status, ['Content-Type'=>'application/json'], json_encode(['error'=>$code], JSON_THROW_ON_ERROR)];
}

function dx_write_json(string $path, array $data): void {
    $temp=$path.'.'.bin2hex(random_bytes(6)).'.tmp';
    if(file_put_contents($temp,json_encode($data,JSON_THROW_ON_ERROR))===false) throw new RuntimeException('storage');
    chmod($temp,0600);
    if(!rename($temp,$path)){unlink($temp);throw new RuntimeException('storage');}
}

function dx_provider(string $key, string $voice, string $model, string $text): string {
    $curl=curl_init('https://api.elevenlabs.io/v1/text-to-speech/'.rawurlencode($voice).'?output_format=pcm_22050');
    $pcm='';$tooLarge=false;
    curl_setopt_array($curl,[CURLOPT_POST=>true,CURLOPT_POSTFIELDS=>json_encode(['text'=>$text,'model_id'=>$model,'seed'=>42],JSON_THROW_ON_ERROR),
        CURLOPT_HTTPHEADER=>['xi-api-key: '.$key,'Content-Type: application/json','Accept: audio/pcm'],
        CURLOPT_FOLLOWLOCATION=>false,CURLOPT_CONNECTTIMEOUT=>5,CURLOPT_TIMEOUT=>20,
        CURLOPT_SSL_VERIFYPEER=>true,CURLOPT_SSL_VERIFYHOST=>2,CURLOPT_PROTOCOLS=>CURLPROTO_HTTPS,
        CURLOPT_WRITEFUNCTION=>static function($handle,string $chunk) use (&$pcm,&$tooLarge): int {
            if(strlen($pcm)+strlen($chunk)>22050*2*120){$tooLarge=true;return 0;}
            $pcm.=$chunk;return strlen($chunk);
        }]);
    $ok=curl_exec($curl);$status=curl_getinfo($curl,CURLINFO_RESPONSE_CODE);$type=strtolower(explode(';',(string)curl_getinfo($curl,CURLINFO_CONTENT_TYPE))[0]);
    curl_close($curl);
    if($ok===false || $status!==200 || $tooLarge || !in_array($type,['audio/pcm','audio/raw','application/octet-stream'],true) || $pcm==='' || strlen($pcm)%2!==0)throw new RuntimeException('provider');
    return $pcm;
}

function dx_cache(string $dir,string $key,int $now): ?string {
    $path=$dir.'/'.$key.'.pcm';
    if(is_link($path) || !is_file($path) || filemtime($path)<$now-86400 || filesize($path)>22050*2*120)return null;
    $pcm=file_get_contents($path);
    return $pcm!==false && $pcm!=='' && strlen($pcm)%2===0 ? $pcm : null;
}

function dx_cache_save(string $dir,string $key,string $pcm,int $limit,int $now): void {
    $files=glob($dir.'/*.pcm') ?: []; $total=0;$items=[];
    foreach($files as $path){
        if(is_link($path))continue;
        $size=filesize($path);$stamp=filemtime($path);
        if($stamp<$now-86400){unlink($path);continue;}
        $total+=$size;$items[]=[$stamp,$path,$size];
    }
    usort($items,static fn($a,$b)=>$a[0]<=>$b[0]);
    while($items && ($total+strlen($pcm)>$limit || count($items)>=2000)){
        [, $path, $size]=array_shift($items);unlink($path);$total-=$size;
    }
    if(strlen($pcm)>$limit)return;
    $temp=$dir.'/'.bin2hex(random_bytes(12)).'.tmp';
    if(file_put_contents($temp,$pcm)===false)throw new RuntimeException('storage');
    chmod($temp,0600);rename($temp,$dir.'/'.$key.'.pcm');touch($dir.'/'.$key.'.pcm',$now);
}

function dx_service(array $config,string $method,string $authorization,string $body,string $remoteIp,?callable $provider=null,?int $now=null): array {
    $now=$now ?? time();
    if(($config['enabled'] ?? false)!==true || empty($config['api_key']) || empty($config['pilot_token']) || count($config['voices'] ?? [])<1)return dx_reply(503,'not_configured');
    if(!hash_equals('Bearer '.$config['pilot_token'],$authorization))return dx_reply(401,'unauthorized');
    if(!in_array($method,['GET','POST'],true))return dx_reply(405,'method_not_allowed');
    $voices=$config['voices'];$model=$config['model_id'];
    if(!array_is_list($voices))return dx_reply(503,'not_configured');
    if(count($voices)>100 || !preg_match('/^[A-Za-z0-9_-]{1,128}$/D',$model))return dx_reply(503,'not_configured');
    foreach($voices as $voice){if(!is_array($voice) || count($voice)!==2 || !isset($voice['id'],$voice['name']) || !preg_match('/^[A-Za-z0-9_-]{1,128}$/D',$voice['id']) || !is_string($voice['name']) || strlen($voice['name'])>100)return dx_reply(503,'not_configured');}
    $plan=[];$voiceId='';
    if($method==='POST'){
        if(strlen($body)>32768)return dx_reply(413,'too_large');
        try{$input=json_decode($body,true,32,JSON_THROW_ON_ERROR);}catch(Throwable $e){return dx_reply(400,'bad_request');}
        if(!is_array($input) || !in_array(count($input),[4,5],true) || ($input['schema'] ?? null)!=='dxtalker-speech-request' || ($input['version'] ?? null)!==1 || !is_string($input['voice_id'] ?? null) || !is_array($input['plan'] ?? null))return dx_reply(400,'bad_request');
        if(count($input)===5 && (!isset($input['model_id']) || !is_string($input['model_id'])))return dx_reply(400,'bad_request');
        if(isset($input['model_id']) && $input['model_id']!=='' && $input['model_id']!==$model)return dx_reply(403,'model_changed');
        $voiceId=$input['voice_id'] ?: $voices[0]['id'];
        if(!in_array($voiceId,array_column($voices,'id'),true))return dx_reply(403,'voice_unavailable');
        $plan=$input['plan'];$chars=0;$pauses=0;
        if(!array_is_list($plan) || count($plan)<1 || count($plan)>128)return dx_reply(400,'bad_request');
        foreach($plan as $part){
            if(!is_array($part) || !array_is_list($part) || count($part)!==2 || !is_string($part[0]) || !is_int($part[1]) || $part[1]<0 || $part[1]>3000 || trim($part[0])==='' || preg_match('/[\x00-\x1f\x7f]/',$part[0]))return dx_reply(400,'bad_request');
            $chars+=strlen($part[0]);$pauses+=$part[1];
        }
        if($chars>1000 || $pauses>60000)return dx_reply(413,'too_large');
    }
    $private=$config['storage'];
    if(!is_dir($private) && !mkdir($private,0700,true))return dx_reply(503,'storage_unavailable');
    $cache=$private.'/cache';if(!is_dir($cache))mkdir($cache,0700);
    $lock=fopen($private.'/usage.lock','c');if(!$lock)return dx_reply(503,'storage_unavailable');chmod($private.'/usage.lock',0600);
    if(!flock($lock,LOCK_EX)){fclose($lock);return dx_reply(503,'storage_unavailable');}
    $job=bin2hex(random_bytes(12));$keys=[];$missing=[];$ready=[];
    try{
        $statePath=$private.'/usage.json';
        $state=is_file($statePath) ? json_decode((string)file_get_contents($statePath),true,32,JSON_THROW_ON_ERROR) : [];
        if(!is_array($state))throw new RuntimeException('storage');
        $day=gmdate('Y-m-d',$now);$hour=gmdate('Y-m-d-H',$now);
        if(($state['day'] ?? '')!==$day)$state=['day'=>$day,'characters'=>0,'requests'=>0,'hour'=>$hour,'ips'=>[],'jobs'=>[]];
        if(($state['hour'] ?? '')!==$hour){$state['hour']=$hour;$state['ips']=[];}
        $ip=hash_hmac('sha256',$remoteIp,$config['pilot_token']);
        $state['jobs']=array_filter($state['jobs'] ?? [],static fn($expires)=>$expires>$now);
        if(($state['requests'] ?? 0)>=$config['daily_requests'] || ($state['ips'][$ip] ?? 0)>=$config['hourly_requests_per_ip'])return dx_reply(429,'rate_limited');
        $state['requests']++;$state['ips'][$ip]=($state['ips'][$ip] ?? 0)+1;
        if($method==='GET'){
            dx_write_json($statePath,$state);
            return [200,['Content-Type'=>'application/json'],json_encode(['schema'=>'dxtalker-speech-catalog','version'=>1,'model_id'=>$model,'voices'=>$voices],JSON_THROW_ON_ERROR)];
        }
        foreach($plan as [$text,$pause]){
            $key=hash('sha256',json_encode([$model,$voiceId,$text],JSON_THROW_ON_ERROR));$keys[]=$key;
            $cached=dx_cache($cache,$key,$now);
            if($cached===null)$missing[$key]=$text;else $ready[$key]=$cached;
        }
        $charge=array_sum(array_map('strlen',$missing));
        if($state['characters']+$charge>$config['daily_characters']){dx_write_json($statePath,$state);return dx_reply(429,'quota_exceeded');}
        if(count($state['jobs'])>=2){dx_write_json($statePath,$state);return dx_reply(429,'busy');}
        $state['characters']+=$charge;$state['jobs'][$job]=$now+180;
        dx_write_json($statePath,$state);
    }catch(Throwable $e){return dx_reply(503,'storage_unavailable');}
    finally{flock($lock,LOCK_UN);fclose($lock);}
    // Reserve quota before any provider call; failed/cancelled requests are never refunded or retried.
    try{
        $provider=$provider ?? 'dx_provider';$audio='';$deadline=microtime(true)+60;
        foreach($plan as $index=>[$text,$pause]){
            if(microtime(true)>$deadline)throw new RuntimeException('timeout');
            $key=$keys[$index];$pcm=$ready[$key] ?? null;
            if($pcm===null){
                $pcm=$provider($config['api_key'],$voiceId,$model,$text);
                if(!is_string($pcm) || $pcm==='' || strlen($pcm)%2!==0 || strlen($pcm)>22050*2*120)throw new RuntimeException('provider');
                $ready[$key]=$pcm;
                // Serialize cache eviction/writes so parallel clients cannot exceed the configured cache bound.
                $cacheLock=fopen($private.'/cache.lock','c');if(!$cacheLock || !flock($cacheLock,LOCK_EX))throw new RuntimeException('storage');
                try{dx_cache_save($cache,$key,$pcm,$config['cache_bytes'],$now);}finally{flock($cacheLock,LOCK_UN);fclose($cacheLock);}
            }
            $audio.=$pcm.str_repeat("\0",(int)round(22050*$pause/1000)*2);
            if(strlen($audio)>22050*2*120)throw new RuntimeException('too_large');
        }
        return [200,['Content-Type'=>'application/octet-stream'],$audio];
    }catch(Throwable $e){return dx_reply(502,'provider_unavailable');}
    finally{
        $lock=fopen($private.'/usage.lock','c');
        if($lock && flock($lock,LOCK_EX)){
            try{$state=json_decode((string)file_get_contents($private.'/usage.json'),true,32,JSON_THROW_ON_ERROR);unset($state['jobs'][$job]);dx_write_json($private.'/usage.json',$state);}catch(Throwable $e){}
            flock($lock,LOCK_UN);
        }
        if($lock)fclose($lock);
    }
}

function dx_http_entry(string $configPath): void {
    ini_set('display_errors','0');
    header('Cache-Control: no-store');header('X-Content-Type-Options: nosniff');
    try{
        if(($_SERVER['HTTPS'] ?? '')!=='on' && ($_SERVER['HTTPS'] ?? '')!=='1'){http_response_code(400);echo '{"error":"https_required"}';return;}
        $config=json_decode((string)file_get_contents($configPath),true,32,JSON_THROW_ON_ERROR);
        $body=file_get_contents('php://input',false,null,0,32769);
        [$status,$headers,$content]=dx_service($config,$_SERVER['REQUEST_METHOD'] ?? '','Bearer '.($_SERVER['HTTP_X_DXTALKER_PILOT'] ?? ''),$body===false?'':$body,$_SERVER['REMOTE_ADDR'] ?? 'unknown');
        http_response_code($status);foreach($headers as $name=>$value)header($name.': '.$value);echo $content;
    }catch(Throwable $e){http_response_code(503);header('Content-Type: application/json');echo '{"error":"service_unavailable"}';}
}
