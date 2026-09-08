// notify_qq.mjs - 主动推送 QQ 消息 (REST 直发, 不占 WebSocket)
// 用法: node scripts/notify_qq.mjs --content "文本"   或  --file path.txt
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const here = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.resolve(here, '..');
const CONFIG = process.env.QQ_PUSH_CONFIG || path.join(ROOT, 'scripts', 'qq_push_config.json');

function stamp() { return new Date().toISOString().replace('T', ' ').slice(0, 19) + ' UTC'; }

async function main() {
  const argv = process.argv.slice(2);
  let content = '';
  for (let i = 0; i < argv.length; i++) {
    if (argv[i] === '--content' && i + 1 < argv.length) { content = argv[i + 1]; i++; }
    else if (argv[i] === '--file' && i + 1 < argv.length) {
      try { content = fs.readFileSync(argv[i + 1], 'utf8'); } catch (e) { console.error('read file fail', e.message); process.exit(2); }
      i++;
    }
  }
  content = (content || '').trim();
  if (!content) { console.log('[notify_qq] empty content, skip'); process.exit(0); }

  let cfg = {};
  try { cfg = JSON.parse(fs.readFileSync(CONFIG, 'utf8')); } catch (e) { /* keep empty */ }
  const logPath = cfg.logPath || path.join(ROOT, 'scripts', 'alerts', 'qq_push.log');
  fs.mkdirSync(path.dirname(logPath), { recursive: true });
  const persist = (tag) => fs.appendFileSync(logPath, '### ' + stamp() + ' ' + tag + '\n\n' + content + '\n\n', 'utf8');

  const enabled = cfg.enabled === true;
  const appId = cfg.appId || '';
  const appSecret = cfg.appSecret || '';
  const targetId = cfg.targetId || '';
  const scope = cfg.scope || 'c2c';
  if (!enabled || !appId || !appSecret || !targetId) {
    persist('[log_only]');
    console.log('[notify_qq] not configured (enabled=' + enabled + '), content logged only');
    process.exit(0);
  }

  const sdkUrl = cfg.sdkUrl || '';
  try {
    if (!sdkUrl) throw new Error('sdkUrl missing in ' + CONFIG);
    const mod = await import(sdkUrl);
    const QQBot = mod.QQBot;
    const bot = new QQBot({ appId: appId, appSecret: appSecret, logger: console });
    const resp = await bot.sendText({ scope: scope, targetId: targetId }, content);
    persist('[pushed ' + scope + ':' + targetId + ' id=' + (resp && resp.id) + ']');
    console.log('[notify_qq] pushed ok id=' + (resp && resp.id));
  } catch (err) {
    persist('[push_failed] ' + (err && err.message ? err.message : String(err)));
    console.error('[notify_qq] push failed: ' + (err && err.message ? err.message : String(err)));
    process.exit(3);
  }
}

main().catch((e) => { console.error(e); process.exit(1); });
