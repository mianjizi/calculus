/* 四套卷端到端测试：在 jsdom 里逐套作答，检查判分、解析、容错与出处标注。
   用法：node test_all.mjs <html> <bank.json> */
import fs from 'node:fs';
import { JSDOM } from 'jsdom';

const htmlPath = process.argv[2], bankPath = process.argv[3];
const html = fs.readFileSync(htmlPath, 'utf8');
const bank = JSON.parse(fs.readFileSync(bankPath, 'utf8'));

let fails = 0, checks = 0;
function ok(cond, msg) {
  checks++;
  if (!cond) { fails++; console.log('  ✘ ' + msg); } else { console.log('  ✔ ' + msg); }
}
function boot() { return new JSDOM(html, { runScripts: 'dangerously', pretendToBeVisual: true }).window; }
function goPaper(w, pid) {
  const b = w.document.querySelector('button[data-pid="' + pid + '"]');
  if (!b) throw new Error('缺少卷切换按钮 ' + pid);
  b.click();
}
function setText(w, n, val) {
  const el = w.document.querySelector('input.ans[data-q="' + n + '"]');
  if (!el) throw new Error('第 ' + n + ' 题缺少作答框');
  el.value = val;
  el.dispatchEvent(new w.Event('input', { bubbles: true }));
}
function pick(w, n, idx) {
  const els = w.document.querySelectorAll('input[data-kind="choice"][data-q="' + n + '"]');
  els[idx].checked = true;
  els[idx].dispatchEvent(new w.Event('change', { bubbles: true }));
}
function rub(w, n, mode) {
  w.document.querySelectorAll('input[data-kind="rub"][data-q="' + n + '"]').forEach((el, i) => {
    el.checked = mode === 'all' ? true : (mode === 'none' ? false : i === 0);
    el.dispatchEvent(new w.Event('change', { bubbles: true }));
  });
}
const submit = (w) => w.document.getElementById('btnSubmit').click();
function total(w) {
  const m = w.document.querySelector('#report .big');
  return m ? Number(m.textContent) : null;
}
const fb = (w, n) => w.document.getElementById('fb' + n).textContent;

console.log('== 页面整体 ==');
{
  const w = boot();
  const tabs = w.document.querySelectorAll('#tabs button').length;
  ok(tabs === bank.papers.length, '卷切换按钮 ' + tabs + ' 个（题库 ' + bank.papers.length + ' 套）');
  const notes = w.document.getElementById('notes').textContent;
  ok(notes.includes('考研数学真题') && notes.includes('复算'), '页脚含来源说明与复算说明');
}

for (const P of bank.papers) {
  console.log('\n== ' + P.name + ' ==');
  const w = boot();
  goPaper(w, P.id);

  ok(w.document.querySelectorAll('.q').length === P.qs.length, '渲染 ' + P.qs.length + ' 题');
  ok(w.document.querySelectorAll('.src').length === P.qs.length, '每题都显示了出处标注');
  const head = w.document.getElementById('pname').textContent;
  ok(head.includes(P.name), '卷名显示：' + P.name);

  // 空卷
  submit(w);
  ok(total(w) === 0, '空卷得 0 分');
  ok([...w.document.querySelectorAll('.feedback')].some((e) => e.textContent.includes('未作答')), '空卷提示未作答');

  // 全对：选择题标准项、可判分题用第一个可接受写法、得分点全勾
  const w2 = boot(); goPaper(w2, P.id);
  for (const q of P.qs) {
    if (q.t === 'choice') pick(w2, q.n, q.a);
    else if (q.accept) setText(w2, q.n, q.accept[0]);
    else rub(w2, q.n, 'all');
  }
  submit(w2);
  ok(total(w2) === 100, '全部按参考答案作答得 100 分（实得 ' + total(w2) + '）');
  ok([...w2.document.querySelectorAll('.sol')].every((e) => e.classList.contains('hidden')), '全对时解析默认收起');

  // 逐个写法容错：accept 里每一种写法都应判对
  let aliasN = 0, aliasBad = 0;
  for (const q of P.qs) {
    if (!q.accept) continue;
    for (const a of q.accept) {
      aliasN++;
      setText(w2, q.n, a);
      submit(w2);
      if (!fb(w2, q.n).includes('✔')) { aliasBad++; console.log('      ✘ 第 ' + q.n + ' 题写法「' + a + '」未被判对'); }
    }
  }
  ok(aliasBad === 0, 'accept 里 ' + aliasN + ' 种写法全部判对');

  // 全错
  const w3 = boot(); goPaper(w3, P.id);
  for (const q of P.qs) {
    if (q.t === 'choice') pick(w3, q.n, q.a === 0 ? 1 : 0);
    else if (q.accept) setText(w3, q.n, 'zzz');
    else rub(w3, q.n, 'none');
  }
  submit(w3);
  ok(total(w3) === 0, '全错得 0 分');
  ok(P.qs.every((q) => !w3.document.getElementById('sol' + q.n).classList.contains('hidden')), '错题解析自动展开');

  // 手动改判
  const btn = w3.document.querySelector('button[data-over]');
  ok(!!btn, '错题带「改判」按钮');
  if (btn) { btn.click(); ok(total(w3) > 0, '改判后分数上升为 ' + total(w3)); }

  // 答案格式容错（取每条 accept 的中间一种写法，验证空格/大小写/异体符号）
  const w4 = boot(); goPaper(w4, P.id);
  const q9 = P.qs.find((q) => q.accept);
  if (q9) {
    const mid = q9.accept[Math.floor(q9.accept.length / 2)];
    setText(w4, q9.n, '  ' + mid.toUpperCase() + '  ');
    submit(w4);
    ok(fb(w4, q9.n).includes('✔'), '写法「' + mid.toUpperCase() + '」（带空格/大写）判对');
  }
}

console.log('\n' + (fails ? '失败 ' + fails + '/' + checks + ' 项' : '全部 ' + checks + ' 项通过'));
process.exit(fails ? 1 : 0);
