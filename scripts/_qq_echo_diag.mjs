// _qq_echo_diag.mjs - 临时诊断: 直连QQ WS, 打印入站消息JSON并回声回复(用于抓openid/验证投递)
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const here = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.resolve(here, '..');
const cfg = JSON.parse(fs.readFileSync(path.join(ROOT, 'scripts', 'qq_push_config.json'), 'utf8'));
const LOG = path.join(ROOT, 'scripts', 'alerts', 'qq_diag_capture.log');
const stamp = () => new Date().toISOString().replace('T', ' ').slice(0, 19);
fs.appendFileSync(LOG, '\n### ' + stamp() + ' diag start appId=' + cfg.appId + '\n', 'utf8');
const mod = await import(cfg.sdkUrl);
const bot = new mod.QQBot({ appId: cfg.appId, appSecret: cfg.appSecret, logger: console });
let got = 0;
bot.on('message', async (mCtx) => {
  const msg = mCtx.message;
  got += 1;
  const json = JSON.stringify(msg, null, 1);
  console.log('[QQ_ECHO] got message #' + got + ': ' + json.slice(0, 2500));
  fs.appendFileSync(LOG, '### ' + stamp() + ' got#' + got + '\n' + json.slice(0, 4000) + '\n', 'utf8');
  try {
    const text = (msg.content || '(no text)').toString().slice(0, 200);
    await bot.sendText(msg.replyTarget, '收到你的消息: ' + text);
    console.log('[QQ_ECHO] echo sent to', JSON.stringify(msg.replyTarget));
    fs.appendFileSync(LOG, 'echo target: ' + JSON.stringify(msg.replyTarget) + '\n', 'utf8');
  } catch (e) { console.log('[QQ_ECHO] echo fail: ' + e.message); }
  if (got >= 3) { console.log('[QQ_ECHO] enough, exiting'); process.exit(0); }
});
bot.on('error', (e) => console.log('[QQ_ECHO] error: ' + (e && e.message ? e.message : e)));
bot.on('ready', () => console.log('[QQ_ECHO] READY appId=' + cfg.appId));
await bot.start();
console.log('[QQ_ECHO] exited');
